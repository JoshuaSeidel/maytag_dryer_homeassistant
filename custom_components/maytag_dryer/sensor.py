"""Sensor platform for the Maytag Dryer integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    APPLIANCE_TYPE_DRYER,
    APPLIANCE_TYPE_WASHER,
    DOMAIN,
    ICON_DRYER,
    ICON_WASHER,
    MACHINE_STATES,
)
from .coordinator import MaytagCoordinator, _safe_attr

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maytag sensor entities from a config entry."""
    coordinator: MaytagCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[MaytagBaseSensor] = []

    for said in coordinator.dryer_saids:
        entities.append(MaytagDryerSensor(coordinator, said))

    for said in coordinator.washer_saids:
        entities.append(MaytagWasherSensor(coordinator, said))

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Base sensor
# ---------------------------------------------------------------------------

class MaytagBaseSensor(CoordinatorEntity[MaytagCoordinator], SensorEntity):
    """Base class shared by dryer and washer sensors.

    Handles coordinator wiring, device_info, and common attribute extraction.
    Subclasses implement appliance-type-specific attribute extraction.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MaytagCoordinator,
        said: str,
        appliance_type: str,
        icon: str,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self._said = said
        self._appliance_type = appliance_type
        self._attr_icon = icon
        self._attr_unique_id = f"maytag_{appliance_type}_{said.lower()}"
        # Set a stable entity_id that matches the old naming so existing
        # automations and dashboards continue to work.
        self.entity_id = f"sensor.maytag_{appliance_type}_{said.lower()}"

    # ------------------------------------------------------------------
    # Device info — groups sensor + binary_sensor under one device card
    # ------------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info so entities are grouped under a device."""
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
    def native_value(self) -> str | None:
        """Return the human-readable machine state."""
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._said)
        if raw is None:
            return None
        attrs = raw.get("attributes", {})
        status = _safe_attr(attrs, "Cavity_CycleStatusMachineState")
        if status is None:
            return None
        return MACHINE_STATES.get(str(status), str(status))

    # ------------------------------------------------------------------
    # Common attributes shared by dryer and washer
    # ------------------------------------------------------------------

    def _common_attributes(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Extract attributes that exist on both dryers and washers."""
        attrs = raw.get("attributes", {})
        time_remaining = _safe_attr(attrs, "Cavity_TimeStatusEstTimeRemaining")

        end_time = None
        if time_remaining is not None:
            try:
                end_time = dt_util.now() + timedelta(seconds=int(time_remaining))
            except (ValueError, TypeError):
                end_time = None

        return {
            "appliance_id": raw.get("applianceId"),
            "model_number": _safe_attr(attrs, "ModelNumber"),
            "serial_number": _safe_attr(attrs, "XCat_ApplianceInfoSetSerialNumber"),
            "last_synced": raw.get("lastFullSyncTime"),
            "last_modified": raw.get("lastModified"),
            "door_open": _safe_attr(attrs, "Cavity_OpStatusDoorOpen"),
            "status": _safe_attr(attrs, "Cavity_CycleStatusMachineState"),
            "cycle_name": _safe_attr(attrs, "Cavity_CycleSetCycleName"),
            "temperature": None,  # overridden per subclass
            "operations": _safe_attr(attrs, "Cavity_OpSetOperations"),
            "power_on_hours": _safe_attr(attrs, "XCat_OdometerStatusTotalHours"),
            "hours_in_use": _safe_attr(attrs, "XCat_OdometerStatusRunningHours"),
            "total_cycles": _safe_attr(attrs, "XCat_OdometerStatusCycleCount"),
            "remote_enabled": _safe_attr(attrs, "XCat_RemoteSetRemoteControlEnable"),
            "time_remaining": time_remaining,
            "online": _safe_attr(attrs, "Online"),
            "end_time": end_time,
        }

    # ------------------------------------------------------------------
    # CoordinatorEntity callback
    # ------------------------------------------------------------------

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# Dryer sensor
# ---------------------------------------------------------------------------

class MaytagDryerSensor(MaytagBaseSensor):
    """Sensor entity for a Maytag dryer."""

    _attr_name = "Dryer"

    def __init__(self, coordinator: MaytagCoordinator, said: str) -> None:
        """Initialise the dryer sensor."""
        super().__init__(coordinator, said, APPLIANCE_TYPE_DRYER, ICON_DRYER)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return dryer-specific state attributes."""
        if not self.coordinator.data:
            return {}
        raw = self.coordinator.data.get(self._said)
        if raw is None:
            return {}

        attrs = raw.get("attributes", {})
        base = self._common_attributes(raw)

        # Override temperature with dryer-specific key
        base["temperature"] = _safe_attr(attrs, "DryCavity_CycleSetTemperature")

        # Dryer-specific attributes
        base.update(
            {
                "cycle_id": _safe_attr(attrs, "DryCavity_CycleSetCycleSelect"),
                "manual_dry_time": _safe_attr(attrs, "DryCavity_CycleSetManualDryTime"),
                "dryness_level": _safe_attr(attrs, "DryCavity_CycleSetDryness"),
                "airflow": _safe_attr(attrs, "DryCavity_CycleStatusAirFlowStatus"),
                "drying": _safe_attr(attrs, "DryCavity_CycleStatusDrying"),
                "damp": _safe_attr(attrs, "DryCavity_CycleStatusDamp"),
                "steaming": _safe_attr(attrs, "DryCavity_CycleStatusSteaming"),
                "sensing": _safe_attr(attrs, "DryCavity_CycleStatusSensing"),
                "cooldown": _safe_attr(attrs, "DryCavity_CycleStatusCoolDown"),
            }
        )

        return base


# ---------------------------------------------------------------------------
# Washer sensor
# ---------------------------------------------------------------------------

class MaytagWasherSensor(MaytagBaseSensor):
    """Sensor entity for a Maytag washer."""

    _attr_name = "Washer"

    def __init__(self, coordinator: MaytagCoordinator, said: str) -> None:
        """Initialise the washer sensor."""
        super().__init__(coordinator, said, APPLIANCE_TYPE_WASHER, ICON_WASHER)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return washer-specific state attributes."""
        if not self.coordinator.data:
            return {}
        raw = self.coordinator.data.get(self._said)
        if raw is None:
            return {}

        attrs = raw.get("attributes", {})
        base = self._common_attributes(raw)

        # Override temperature with washer-specific key
        base["temperature"] = _safe_attr(attrs, "WashCavity_CycleSetTemperature")

        # Washer-specific attributes
        base.update(
            {
                "cycle_id": _safe_attr(attrs, "WashCavity_CycleSetCycleSelect"),
                "door_locked": _safe_attr(attrs, "Cavity_OpStatusDoorLocked"),
                "drawer_open": _safe_attr(
                    attrs, "WashCavity_OpStatusDispenserDrawerOpen"
                ),
                "need_clean": _safe_attr(
                    attrs, "WashCavity_CycleStatusCleanReminder"
                ),
                "delay_time": _safe_attr(attrs, "Cavity_TimeSetDelayTime"),
                "delay_remaining": _safe_attr(
                    attrs, "Cavity_TimeStatusDelayTimeRemaining"
                ),
                "rinsing": _safe_attr(attrs, "WashCavity_CycleStatusRinsing"),
                "draining": _safe_attr(attrs, "WashCavity_CycleStatusDraining"),
                "filling": _safe_attr(attrs, "WashCavity_CycleStatusFilling"),
                "spinning": _safe_attr(attrs, "WashCavity_CycleStatusSpinning"),
                "soaking": _safe_attr(attrs, "WashCavity_CycleStatusSoaking"),
                "sensing": _safe_attr(attrs, "WashCavity_CycleStatusSensing"),
                "washing": _safe_attr(attrs, "WashCavity_CycleStatusWashing"),
                "add_garment": _safe_attr(
                    attrs, "WashCavity_CycleStatusAddGarment"
                ),
                "spin_speed": _safe_attr(attrs, "WashCavity_CycleSetSpinSpeed"),
                "soil_level": _safe_attr(attrs, "WashCavity_CycleSetSoilLevel"),
                "dispense_enable": _safe_attr(
                    attrs, "WashCavity_CycleSetBulkDispense1Enable"
                ),
                "dispense_level": _safe_attr(
                    attrs, "WashCavity_OpStatusBulkDispense1Level"
                ),
                "dispense_concentration": _safe_attr(
                    attrs, "WashCavity_OpSetBulkDispense1Concentration"
                ),
            }
        )

        return base
