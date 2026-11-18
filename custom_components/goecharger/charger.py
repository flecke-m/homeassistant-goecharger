"""Per-charger state and MQTT command publishing for the go-eCharger.

A single charger (identified by its serial number) is represented by one
ChargerData object. It stores the latest status object, hands it to all
entities that are interested, and is used as the target for commands.
"""

import logging

from homeassistant.components import mqtt

from .const import MQTT_TOPIC_COMMAND

_LOGGER = logging.getLogger(__name__)

# Text values for the status codes, see "Parameter" in the
# go-eCharger API v1 documentation.
_CAR_STATUS = {
    "1": "Charger ready, no vehicle",
    "2": "charging",
    "3": "Waiting for vehicle",
    "4": "charging finished, vehicle still connected",
}
_ERR = {
    "0": "OK",
    "1": "RCCB",
    "3": "PHASE",
    "8": "NO_GROUND",
    "10": "INTERNAL",
}
_ACCESS = {
    "0": "free",
    "1": "rfid/app",
    "2": "cost based / automatic",
}
_ADAPTER = {
    "0": "No Adapter",
    "1": "16A-Adapter",
}
_STOP_MODE = {
    "0": "manual",
    "2": "kWh based",
}


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _index_or_zero(array, index):
    """Return array[index], or 0 when the array is missing/too short."""
    try:
        return array[index]
    except (IndexError, TypeError):
        return 0


def _on_off(flag):
    return "on" if flag else "off"


