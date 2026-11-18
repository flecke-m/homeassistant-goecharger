"""Config flow for the go-eCharger MQTT integration."""

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_CORRECTION_FACTOR, CONF_NAME, CONF_SERIAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The serial number is 6 digits (the charger formats it as %06d) and is
# part of the MQTT topics.
_SERIAL_PATTERN = re.compile(r"^\d{6}$")


def _user_schema(current: dict[str, Any] | None = None) -> vol.Schema:
    current = current or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=current.get(CONF_NAME, "")): str,
            vol.Required(CONF_SERIAL, default=current.get(CONF_SERIAL, "")): str,
            vol.Required(
                CONF_CORRECTION_FACTOR,
                default=current.get(CONF_CORRECTION_FACTOR, "1.0"),
            ): str,
        }
    )


def _normalize_serial(value: Any) -> str:
    return str(value or "").strip()


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for the go-eCharger."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Let the user add a charger: name + 6 digit serial number."""
        errors = {}
        if user_input is not None:
            serial = _normalize_serial(user_input.get(CONF_SERIAL))
            if not _SERIAL_PATTERN.match(serial):
                errors[CONF_SERIAL] = "invalid_serial"
            elif any(
                _normalize_serial(entry.data.get(CONF_SERIAL)) == serial
                for entry in self._async_current_entries()
            ):
                return self.async_abort(reason="already_configured")
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_SERIAL: serial,
                        CONF_CORRECTION_FACTOR: user_input[CONF_CORRECTION_FACTOR],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def async_step_import(self, info: dict) -> config_entries.FlowResult:
        """Import a charger configured in configuration.yaml.

        Matches the existing name-based identity so repeated imports do not
        duplicate entries created in the UI.
        """
        data = {
            CONF_NAME: info[CONF_NAME],
            CONF_SERIAL: _normalize_serial(info.get(CONF_SERIAL)),
            CONF_CORRECTION_FACTOR: info.get(CONF_CORRECTION_FACTOR, "1.0"),
        }
        for entry in self._async_current_entries():
            if entry.data.get(CONF_NAME) == data[CONF_NAME]:
                merged = {**entry.data, **data}
                if merged != entry.data:
                    self.hass.config_entries.async_update_entry(entry, data=merged)
                return self.async_abort(reason="already_configured")
        return self.async_create_entry(title=data[CONF_NAME], data=data)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for the go-eCharger."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage options for the go-eCharger component."""
        errors = {}
        if user_input is not None:
            serial = _normalize_serial(user_input.get(CONF_SERIAL))
            if not _SERIAL_PATTERN.match(serial):
                errors[CONF_SERIAL] = "invalid_serial"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_SERIAL: serial,
                        CONF_CORRECTION_FACTOR: user_input[CONF_CORRECTION_FACTOR],
                    },
                )

        # Falls back to the entry data when no options have been set yet.
        current = self.config_entry.options or self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=_user_schema(current),
            errors=errors,
        )
