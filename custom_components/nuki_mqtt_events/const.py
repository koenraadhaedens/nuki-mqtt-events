"""Constants for the Nuki MQTT Events integration."""

DOMAIN = "nuki_mqtt_events"
PLATFORMS = ["sensor", "binary_sensor"]

CONF_TOPIC = "topic"
CONF_AUTHORIZATION_NAMES = "authorization_names"
CONF_CODE_NAMES = "code_names"
DEFAULT_TOPIC = "nuki/#"

DATA_AUTHORIZATION_NAMES = "authorization_names"
DATA_CODE_NAMES = "code_names"

ATTR_DEVICE_ID = "device_id"
ATTR_NAME = "name"
ATTR_STATE = "state"
ATTR_CONNECTED = "connected"
ATTR_BATTERY_CHARGE_STATE = "batteryChargeState"
ATTR_BATTERY_CRITICAL = "batteryCritical"
ATTR_BATTERY_CHARGING = "batteryCharging"
ATTR_DEVICE_TYPE = "deviceType"
ATTR_DEVICE_TYPE_NAME = "device_type"
