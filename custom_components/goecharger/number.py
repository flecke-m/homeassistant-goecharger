"""Number platform for go-eCharger charge controls."""

import logging

from homeassistant import config_entries, core
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfEnergy

from .base_entity import GoeChargerBaseEntity
from .charger import ChargerData, async_publish_command
from .const import CONF_NAME, CONF_SERIAL, DATA_CHARGERS, DOMAIN, PARAM_CHARGE_LIMIT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
) -> None:
    """Set up charge-control numbers for one charger."""
    charger = hass.data[DOMAIN][DATA_CHARGERS][config_entry.data[CONF_SERIAL]]
    async_add_entities([GoeChargerChargeLimitNumber(hass, charger)])


class GoeChargerChargeLimitNumber(GoeChargerBaseEntity, NumberEntity):
    """Set the charge limit in kWh."""

    _attr_native_min_value = 0
    _attr_native_max_value = 20
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:battery-charging"

    def __init__(self, hass: core.HomeAssistant, charger: ChargerData) -> None:
        super().__init__(charger)
        self._hass = hass
        self.entity_id = f"number.goecharger_{charger.name}_charge_limit"
        self._attr_name = f"{charger.name} Charge limit"

    @property
    def unique_id(self) -> str:
        """Return a stable unique ID."""
        return f"{self._charger.name}_charge_limit_number"

    @property
    def native_value(self) -> float | None:
        """Return the latest charge limit reported by the charger."""
        value = (self._charger.status or {}).get("charge_limit")
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Publish the charge limit in 0.1 kWh units (0.5 kWh UI steps)."""
        value = max(0.0, min(20.0, float(value)))
        dwo = int(round(value * 10))
        _LOGGER.debug("Setting charge limit for %s to %.1f kWh", self._charger.name, value)
        await async_publish_command(self._hass, self._charger, PARAM_CHARGE_LIMIT, dwo)