def map_status(raw):
    """Map a raw go-eCharger status object to friendly sensor values.

    Field names, units and conversions follow the official go-eCharger
    API v1 documentation ("Parameter" section), e.g.:

    - dws: charged energy in deca-watt seconds (-> /360000 = kWh)
    - dwo: shutdown value in 0.1 kWh (-> /10 = kWh)
    - eto: total charged energy in 0.1 kWh (-> /10 = kWh)
    - nrg[4..6]: amperage in 0.1 A, nrg[7..10]: power in 0.1 kW,
      nrg[11]: total power in 0.01 kW
    - tof: time zone in hours + 100 (101 == GMT+1)
    - pha: binary flags 0b00ABCDEF for the phases in front of (A/B/C)
      and behind (D/E/F) the contactors
    """
    if not isinstance(raw, dict) or not raw:
        return {}

    nrg = raw.get("nrg") or []
    tma = raw.get("tma") or []

    try:
        pha = int(raw.get("pha", 0))
    except (TypeError, ValueError):
        pha = 0
    pre_l3 = pha & 0x20
    pre_l2 = pha & 0x10
    pre_l1 = pha & 0x08
    post_l3 = pha & 0x04
    post_l2 = pha & 0x02
    post_l1 = pha & 0x01

    wifi_state = raw.get("wst")
    if wifi_state is None:
        wifi = "unknown"
    elif str(wifi_state) == "3":
        wifi = "connected"
    else:
        wifi = "not connected"

    if str(raw.get("wen")) == "1":
        wifi_enabled = "on"
    elif str(raw.get("wen")) == "0":
        wifi_enabled = "off"
    else:
        wifi_enabled = "unknown"

    if str(raw.get("alw")) == "1":
        allow_charging = "on"
    elif str(raw.get("alw")) == "0":
        allow_charging = "off"
    else:
        allow_charging = "unknown"

    temperatures = [_index_or_zero(tma, index) for index in range(4)]
    if tma:
        # Newer firmware reports the individual temperatures in "tma";
        # charger_temp is the average of the four probes.
        charger_temp = round(sum(float(t) for t in temperatures) / 4, 2)
    else:
        # Older firmware only reports a single controller temperature.
        charger_temp = _int(raw.get("tmp", 0))

    return {
        "car_status": _CAR_STATUS.get(str(raw.get("car")), "unknown"),
        "charger_max_current": _int(raw.get("amp")),
        "charger_temporary_max_current": _int(raw.get("amx")),
        "charger_absolute_max_current": _int(raw.get("ama")),
        "charger_err": _ERR.get(str(raw.get("err")), "UNKNOWN"),
        "charger_access": _ACCESS.get(str(raw.get("ast")), "unknown"),
        "allow_charging": allow_charging,
        "stop_mode": _STOP_MODE.get(str(raw.get("stp")), "unknown"),
        "cable_lock_mode": _int(raw.get("ust")),
        "cable_max_current": _int(raw.get("cbl")),
        "pre_contactor_l1": _on_off(pre_l1),
        "pre_contactor_l2": _on_off(pre_l2),
        "pre_contactor_l3": _on_off(pre_l3),
        "post_contactor_l1": _on_off(post_l1),
        "post_contactor_l2": _on_off(post_l2),
        "post_contactor_l3": _on_off(post_l3),
        "charger_temp": charger_temp,
        "charger_temp0": float(temperatures[0]),
        "charger_temp1": float(temperatures[1]),
        "charger_temp2": float(temperatures[2]),
        "charger_temp3": float(temperatures[3]),
        # dws is in deca-watt seconds: dws * 0.1 Ws / 3.6e6 Ws/kWh
        "current_session_charged_energy": round(_int(raw.get("dws")) / 360000.0, 5),
        # dwo is the shutdown value in 0.1 kWh
        "charge_limit": _int(raw.get("dwo")) / 10.0,
        "adapter": _ADAPTER.get(str(raw.get("adi")), "unknown"),
        "unlocked_by_card": _int(raw.get("uby")),
        # eto is the total charged energy in 0.1 kWh
        "energy_total": _int(raw.get("eto")) / 10.0,
        "wifi": wifi,
        "u_l1": _int(_index_or_zero(nrg, 0)),
        "u_l2": _int(_index_or_zero(nrg, 1)),
        "u_l3": _int(_index_or_zero(nrg, 2)),
        "u_n": _int(_index_or_zero(nrg, 3)),
        "i_l1": _int(_index_or_zero(nrg, 4)) / 10.0,
        "i_l2": _int(_index_or_zero(nrg, 5)) / 10.0,
        "i_l3": _int(_index_or_zero(nrg, 6)) / 10.0,
        "p_l1": _int(_index_or_zero(nrg, 7)) / 10.0,
        "p_l2": _int(_index_or_zero(nrg, 8)) / 10.0,
        "p_l3": _int(_index_or_zero(nrg, 9)) / 10.0,
        "p_n": _int(_index_or_zero(nrg, 10)) / 10.0,
        "p_all": _int(_index_or_zero(nrg, 11)) / 100.0,
        "lf_l1": _int(_index_or_zero(nrg, 12)),
        "lf_l2": _int(_index_or_zero(nrg, 13)),
        "lf_l3": _int(_index_or_zero(nrg, 14)),
        "lf_n": _int(_index_or_zero(nrg, 15)),
        "firmware": raw.get("fwv", "unknown"),
        "serial_number": raw.get("sse", "unknown"),
        "wifi_ssid": raw.get("wss", "unknown"),
        "wifi_enabled": wifi_enabled,
        # tof is the time zone in hours + 100 (101 == GMT+1)
        "timezone_offset": _int(raw.get("tof", 100)) - 100,
        "timezone_dst_offset": _int(raw.get("tds")),
    }


class ChargerData:
    """Latest status of a single charger and the entities watching it."""

    def __init__(self, name, serial, correction_factor=1.0):
        self.name = name
        self.serial = serial
        self.correction_factor = correction_factor
        self.status = None
        self._listeners = set()

    def add_listener(self, listener):
        self._listeners.add(listener)

    def remove_listener(self, listener):
        self._listeners.discard(listener)

    def clear_listeners(self):
        self._listeners.clear()

    def update(self, raw_status):
        """Store a new raw status object and wake up the entities."""
        self.status = map_status(raw_status)
        for listener in list(self._listeners):
            listener()


async def async_publish_command(hass, charger, param, value):
    """Publish a `param=value` command to the charger's command topic."""
    topic = MQTT_TOPIC_COMMAND.format(serial=charger.serial)
    payload = f"{param}={value}"
    _LOGGER.debug("Publishing %s to %s", payload, topic)
    await mqtt.async_publish(hass, topic, payload, qos=0)
