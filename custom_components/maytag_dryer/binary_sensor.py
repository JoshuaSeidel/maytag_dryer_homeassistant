"""Binary sensor platform for the Maytag Dryer integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    APPLIANCE_TYPE_DRYER,
    APPLIANCE_TYPE_WASHER,
    DOMAIN,
)
from .coordinator import MaytagCoordinator, _safe_attr

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maytag binary sensor entities from a config entry."""
    coordinator: MaytagCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[MaytagDoorBinarySensor] = []

    for said in coordinator.dryer_saids:
        entities.append(MaytagDoorBinarySensor(coordinator, said, APPLIANCE_TYPE_DRYER))

    for said in coordinator.washer_saids:
        entities.append(MaytagDoorBinarySensor(coordinator, said, APPLIANCE_TYPE_WASHER))

    async_add_entities(entities)


class MaytagDoorBinarySensor(CoordinatorEntity[MaytagCoordinator], BinarySensorEntity):
    """Binary sensor representing the door open/closed state of a Maytag appliance.

    Reads door state directly from the coordinator data — no separate API call
    needed, no race condition with the sensor platform.
    """

    _attr_device_class = BinarySensorDeviceClass.DOOR
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MaytagCoordinator,
        said: str,
        appliance_type: str,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self._said = said
        self._appliance_type = appliance_type
        self._attr_name = f"{appliance_type.title()} Door"
        self._attr_unique_id = f"maytag_{appliance_type}_door_{said.lower()}"
        self.entity_id = f"binary_sensor.maytag_{appliance_type}_door_{said.lower()}"

    # ------------------------------------------------------------------
    # Device info — same identifiers as the sensor so they share a device
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info matching the corresponding sensor entity."""
        raw = self.coordinator.data.get(self._said, {}) if self.coordinator.data else {}
        attrs = raw.get("attributes", {})
        model = _safe_attr(attrs, "ModelNumber")
        serial = _safe_attr(attrs, "XCat_ApplianceInfoSetSerialNumber")

        return DeviceInfo(
            identifiers={(DOMAIN, self._said)},
            name=f"Maytag {self._appliance_type.title()} {self._said}",
            manufacturer="Whirlpool / Maytag",
            model=model,
            serial_number=serial,
        )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def is_on(self) -> bool | None:
        """Return True if the door is open."""
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._said)
        if raw is None:
            return None
        attrs = raw.get("attributes", {})
        door_value = _safe_attr(attrs, "Cavity_OpStatusDoorOpen")
        if door_value is None:
            return None
        try:
            return bool(int(door_value))
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # CoordinatorEntity callback
    # ------------------------------------------------------------------

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
