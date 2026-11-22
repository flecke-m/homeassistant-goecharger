"""MQTT based integration for the go-eCharger.

No HTTP polling: the charger (firmware >= 030 with the "custom MQTT
server" enabled) pushes its status object every 5 seconds to
``go-eCharger/{serial}/status`` and commands are published to
``go-eCharger/{serial}/cmd/req`` as ``param=value``.

See: https://github.com/goecharger/go-eCharger-API-v1
"""

import json
import logging
from functools import partial

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components import mqtt
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .charger import ChargerData, async_publish_command
from .const import (
    ATTR_ABSOLUTE_MAX_CURRENT,
    ATTR_CABLE_LOCK_MODE,
    ATTR_CHARGE_LIMIT,
    ATTR_CHARGER_NAME,
    ATTR_MAX_CURRENT,
    CONF_CHARGERS,
    CONF_CORRECTION_FACTOR,
    CONF_NAME,
    CONF_SERIAL,
    DATA_CHARGERS,
    DATA_UNSUBSCRIBERS,
    DOMAIN,
    MAX_CURRENT,
    MIN_CURRENT,
    MQTT_TOPIC_STATUS,
    PARAM_ABSOLUTE_MAX_CURRENT,
    PARAM_CABLE_LOCK_MODE,
    PARAM_CHARGE_LIMIT,
    PARAM_MAX_CURRENT,
    PARAM_TEMPORARY_MAX_CURRENT,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_NAME): cv.string,
                vol.Optional(CONF_SERIAL): cv.string,
                vol.Optional(CONF_CORRECTION_FACTOR, default="1.0"): cv.string,
                vol.Optional(CONF_CHARGERS): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required(CONF_NAME): cv.string,
                                vol.Required(CONF_SERIAL): cv.string,
                                vol.Optional(
                                    CONF_CORRECTION_FACTOR, default="1.0"
                                ): cv.string,
                            }
                        )
                    ],
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

SCHEMA_SET_CURRENT = vol.Schema(
    {
        vol.Optional(ATTR_CHARGER_NAME): cv.string,
        vol.Required(ATTR_MAX_CURRENT): vol.Any(int, cv.string),
    }
)

SCHEMA_SET_ABSOLUTE_MAX_CURRENT = vol.Schema(
    {
        vol.Optional(ATTR_CHARGER_NAME): cv.string,
        vol.Required(ATTR_ABSOLUTE_MAX_CURRENT): vol.Any(int, cv.string),
    }
)

SCHEMA_SET_CABLE_LOCK_MODE = vol.Schema(
    {
        vol.Optional(ATTR_CHARGER_NAME): cv.string,
        vol.Required(ATTR_CABLE_LOCK_MODE): vol.Any(int, cv.string),
    }
)

SCHEMA_SET_CHARGE_LIMIT = vol.Schema(
    {
        vol.Optional(ATTR_CHARGER_NAME): cv.string,
        vol.Required(ATTR_CHARGE_LIMIT): vol.Any(float, int, cv.string),
    }
)


