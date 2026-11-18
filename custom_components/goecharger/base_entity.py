"""Base entity shared by the go-eCharger sensors and switch."""

from homeassistant.helpers.entity import Entity

from .charger import ChargerData
from .const import DOMAIN


class GoeChargerBaseEntity(Entity):
    """Entity that is driven by the MQTT status updates of one charger."""

    _attr_should_poll = False

    def __init__(self, charger: ChargerData) -> None:
        self._charger = charger

    async def async_added_to_hass(self) -> None:
        self._charger.add_listener(self._async_on_status_update)

    async def async_will_remove_from_hass(self) -> None:
        self._charger.remove_listener(self._async_on_status_update)

    def _async_on_status_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """The entity is available once the first status arrived."""
        return self._charger.status is not None

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self._charger.name)},
            "name": self._charger.name,
            "manufacturer": "go-e",
            "model": "HOME",
        }
