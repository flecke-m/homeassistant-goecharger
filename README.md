# Home Assistant integration for the go-eCharger

A Home Assistant custom integration for monitoring and controlling go-eCharger devices through the **local MQTT interface of API Version 1**. The charger publishes its status and the integration sends commands over MQTT; no HTTP polling or cloud connection is used.

## Features

- Charger status and electrical measurements as Home Assistant sensors
- Switch to allow or block charging
- Native number entity for the charge limit (0–20 kWh, 0.5 kWh steps)
- Native select entity for maximum charging current: **6, 8, 10, 12, 14 or 16 A**
- Existing services for setting the temporary current, absolute maximum current and cable lock mode
- MQTT push updates; entities synchronize automatically with the charger's reported status
- Optional correction factor for energy measurements

## Installation

### Home Assistant Marketplace

On Home Assistant 2026.11 and newer, the community store is built in as the **Marketplace**.

1. Open **Settings → Marketplace**.
2. Select **Add from link**.
3. Enter this repository URL: `https://github.com/flecke-m/homeassistant-goecharger`.
4. Add and install **go-eCharger** from the repository page.
5. Make sure the **MQTT** integration is configured and connected to the broker used by the charger.
6. Add the integration under **Settings → Devices & Services → Add Integration → go-eCharger**.

The Marketplace uses the repository's `hacs.json` metadata file; its filename remains unchanged. On Home Assistant versions before 2026.11, install the integration through HACS as a custom repository (Integration).

### Manual installation

1. Download or clone this repository.
2. Copy `custom_components/goecharger` into the `custom_components` directory of your Home Assistant configuration.
3. Restart Home Assistant.
4. Make sure the MQTT integration is configured and connected.
5. Add **go-eCharger** under **Settings → Devices & Services → Add Integration**.

## Configure the charger

Enable the MQTT API on the charger and configure it to connect to your MQTT broker. The integration listens for status messages on:

```text
go-eCharger/{serial}/status
```

Commands are published to:

```text
go-eCharger/{serial}/cmd/req
```

The serial number is the charger's 6-digit serial number. The MQTT integration in Home Assistant must be connected to the same broker.

Add the charger through the integration UI using its name and serial number. Multiple chargers can be added independently. The optional correction factor can be adjusted in the integration options.

A YAML import is also supported for existing installations:

```yaml
goecharger:
  chargers:
    - name: charger1
      serial: "123456"
      correction_factor: "1.0"
```

## Charge controls

The integration creates the following entities for each configured charger:

| Entity | Type | Description |
| --- | --- | --- |
| `number.goecharger_{name}_charge_limit` | Number | Charge limit in kWh, in 0.5 kWh increments from 0 to 20 (0 disables the limit) |
| `select.goecharger_{name}_max_current` | Select | Maximum current: 6, 8, 10, 12, 14 or 16 A |
| `sensor.goecharger_{name}_charge_limit` | Sensor | Read-only measurement of the charge limit reported by the charger |
| `switch.goecharger_{name}_allow_charging` | Switch | Allow or block charging |

Replace `{name}` with the charger name configured in the integration. The number and select entities publish changes directly over MQTT. Incoming charger status messages update their displayed values automatically; no separate `input_number`, `input_select` or automations are required.

The 16 A maximum-current selection is intentionally limited to the supported values above. This does not change the separate absolute-current or temporary-current services.

## Dashboard example

Add the entities to an Entities card in a Lovelace dashboard (replace `mycharger` with your configured charger name):

```yaml
type: entities
title: go-eCharger
show_header_toggle: false
entities:
  - entity: switch.goecharger_mycharger_allow_charging
  - entity: number.goecharger_mycharger_charge_limit
  - entity: select.goecharger_mycharger_max_current
  - entity: sensor.goecharger_mycharger_car_status
  - entity: sensor.goecharger_mycharger_charger_temp
  - entity: sensor.goecharger_mycharger_current_session_charged_energy
  - entity: sensor.goecharger_mycharger_p_all
```

## Services

The integration also provides services under the `goecharger` domain:

- `set_max_current`
- `set_temporary_max_current`
- `set_absolute_max_current`
- `set_charge_limit`
- `set_cable_lock_mode`

Each service accepts an optional `charger_name`. If omitted, the command is sent to all configured chargers. The native charge-control entities are the recommended way to change the regular charge limit and maximum current.

## Notes

- MQTT must be enabled on the charger and configured to publish to the broker used by Home Assistant.
- The integration uses local MQTT push updates and does not poll the charger over HTTP.
- Existing sensor and switch entities and the service interface are retained.
