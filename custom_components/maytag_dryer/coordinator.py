"""DataUpdateCoordinator for the Maytag Dryer integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_AUTH_URL,
    API_APPLIANCE_URL,
    API_CLIENT_ID,
    API_CLIENT_SECRET,
    API_USER_AGENT,
    CONF_DRYER_SAIDS,
    CONF_PASSWORD,
    CONF_USER,
    CONF_WASHER_SAIDS,
    DOMAIN,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


def _safe_attr(attributes: dict[str, Any] | None, key: str) -> Any:
    """Safely extract a value from the appliance attributes dict.

    Returns None if the key is missing or the value sub-key is absent,
    instead of raising AttributeError on chained .get() calls.
    """
    if attributes is None:
        return None
    entry = attributes.get(key)
    if entry is None:
        return None
    return entry.get("value")


class MaytagCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinator that fetches data for all configured Maytag appliances.

    A single coordinator is created per config entry.  It authenticates once
    and then polls every SCAN_INTERVAL, returning a dict keyed by SAID where
    each value is the raw parsed appliance data dict from the Whirlpool API.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self._user: str = entry.data[CONF_USER]
        self._password: str = entry.data[CONF_PASSWORD]
        self._dryer_saids: list[str] = entry.data.get(CONF_DRYER_SAIDS, [])
        self._washer_saids: list[str] = entry.data.get(CONF_WASHER_SAIDS, [])
        self._access_token: str | None = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def dryer_saids(self) -> list[str]:
        """Return the list of dryer SAIDs."""
        return self._dryer_saids

    @property
    def washer_saids(self) -> list[str]:
        """Return the list of washer SAIDs."""
        return self._washer_saids

    @property
    def all_saids(self) -> list[str]:
        """Return all SAIDs (dryers + washers)."""
        return self._dryer_saids + self._washer_saids

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def _async_authenticate(self) -> None:
        """Obtain an OAuth2 access token from the Whirlpool API.

        Raises ConfigEntryAuthFailed on HTTP 401/403 so HA can surface a
        re-auth notification to the user.  Raises UpdateFailed for transient
        network errors.
        """
        session = async_get_clientsession(self.hass)
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "user-agent": API_USER_AGENT,
        }
        payload = {
            "client_id": API_CLIENT_ID,
            "client_secret": API_CLIENT_SECRET,
            "grant_type": "password",
            "username": self._user,
            "password": self._password,
        }

        try:
            async with asyncio.timeout(15):
                resp = await session.post(API_AUTH_URL, data=payload, headers=headers)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Network error during authentication: {err}") from err

        if resp.status == 423:
            raise ConfigEntryAuthFailed(
                "Whirlpool account is locked (HTTP 423). "
                "Unlock your account at account.maytag.com, then reconfigure the integration."
            )
        if resp.status in (400, 401, 403, 500):
            # 400/401/403 = bad credentials; 500 = Whirlpool returns this for wrong password
            raise ConfigEntryAuthFailed(
                f"Invalid credentials (HTTP {resp.status}). "
                "Please reconfigure the integration."
            )
        if resp.status != 200:
            raise UpdateFailed(
                f"Unexpected HTTP {resp.status} from authentication endpoint"
            )

        try:
            # Use content_type=None to accept any content-type the API returns
            data = await resp.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError) as err:
            raise UpdateFailed(f"Could not parse authentication response: {err}") from err

        token = data.get("access_token")
        if not token:
            raise ConfigEntryAuthFailed(
                "Authentication succeeded but no access_token was returned. "
                "Credentials may be invalid."
            )

        self._access_token = token
        _LOGGER.debug("Successfully authenticated with Whirlpool API")

    # ------------------------------------------------------------------
    # Per-appliance fetch
    # ------------------------------------------------------------------

    async def _async_fetch_appliance(
        self, said: str, session: aiohttp.ClientSession
    ) -> dict[str, Any]:
        """Fetch raw data for a single appliance SAID.

        Returns the parsed JSON dict.  Raises UpdateFailed on errors.
        On HTTP 401 clears the token so the next coordinator cycle re-auths.
        """
        url = API_APPLIANCE_URL.format(said=said)
        headers = {
            "Authorization": f"bearer {self._access_token}",
            "user-agent": API_USER_AGENT,
        }

        try:
            async with asyncio.timeout(15):
                resp = await session.get(url, headers=headers)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Network error fetching appliance {said}: {err}") from err

        if resp.status == 401:
            # Token expired — clear it so next cycle re-authenticates
            self._access_token = None
            raise UpdateFailed(f"Access token expired fetching appliance {said}")

        if resp.status != 200:
            raise UpdateFailed(
                f"Unexpected HTTP {resp.status} fetching appliance {said}"
            )

        try:
            return await resp.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError) as err:
            raise UpdateFailed(
                f"Could not parse response for appliance {said}: {err}"
            ) from err

    # ------------------------------------------------------------------
    # DataUpdateCoordinator hook
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data for all appliances.

        Called automatically by DataUpdateCoordinator every SCAN_INTERVAL.
        Returns a dict mapping SAID -> parsed appliance data.
        """
        # Authenticate if we don't have a token yet
        if self._access_token is None:
            await self._async_authenticate()

        session = async_get_clientsession(self.hass)
        results: dict[str, dict[str, Any]] = {}

        for said in self.all_saids:
            try:
                raw = await self._async_fetch_appliance(said, session)
            except UpdateFailed:
                # If token expired mid-loop, re-auth and retry once
                if self._access_token is None:
                    _LOGGER.debug("Token expired; re-authenticating")
                    await self._async_authenticate()
                    raw = await self._async_fetch_appliance(said, session)
                else:
                    raise

            results[said] = raw
            _LOGGER.debug("Fetched data for appliance %s", said)

        return results
