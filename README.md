# Nuki MQTT Events

Nuki MQTT Events is a Home Assistant custom integration for exposing Nuki device events received over MQTT as Home Assistant entities.

It is designed to be installed and updated through the Home Assistant Community Store (HACS) as a custom repository.

> [!NOTE]
> This integration is not affiliated with or endorsed by Nuki. It is an independent, community-backed project based on publicly available documentation and APIs.

> [!IMPORTANT]
> This project was created primarily with the assistance of AI. It has been reviewed and tested by a professional programmer, but this disclosure is provided for transparency.

## Features

- Automatically subscribes to the default `nuki/#` MQTT topic pattern
- Supports complete multiline payloads and values published on individual topics
- Creates sensors for state, device name, device type, last update, firmware, battery percentage, mode, raw lock action event, and readable last action
- Creates binary sensors for connectivity, battery critical, battery charging, keypad battery critical, and door-sensor battery critical
- Creates an independent Home Assistant device and entity set for every Nuki device

## Prerequisites

Before installing the integration:

1. Configure the built-in [Home Assistant MQTT integration](https://www.home-assistant.io/integrations/mqtt/).
2. Enable MQTT for your Nuki device in the Nuki app.
3. Confirm that your Nuki bridge or MQTT broker publishes messages under the Nuki MQTT namespace, typically `nuki/#`.

## Installation with HACS

1. Open **HACS** in Home Assistant.
2. Select the three-dot menu and choose **Custom repositories**.
3. Enter `https://github.com/koenraadhaedens/nuki-mqtt-events` as the repository.
4. Select **Integration** as the category, then click **Add**.
5. In **HACS > Integrations**, search for **Nuki MQTT Events** and install it.
6. Restart Home Assistant.
7. Go to **Settings > Devices & services** and click **Add integration**.
8. Search for **Nuki MQTT Events** and complete the setup.

The integration automatically subscribes to the Nuki MQTT namespace; no manual topic entry is required.
Only one integration entry is allowed; it handles all Nuki devices. Adding it again
is blocked to prevent duplicate MQTT subscriptions and entities.

## Supported MQTT message formats

The integration supports complete multiline Nuki key/value payloads and brokers that publish each field on its own topic, such as `nuki/4CFF3164/connected` with the payload `true`.

Example complete payload:

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

The integration:

- `true` / `false` to boolean values
- converts numeric values to integers or floating-point numbers
- maps `state` to a Home Assistant-friendly value such as `locked`, `unlocked`, `unlatched`, or `disconnected`
- decodes `lockActionEvent` into a readable value such as `Unlock by Koenraad via app` or `Unlock by Koenraad via keypad`

## Naming app and keypad users

The `lockActionEvent` payload uses the format `action,trigger,authorization ID,code ID,detail`. App users normally use the authorization ID, while keypad users use the code ID.

To map these IDs to names, add the following to your Home Assistant `configuration.yaml`:

```yaml
nuki_mqtt_events: !include nuki_mqtt_events.yaml
```

Create `nuki_mqtt_events.yaml` in the same directory:

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

Add as many authorization and code IDs as needed, then restart Home Assistant. To discover the IDs, trigger the lock once and inspect the `authorization_id` and `code_id` attributes of the **Last action** sensor. This sensor also exposes the decoded action, trigger, source, and keypad input type as attributes.

An example configuration is available in [`examples/nuki_mqtt_events.yaml`](examples/nuki_mqtt_events.yaml).

## Entities

For the sample payload above, the integration creates up to 14 entities: nine sensors and five binary sensors. Entities are created when their values are first published.

![Nuki MQTT Events entities in Home Assistant](custom_components/nuki_mqtt_events/images/Screenshot-nuki-mqtt-events.png)

- **State** maps the numeric Nuki `state` value to a readable state.
- **Last action** decodes the five-part `lockActionEvent`.
- **Lock action event** retains the raw event.
- **Device name** exposes the name reported by Nuki.
- Each boolean field is available as its own binary sensor.

Each Nuki device gets its own Home Assistant device and entity set. Entity names use the `name` value from the MQTT payload when available, such as `Backdoor State`. Until a name is received, the integration uses the device segment of the MQTT topic, such as `4CFF3164 State`. This prevents messages from multiple Nuki devices from overwriting one another.

## Versioning

This project follows [semantic versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`) and uses GitHub Releases for published builds.

## License

MIT
