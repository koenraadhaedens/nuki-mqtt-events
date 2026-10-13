"""Binary sensor platform for the Nuki MQTT Events integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC, DEFAULT_TOPIC
from .parser import parse_nuki_event


@dataclass(frozen=True)
class NukiBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a boolean value published in a Nuki MQTT payload."""

    payload_key: str = ""


BINARY_SENSORS = (
    NukiBinarySensorDescription(
        key="connected",
        name="Connected",
        icon="mdi:connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        payload_key="connected",
    ),
    NukiBinarySensorDescription(
        key="battery_critical",
        name="Battery critical",
        device_class=BinarySensorDeviceClass.BATTERY,
        payload_key="batteryCritical",
    ),
    NukiBinarySensorDescription(
        key="battery_charging",
        name="Battery charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        payload_key="batteryCharging",
    ),
    NukiBinarySensorDescription(
        key="keypad_battery_critical",
        name="Keypad battery critical",
        device_class=BinarySensorDeviceClass.BATTERY,
        payload_key="keypadBatteryCritical",
    ),
    NukiBinarySensorDescription(
        key="door_sensor_battery_critical",
        name="Door sensor battery critical",
        device_class=BinarySensorDeviceClass.BATTERY,
        payload_key="doorSensorBatteryCritical",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors for boolean Nuki payload fields."""
    topic = config_entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
    async_add_entities(
        NukiPayloadBinarySensor(config_entry.entry_id, topic, description)
        for description in BINARY_SENSORS
    )


class NukiPayloadBinarySensor(BinarySensorEntity):
    """Expose one boolean field from the latest Nuki MQTT payload."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        topic: str,
        description: NukiBinarySensorDescription,
    ) -> None:
        """Initialize the payload binary sensor."""
        self._topic = topic
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_is_on = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to the configured Nuki MQTT topic."""
        await super().async_added_to_hass()
        self.async_on_remove(
            await mqtt.async_subscribe(
                self.hass,
                self._topic,
                self._handle_mqtt_message,
                qos=0,
            )
        )

    async def _handle_mqtt_message(self, message) -> None:
        """Update the binary sensor from the latest payload."""
        payload = parse_nuki_event(message.payload)
        value = payload.get(self.entity_description.payload_key)
        self._attr_is_on = value if isinstance(value, bool) else None
        self.async_write_ha_state()
