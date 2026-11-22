"""Select platform for go-eCharger current controls."""

import logging

from homeassistant import config_entries, core
from homeassistant.components.select import SelectEntity

from .base_entity import GoeChargerBaseEntity
from .charger import ChargerData, async_publish_command
from .const import CONF_SERIAL, DATA_CHARGERS, DOMAIN, PARAM_MAX_CURRENT

_LOGGER = logging.getLogger(__name__)

CURRENT_OPTIONS = ["6", "8", "10", "12", "14", "16"]


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
) -> None:
    """Set up current selection for one charger."""
    charger = hass.data[DOMAIN][DATA_CHARGERS][config_entry.data[CONF_SERIAL]]
    async_add_entities([GoeChargerMaxCurrentSelect(hass, charger)])


class GoeChargerMaxCurrentSelect(GoeChargerBaseEntity, SelectEntity):
    """Select the charger's maximum charging current."""

    _attr_options = CURRENT_OPTIONS
    _attr_icon = "mdi:current-ac"

    def __init__(self, hass: core.HomeAssistant, charger: ChargerData) -> None:
        super().__init__(charger)
        self._hass = hass
        self.entity_id = f"select.goecharger_{charger.name}_max_current"
        self._attr_name = f"{charger.name} Max current"

    @property
    def unique_id(self) -> str:
        """Return a stable unique ID."""
        return f"{self._charger.name}_max_current_select"

    @property
    def current_option(self) -> str | None:
        """Return the current setting if it is one of the supported options."""
        value = (self._charger.status or {}).get("charger_max_current")
        if value is None:
            return None
        option = str(value)
        return option if option in CURRENT_OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        """Publish a selected maximum current."""
        if option not in CURRENT_OPTIONS:
            raise ValueError(f"Unsupported maximum current: {option}")
        _LOGGER.debug("Setting max current for %s to %s A", self._charger.name, option)
        await async_publish_command(self._hass, self._charger, PARAM_MAX_CURRENT, int(option))
