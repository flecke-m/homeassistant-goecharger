"""Constants for the go-eCharger MQTT integration."""

DOMAIN = "goecharger"

CONF_NAME = "name"
CONF_SERIAL = "serial"
CONF_CHARGERS = "chargers"
CONF_CORRECTION_FACTOR = "correction_factor"

# MQTT topics (see "Custom MQTT Server" in the go-eCharger API v1 docs).
# The 6 digit serial number of the charger is part of the topic.
MQTT_TOPIC_STATUS = "go-eCharger/{serial}/status"
MQTT_TOPIC_COMMAND = "go-eCharger/{serial}/cmd/req"

# Keys under hass.data[DOMAIN]
DATA_CHARGERS = "chargers"
DATA_UNSUBSCRIBERS = "unsubscribers"

# Service fields
ATTR_CHARGER_NAME = "charger_name"
ATTR_MAX_CURRENT = "max_current"
ATTR_CABLE_LOCK_MODE = "cable_lock_mode"
ATTR_ABSOLUTE_MAX_CURRENT = "charger_absolute_max_current"
ATTR_CHARGE_LIMIT = "charge_limit"

# go-eCharger API command parameters (API v1, "Commands")
PARAM_ALLOW_CHARGING = "alw"
PARAM_MAX_CURRENT = "amp"
PARAM_TEMPORARY_MAX_CURRENT = "amx"
PARAM_ABSOLUTE_MAX_CURRENT = "ama"
PARAM_CABLE_LOCK_MODE = "ust"
PARAM_CHARGE_LIMIT = "dwo"

# Charging current limits: whole ampere, 6-32A
MIN_CURRENT = 6
MAX_CURRENT = 32

# Cable lock modes (API parameter ust)
CABLE_LOCK_UNLOCKED = 0  # lock as long as the car is connected
CABLE_LOCK_AUTOMATIC = 1  # unlock automatically after charging
CABLE_LOCK_LOCKED = 2  # always keep the cable locked
