"""Config flow for the Maytag Dryer integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_AUTH_URL,
    API_CLIENT_ID,
    API_CLIENT_SECRET,
    API_USER_AGENT,
    CONF_DRYER_SAIDS,
    CONF_PASSWORD,
    CONF_USER,
    CONF_WASHER_SAIDS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Schema for the user step
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USER): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_DRYER_SAIDS, default=""): str,
        vol.Optional(CONF_WASHER_SAIDS, default=""): str,
    }
)

# Schema for the reauth step (credentials only)
STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USER): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


def _parse_saids(raw: str) -> list[str]:
    """Parse a comma- or newline-separated string of SAIDs into a list.

    Strips whitespace and filters empty strings.
    """
    return [s.strip() for s in raw.replace("\n", ",").split(",") if s.strip()]


async def _async_validate_credentials(
    hass: Any, user: str, password: str
) -> str | None:
    """Try to authenticate against the Whirlpool API.

    Returns None on success, or an error key string on failure.
    """
    session = async_get_clientsession(hass)
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": API_USER_AGENT,
    }
    payload = {
        "client_id": API_CLIENT_ID,
        "client_secret": API_CLIENT_SECRET,
        "grant_type": "password",
        "username": user,
        "password": password,
    }

    try:
        async with asyncio.timeout(15):
            resp = await session.post(API_AUTH_URL, data=payload, headers=headers)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return "cannot_connect"

    if resp.status in (401, 403):
        return "invalid_auth"
    if resp.status != 200:
        return "cannot_connect"

    try:
        data = await resp.json()
    except (aiohttp.ContentTypeError, ValueError):
        return "cannot_connect"

    if not data.get("access_token"):
        return "invalid_auth"

    return None


class MaytagDryerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Maytag Dryer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user = user_input[CONF_USER].strip().lower()
            password = user_input[CONF_PASSWORD]
            dryer_saids = _parse_saids(user_input.get(CONF_DRYER_SAIDS, ""))
            washer_saids = _parse_saids(user_input.get(CONF_WASHER_SAIDS, ""))

            if not dryer_saids and not washer_saids:
                errors["base"] = "no_saids"
            else:
                error = await _async_validate_credentials(self.hass, user, password)
                if error:
                    errors["base"] = error
                else:
                    # Use the email as the unique ID to prevent duplicate entries
                    await self.async_set_unique_id(user)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Maytag ({user})",
                        data={
                            CONF_USER: user,
                            CONF_PASSWORD: password,
                            CONF_DRYER_SAIDS: dryer_saids,
                            CONF_WASHER_SAIDS: washer_saids,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={},
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when credentials become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show re-auth form and update credentials on submission."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user = user_input[CONF_USER].strip().lower()
            password = user_input[CONF_PASSWORD]

            error = await _async_validate_credentials(self.hass, user, password)
            if error:
                errors["base"] = error
            else:
                reauth_entry = self._get_reauth_entry()
                await self.async_set_unique_id(user)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_USER: user,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow the user to update credentials and SAIDs."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            user = user_input[CONF_USER].strip().lower()
            password = user_input[CONF_PASSWORD]
            dryer_saids = _parse_saids(user_input.get(CONF_DRYER_SAIDS, ""))
            washer_saids = _parse_saids(user_input.get(CONF_WASHER_SAIDS, ""))

            if not dryer_saids and not washer_saids:
                errors["base"] = "no_saids"
            else:
                error = await _async_validate_credentials(self.hass, user, password)
                if error:
                    errors["base"] = error
                else:
                    await self.async_set_unique_id(user)
                    self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        data_updates={
                            CONF_USER: user,
                            CONF_PASSWORD: password,
                            CONF_DRYER_SAIDS: dryer_saids,
                            CONF_WASHER_SAIDS: washer_saids,
                        },
                    )

        # Pre-fill with existing values
        existing = reconfigure_entry.data
        schema = vol.Schema(
            {
                vol.Required(CONF_USER, default=existing.get(CONF_USER, "")): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(
                    CONF_DRYER_SAIDS,
                    default=", ".join(existing.get(CONF_DRYER_SAIDS, [])),
                ): str,
                vol.Optional(
                    CONF_WASHER_SAIDS,
                    default=", ".join(existing.get(CONF_WASHER_SAIDS, [])),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
