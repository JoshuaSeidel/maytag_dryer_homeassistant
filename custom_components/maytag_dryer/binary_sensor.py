"""Binary sensor for maytag_dryer account status."""
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    PLATFORM_SCHEMA,
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

CONF_DRYER_SAIDS = "dryersaids"
CONF_WASHER_SAIDS = "washersaids"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_DRYER_SAIDS, default=[]): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(CONF_WASHER_SAIDS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the maytag_dryer binary sensor platform."""
    entities = []

    for said in config.get(CONF_DRYER_SAIDS, []):
        entities.append(MaytagDoorBinarySensor(hass, said, "dryer"))

    for said in config.get(CONF_WASHER_SAIDS, []):
        entities.append(MaytagDoorBinarySensor(hass, said, "washer"))

    if entities:
        async_add_entities(entities, True)


class MaytagDoorBinarySensor(BinarySensorEntity):
    """Binary sensor representing the door open state of a Maytag appliance."""

    def __init__(self, hass, said, appliance_type):
        """Initialize the binary sensor."""
        self.hass = hass
        self._said = said
        self._appliance_type = appliance_type
        self._is_on = None

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return f"Maytag {self._appliance_type.title()} Door"

    @property
    def unique_id(self):
        """Return a unique ID for this entity."""
        return f"maytag_{self._appliance_type}_door_{self._said.lower()}"

    @property
    def device_class(self):
        """Return the device class."""
        return BinarySensorDeviceClass.DOOR

    @property
    def is_on(self):
        """Return true if the door is open."""
        return self._is_on

    async def async_update(self):
        """Update door state from the associated sensor entity."""
        sensor_entity_id = f"sensor.maytag_{self._appliance_type}_{self._said.lower()}"
        state = self.hass.states.get(sensor_entity_id)
        if state is not None:
            door_value = state.attributes.get("dooropen")
            if door_value is not None:
                try:
                    self._is_on = bool(int(door_value))
                except (ValueError, TypeError):
                    self._is_on = None
