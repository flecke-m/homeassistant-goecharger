"""Switch platform for the go-eCharger MQTT integration."""

import logging

from homeassistant import config_entries, core
from homeassistant.components.switch import SwitchEntity

from .base_entity import GoeChargerBaseEntity
from .charger import ChargerData, async_publish_command
from .const import CONF_NAME, CONF_SERIAL, DATA_CHARGERS, DOMAIN, PARAM_ALLOW_CHARGING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up the switch for one charger."""
    _LOGGER.debug("Setting up switch for %s", config_entry.data[CONF_NAME])
    charger = hass.data[DOMAIN][DATA_CHARGERS][config_entry.data[CONF_SERIAL]]
    async_add_entities([GoeChargerSwitch(hass, charger)])


class GoeChargerSwitch(GoeChargerBaseEntity, SwitchEntity):
    """Switch that allows or blocks charging (API parameter alw)."""

    def __init__(self, hass: core.HomeAssistant, charger: ChargerData) -> None:
        super().__init__(charger)
        self._hass = hass
        self.entity_id = f"switch.goecharger_{charger.name}_allow_charging"
        self._attr_name = charger.name

    @property
    def unique_id(self) -> str:
        """Return the unique_id of the switch."""
        return f"{self._charger.name}_allow_charging"

    @property
    def is_on(self) -> bool:
        """Return True when charging is allowed (alw == 1)."""
        return (self._charger.status or {}).get("allow_charging") == "on"

    async def async_turn_on(self, **kwargs) -> None:
        """Allow charging."""
        _LOGGER.debug("Allowing charging on %s", self._charger.name)
        await async_publish_command(self._hass, self._charger, PARAM_ALLOW_CHARGING, 1)

    async def async_turn_off(self, **kwargs) -> None:
        """Block charging."""
        _LOGGER.debug("Blocking charging on %s", self._charger.name)
        await async_publish_command(self._hass, self._charger, PARAM_ALLOW_CHARGING, 0)