def _parse_correction_factor(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        _LOGGER.warning("Can't parse correction factor '%s', using 1.0", value)
        return 1.0


def _entry_config(entry) -> dict:
    """Config entry data with (newer) options layered on top."""
    return {**entry.data, **entry.options}


@callback
def _async_status_handler(hass, charger, message):
    """Handle a status message from go-eCharger/{serial}/status."""
    try:
        data = json.loads(message.payload)
    except (TypeError, ValueError) as err:
        _LOGGER.warning("Ignoring invalid status message for %s: %s", charger.name, err)
        return
    if not isinstance(data, dict) or not data:
        _LOGGER.warning("Ignoring unexpected status message for %s", charger.name)
        return
    _LOGGER.debug("Status update for charger %s", charger.name)
    charger.update(data)


async def _async_resolve(hass, raw, *, cast, field):
    """Resolve a service value given as number, numeric string or entity id."""
    if isinstance(raw, bool):
        raise vol.Invalid(f"Invalid value for '{field}': {raw}")
    if isinstance(raw, str):
        raw = raw.strip()
        if cv.match_entity_id(raw):
            state = hass.states.get(raw)
            if state is None:
                raise vol.Invalid(f"Entity '{raw}' not found")
            raw = state.state
    try:
        return cast(raw)
    except (TypeError, ValueError) as err:
        raise vol.Invalid(f"Invalid value for '{field}': {raw}") from err


async def _async_set_for_chargers(hass, charger_name, param, value):
    """Publish a command to one or all configured chargers."""
    chargers = hass.data[DOMAIN][DATA_CHARGERS]
    targets = [
        charger
        for charger in chargers.values()
        if not charger_name or charger.name == charger_name
    ]
    if charger_name and not targets:
        _LOGGER.error("Charger with name '%s' not found!", charger_name)
        return
    for charger in targets:
        await async_publish_command(hass, charger, param, value)


async def async_handle_set_temporary_max_current(hass, call):
    """Set the temporary max current (amx), e.g. for PV charging."""
    value = await _async_resolve(
        hass, call.data[ATTR_MAX_CURRENT], cast=int, field=ATTR_MAX_CURRENT
    )
    value = max(MIN_CURRENT, min(MAX_CURRENT, value))
    _LOGGER.debug("Set temporary max current to %d A", value)
    await _async_set_for_chargers(
        hass, call.data.get(ATTR_CHARGER_NAME), PARAM_TEMPORARY_MAX_CURRENT, value
    )


async def async_handle_set_max_current(hass, call):
    """Set the max current (amp)."""
    value = await _async_resolve(
        hass, call.data[ATTR_MAX_CURRENT], cast=int, field=ATTR_MAX_CURRENT
    )
    value = max(MIN_CURRENT, min(MAX_CURRENT, value))
    _LOGGER.debug("Set max current to %d A", value)
    await _async_set_for_chargers(
        hass, call.data.get(ATTR_CHARGER_NAME), PARAM_MAX_CURRENT, value
    )


async def async_handle_set_absolute_max_current(hass, call):
    """Set the absolute max current (ama)."""
    value = await _async_resolve(
        hass,
        call.data[ATTR_ABSOLUTE_MAX_CURRENT],
        cast=int,
        field=ATTR_ABSOLUTE_MAX_CURRENT,
    )
    value = max(MIN_CURRENT, min(MAX_CURRENT, value))
    _LOGGER.debug("Set absolute max current to %d A", value)
    await _async_set_for_chargers(
        hass,
        call.data.get(ATTR_CHARGER_NAME),
        PARAM_ABSOLUTE_MAX_CURRENT,
        value,
    )


async def async_handle_set_cable_lock_mode(hass, call):
    """Set the cable lock mode (ust: 0=unlocked, 1=automatic, 2=locked)."""
    value = await _async_resolve(
        hass,
        call.data[ATTR_CABLE_LOCK_MODE],
        cast=int,
        field=ATTR_CABLE_LOCK_MODE,
    )
    if value not in (0, 1, 2):
        _LOGGER.error("Invalid cable lock mode %s (must be 0, 1 or 2)", value)
        return
    await _async_set_for_chargers(
        hass, call.data.get(ATTR_CHARGER_NAME), PARAM_CABLE_LOCK_MODE, value
    )


async def async_handle_set_charge_limit(hass, call):
    """Set the charge limit in kWh (dwo, stored in 0.1 kWh steps)."""
    value = await _async_resolve(
        hass, call.data[ATTR_CHARGE_LIMIT], cast=float, field=ATTR_CHARGE_LIMIT
    )
    if value < 0:
        value = 0
    dwo = int(round(value * 10))
    _LOGGER.debug("Set charge limit to %s kWh (dwo=%d)", value, dwo)
    await _async_set_for_chargers(
        hass, call.data.get(ATTR_CHARGER_NAME), PARAM_CHARGE_LIMIT, dwo
    )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up go-eCharger services and import YAML configured chargers."""
    _LOGGER.debug("Setting up go-eCharger (MQTT)")

    data = hass.data.setdefault(DOMAIN, {})
    data.setdefault(DATA_CHARGERS, {})
    data.setdefault(DATA_UNSUBSCRIBERS, {})

    hass.services.async_register(
        DOMAIN,
        "set_temporary_max_current",
        async_handle_set_temporary_max_current,
        schema=SCHEMA_SET_CURRENT,
    )
    hass.services.async_register(
        DOMAIN, "set_max_current", async_handle_set_max_current, schema=SCHEMA_SET_CURRENT
    )
    hass.services.async_register(
        DOMAIN,
        "set_absolute_max_current",
        async_handle_set_absolute_max_current,
        schema=SCHEMA_SET_ABSOLUTE_MAX_CURRENT,
    )
    hass.services.async_register(
        DOMAIN,
        "set_cable_lock_mode",
        async_handle_set_cable_lock_mode,
        schema=SCHEMA_SET_CABLE_LOCK_MODE,
    )
    hass.services.async_register(
        DOMAIN,
        "set_charge_limit",
        async_handle_set_charge_limit,
        schema=SCHEMA_SET_CHARGE_LIMIT,
    )

    if DOMAIN not in config:
        return True

    domain_config = config[DOMAIN]
    charger_configs = list(domain_config.get(CONF_CHARGERS) or [])

    # Single charger shorthand:
    #   goecharger:
    #     name: mycharger
    #     serial: "123456"
    if not charger_configs and domain_config.get(CONF_SERIAL):
        serial = str(domain_config[CONF_SERIAL]).strip()
        charger_configs = [
            {
                CONF_NAME: domain_config.get(CONF_NAME) or serial,
                CONF_SERIAL: serial,
                CONF_CORRECTION_FACTOR: domain_config.get(
                    CONF_CORRECTION_FACTOR, "1.0"
                ),
            }
        ]

    for charger_config in charger_configs:
        _LOGGER.debug("Importing charger %s", charger_config)
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=dict(charger_config),
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up go-eCharger from a config entry (subscribes to the status topic)."""
    _LOGGER.debug("Setting up config entry for %s", entry.title)

    if mqtt.DOMAIN not in hass.config.components:
        raise ConfigEntryNotReady(
            "The MQTT integration is not set up. "
            "Configure 'mqtt' in configuration.yaml first."
        )

    config = _entry_config(entry)
    serial = config[CONF_SERIAL]

    data = hass.data.setdefault(DOMAIN, {})
    chargers = data.setdefault(DATA_CHARGERS, {})
    unsubscribers = data.setdefault(DATA_UNSUBSCRIBERS, {})

    charger = chargers.get(serial)
    if charger is None:
        charger = ChargerData(
            name=config[CONF_NAME],
            serial=serial,
            correction_factor=_parse_correction_factor(
                config.get(CONF_CORRECTION_FACTOR)
            ),
        )
        chargers[serial] = charger
    else:
        charger.name = config[CONF_NAME]
        charger.correction_factor = _parse_correction_factor(
            config.get(CONF_CORRECTION_FACTOR)
        )

    topic = MQTT_TOPIC_STATUS.format(serial=serial)
    _LOGGER.debug("Subscribing to %s", topic)
    unsubscribe = await mqtt.async_subscribe(
        hass, topic, partial(_async_status_handler, hass, charger)
    )
    entry.async_on_unload(unsubscribe)
    unsubscribers[entry.entry_id] = unsubscribe

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.SELECT]
    )
    return True


async def _async_update_listener(hass, entry):
    """Handle options update."""
    _LOGGER.debug("Reloading config entry for %s", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload a config entry: unsubscribe from MQTT and drop the charger."""
    _LOGGER.debug("Unloading config entry for %s", entry.title)

    if not await hass.config_entries.async_unload_platforms(
        entry, [Platform.SENSOR, Platform.SWITCH]
    ):
        return False

    data = hass.data.get(DOMAIN) or {}
    unsubscribers = data.get(DATA_UNSUBSCRIBERS, {})
    unsubscribe = unsubscribers.pop(entry.entry_id, None)
    if unsubscribe is not None:
        unsubscribe()

    serial = _entry_config(entry).get(CONF_SERIAL)
    still_in_use = any(
        other.entry_id != entry.entry_id
        and _entry_config(other).get(CONF_SERIAL) == serial
        for other in hass.config_entries.async_entries(DOMAIN)
    )
    if serial is not None and not still_in_use:
        charger = data.get(DATA_CHARGERS, {}).pop(serial, None)
        if charger is not None:
            charger.clear_listeners()

    if not data.get(DATA_CHARGERS) and not data.get(DATA_UNSUBSCRIBERS):
        hass.data.pop(DOMAIN, None)

    return True
