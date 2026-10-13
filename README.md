# Nuki MQTT Events

Nuki MQTT Events is a Home Assistant custom integration for exposing Nuki device events received over MQTT as Home Assistant entities.

It is designed to be installed and updated using HACS (Home Assistant Community Store) from a custom repository.

## Features

- Connects to an MQTT topic containing Nuki device payloads
- Parses Nuki event messages from the MQTT feed
- Creates a Home Assistant state sensor for the current device state
- Creates a battery sensor for the device battery percentage
- Creates a connectivity binary sensor
- Uses the device name from the MQTT payload when available

## Supported MQTT message format

This integration expects messages in the Nuki key/value format, for example:

```text
▼ 4CFF3164
connected = true
timestamp = 2026-10-13T17:45:01Z
deviceType = 5
name = Backdoor
firmware = 5.9.4
batteryChargeState = 100
batteryCritical = false
batteryCharging = false
keypadBatteryCritical = false
doorSensorBatteryCritical = false
state = 3
mode = 2
lockActionEvent = 0,0,87501,8192,1
```

The integration converts values such as:
- `true` / `false` to boolean values
- numeric values to integers/floats
- `state` to a HA-friendly state like `locked`, `unlocked`, `unlatched`, or `disconnected`

## Installation in Home Assistant with HACS

1. Open Home Assistant.
2. Go to Settings > Devices & Services > Helpers or simply open the HACS integration.
3. In HACS, click the three-dot menu and choose Custom repositories.
4. Add the repository as follows:
   - Repository: `koenraadhaedens/nuki-mqtt-events`
   - Category: `Integration`
5. Click Add.
6. Open HACS > Integrations.
7. Search for `Nuki MQTT Events`.
8. Click Install.
9. Restart Home Assistant.
10. Go to Settings > Devices & Services > Add Integration and search for `Nuki MQTT Events`.
11. Enter the MQTT topic that contains your Nuki event payloads, for example:
   - `nuki/event`

## MQTT setup

This integration depends on the built-in Home Assistant MQTT integration.

Before using it, make sure:
- MQTT is enabled in Home Assistant
- your Nuki bridge or MQTT broker is publishing messages to the configured topic

## Example entity naming

If the MQTT payload includes a device name such as `Backdoor`, the integration will create entities like:

- `sensor.backdoor_state`
- `sensor.backdoor_battery`
- `binary_sensor.backdoor_connection`

## Versioning

This project follows semantic versioning:

- `MAJOR.MINOR.PATCH`
- Example: `0.1.0`

The project uses GitHub Releases for published builds.

## License

MIT
