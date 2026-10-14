# Nuki MQTT Events

Nuki MQTT Events is a Home Assistant custom integration for exposing Nuki device events received over MQTT as Home Assistant entities.

It is designed to be installed and updated using HACS (Home Assistant Community Store) from a custom repository.

## Features

- Connects to the Nuki MQTT namespace automatically
- Subscribes to MQTT events under the default `nuki/#` topic pattern
- Parses Nuki event messages from the MQTT feed
- Creates sensors for state, device name, device type, last update, firmware, battery percentage, mode, raw lock action event, and a readable last action
- Creates binary sensors for connectivity, battery critical, battery charging, keypad battery critical, and door-sensor battery critical
- Creates an independent entity set for every Nuki device found under the subscribed topic

## Supported MQTT message format

The integration supports a complete multiline Nuki key/value payload, as well as MQTT brokers that publish each field on its own topic (for example, `nuki/4CFF3164/connected` with payload `true`). Example complete payload:

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
- `lockActionEvent` to a readable value such as `Unlock by Koenraad via app` or `Unlock by Koenraad via keypad`

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
11. The integration automatically subscribes to the Nuki MQTT namespace and does not require a manual topic entry.

## MQTT setup

This integration depends on the built-in Home Assistant MQTT integration.

Before using it, make sure:
- MQTT is enabled in Home Assistant
- your Nuki bridge or MQTT broker is publishing messages under the Nuki MQTT namespace, typically `nuki/#`

### Naming app and keypad users

The `lockActionEvent` payload is `action,trigger,authorization ID,code ID,detail`.
App users normally use the authorization ID, while keypad users use the code ID.
Keep the mappings in a dedicated file by adding this to `configuration.yaml`:

```yaml
nuki_mqtt_events: !include nuki_mqtt_events.yaml
```

Then create `nuki_mqtt_events.yaml` in the same Home Assistant configuration
directory. You can add as many authorization IDs and code IDs as needed:

```yaml
authorization_names:
  "87501": Koenraad
  "87502": Alice
  "87503": Bob

code_names:
  "8192": Koenraad
  "8193": Alice
  "8194": Cleaner
```

Restart Home Assistant after changing these mappings. Trigger the lock once and inspect
the `authorization_id` and `code_id` attributes of the `Last action` sensor to discover
the IDs. The sensor also exposes the decoded action, trigger, source, and keypad input
type as attributes.

## Entities

For the sample payload above, the integration creates up to 14 entities: nine sensors and five binary sensors. Entities are created when their values are first published. The `State` sensor maps the numeric Nuki `state` value to a readable state, while `Last action` decodes the five-part `lockActionEvent`. The raw event remains available as `Lock action event`. Each boolean field is available as its own binary sensor. The device name is exposed as the `Device name` sensor.

Each Nuki device gets its own Home Assistant device and entity set. Entity names use the `name` value from the MQTT payload when available, such as `Backdoor State`. Until a name is received, the integration uses the device segment of the MQTT topic, such as `4CFF3164 State`. This prevents messages from multiple Nuki devices under `nuki/#` from overwriting one another.

## Versioning

This project follows semantic versioning:

- `MAJOR.MINOR.PATCH`
- Example: `0.1.0`

The project uses GitHub Releases for published builds.

## License

MIT
