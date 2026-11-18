"""Sensor platform for the go-eCharger MQTT integration."""

import logging

from homeassistant import config_entries, core
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)

from .base_entity import GoeChargerBaseEntity
from .charger import ChargerData
from .const import CONF_NAME, CONF_SERIAL, DATA_CHARGERS, DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_ID = "Card ID"

_SENSOR_UNITS = {
    "charger_temp": {"unit": UnitOfTemperature.CELSIUS, "name": "Charger Temp"},
    "charger_temp0": {"unit": UnitOfTemperature.CELSIUS, "name": "Charger Temp 0"},
    "charger_temp1": {"unit": UnitOfTemperature.CELSIUS, "name": "Charger Temp 1"},
    "charger_temp2": {"unit": UnitOfTemperature.CELSIUS, "name": "Charger Temp 2"},
    "charger_temp3": {"unit": UnitOfTemperature.CELSIUS, "name": "Charger Temp 3"},
    "p_l1": {"unit": UnitOfPower.KILO_WATT, "name": "Power L1"},
    "p_l2": {"unit": UnitOfPower.KILO_WATT, "name": "Power L2"},
    "p_l3": {"unit": UnitOfPower.KILO_WATT, "name": "Power L3"},
    "p_n": {"unit": UnitOfPower.KILO_WATT, "name": "Power N"},
    "p_all": {"unit": UnitOfPower.KILO_WATT, "name": "Power All"},
    "current_session_charged_energy": {
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "name": "Current Session charged",
    },
    "current_session_charged_energy_corrected": {
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "name": "Current Session charged corrected",
    },
    "energy_total": {"unit": UnitOfEnergy.KILO_WATT_HOUR, "name": "Total Charged"},
    "energy_total_corrected": {
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "name": "Total Charged corrected",
    },
    "charge_limit": {"unit": UnitOfEnergy.KILO_WATT_HOUR, "name": "Charge limit"},
    "u_l1": {"unit": UnitOfElectricPotential.VOLT, "name": "Voltage L1"},
    "u_l2": {"unit": UnitOfElectricPotential.VOLT, "name": "Voltage L2"},
    "u_l3": {"unit": UnitOfElectricPotential.VOLT, "name": "Voltage L3"},
    "u_n": {"unit": UnitOfElectricPotential.VOLT, "name": "Voltage N"},
    "i_l1": {"unit": UnitOfElectricCurrent.AMPERE, "name": "Current L1"},
    "i_l2": {"unit": UnitOfElectricCurrent.AMPERE, "name": "Current L2"},
    "i_l3": {"unit": UnitOfElectricCurrent.AMPERE, "name": "Current L3"},
    "charger_temporary_max_current": {
        "unit": UnitOfElectricCurrent.AMPERE,
        "name": "Charger temporary current setting",
    },
    "charger_max_current": {
        "unit": UnitOfElectricCurrent.AMPERE,
        "name": "Charger max current setting",
    },
    "charger_absolute_max_current": {
        "unit": UnitOfElectricCurrent.AMPERE,
        "name": "Charger absolute max current setting",
    },
    "cable_lock_mode": {"unit": None, "name": "Cable lock mode"},
    "cable_max_current": {"unit": UnitOfElectricCurrent.AMPERE, "name": "Cable max current"},
    "unlocked_by_card": {"unit": CARD_ID, "name": "Card used"},
    "lf_l1": {"unit": PERCENTAGE, "name": "Power factor L1"},
    "lf_l2": {"unit": PERCENTAGE, "name": "Power factor L2"},
    "lf_l3": {"unit": PERCENTAGE, "name": "Power factor L3"},
    "lf_n": {"unit": PERCENTAGE, "name": "Loadfactor N"},
    "car_status": {"unit": None, "name": "Status"},
}

_SENSOR_STATE_CLASS = {
    "energy_total": SensorStateClass.TOTAL_INCREASING,
    "energy_total_corrected": SensorStateClass.TOTAL_INCREASING,
    "current_session_charged_energy": SensorStateClass.TOTAL_INCREASING,
    "current_session_charged_energy_corrected": SensorStateClass.TOTAL_INCREASING,
}

_SENSOR_DEVICE_CLASS = {
    "energy_total": SensorDeviceClass.ENERGY,
    "energy_total_corrected": SensorDeviceClass.ENERGY,
    "current_session_charged_energy": SensorDeviceClass.ENERGY,
    "current_session_charged_energy_corrected": SensorDeviceClass.ENERGY,
}

_SENSORS = [
    "car_status",
    "charger_temporary_max_current",
    "charger_max_current",
    "charger_absolute_max_current",
    "charger_err",
    "charger_access",
    "stop_mode",
    "cable_lock_mode",
    "cable_max_current",
    "pre_contactor_l1",
    "pre_contactor_l2",
    "pre_contactor_l3",
    "post_contactor_l1",
    "post_contactor_l2",
    "post_contactor_l3",
    "charger_temp",
    "charger_temp0",
    "charger_temp1",
    "charger_temp2",
    "charger_temp3",
    "current_session_charged_energy",
    "current_session_charged_energy_corrected",
    "charge_limit",
    "adapter",
    "unlocked_by_card",
    "energy_total",
    "energy_total_corrected",
    "wifi",
    "u_l1",
    "u_l2",
    "u_l3",
    "u_n",
    "i_l1",
    "i_l2",
    "i_l3",
    "p_l1",
    "p_l2",
    "p_l3",
    "p_n",
    "p_all",
    "lf_l1",
    "lf_l2",
    "lf_l3",
    "lf_n",
    "firmware",
    "serial_number",
    "wifi_ssid",
    "wifi_enabled",
    "timezone_offset",
    "timezone_dst_offset",
]


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Set up the sensors for one charger."""
    _LOGGER.debug("Setting up sensors for %s", config_entry.data[CONF_NAME])
    charger = hass.data[DOMAIN][DATA_CHARGERS][config_entry.data[CONF_SERIAL]]
    _LOGGER.debug("Adding %d sensors for charger %s", len(_SENSORS), charger.name)
    async_add_entities(GoeChargerSensor(charger, attribute) for attribute in _SENSORS)


class GoeChargerSensor(GoeChargerBaseEntity, SensorEntity):
    """Sensor for a single attribute of a go-eCharger."""

    def __init__(self, charger: ChargerData, attribute: str) -> None:
        super().__init__(charger)
        self._attribute = attribute
        meta = _SENSOR_UNITS.get(attribute)
        self.entity_id = f"sensor.goecharger_{charger.name}_{attribute}"
        self._attr_name = meta["name"] if meta else attribute
        self._attr_native_unit_of_measurement = meta["unit"] if meta else None
        self._attr_state_class = _SENSOR_STATE_CLASS.get(attribute)
        self._attr_device_class = _SENSOR_DEVICE_CLASS.get(attribute)

    @property
    def unique_id(self) -> str:
        """Return the unique_id of the sensor."""
        return f"{self._charger.name}_{self._attribute}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        status = self._charger.status or {}
        attribute = self._attribute
        if attribute == "energy_total_corrected":
            return round(
                status.get("energy_total", 0) * self._charger.correction_factor, 5
            )
        if attribute == "current_session_charged_energy_corrected":
            return round(
                status.get("current_session_charged_energy", 0)
                * self._charger.correction_factor,
                5,
            )
        if attribute not in status:
            return None
        return status[attribute]
