"""Sensor platform for the Nuki MQTT Events integration."""

from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_BATTERY_CHARGE_STATE,
    ATTR_BATTERY_CRITICAL,
    ATTR_BATTERY_CHARGING,
    CONF_TOPIC,
    DEFAULT_TOPIC,
)
from .parser import device_label, parse_nuki_event


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    topic = config_entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
    async_add_entities(
        [
            NukiMqttEventSensor(config_entry.entry_id, topic),
            NukiMqttBatterySensor(config_entry.entry_id, topic),
        ]
    )


class NukiMqttEventSensor(SensorEntity):
    """Represent the latest Nuki device state."""

    _attr_has_entity_name = True

    def __init__(self, entry_id: str, topic: str) -> None:
        self._entry_id = entry_id
        self._topic = topic
        self._device_name = "Nuki"
        self._attr_name = "State"
        self._attr_unique_id = f"{entry_id}_state"
        self._attr_native_value = "unknown"
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT events when the entity is added."""
        await mqtt.async_subscribe(
            self.hass,
            self._topic,
            self._handle_mqtt_message,
            qos=0,
        )
        await super().async_added_to_hass()

    async def _handle_mqtt_message(self, message) -> None:
        """Update the sensor state and attributes with the latest payload."""
        payload = parse_nuki_event(message.payload)
        self._device_name = device_label(payload)
        self._attr_name = f"{self._device_name} State"
        self._attr_unique_id = f"{self._device_name.lower().replace(' ', '_')}_state"
        self._attr_native_value = payload.get("event", "unknown")
        self._attr_extra_state_attributes = {
            key: value for key, value in payload.items() if key not in {"event"}
        }
        self.async_write_ha_state()

    @property
    def icon(self):
        """Return the state icon."""
        return "mdi:lock"


class NukiMqttBatterySensor(SensorEntity):
    """Represent the Nuki battery charge state."""

    _attr_has_entity_name = True

    def __init__(self, entry_id: str, topic: str) -> None:
        self._entry_id = entry_id
        self._topic = topic
        self._device_name = "Nuki"
        self._attr_name = "Battery"
        self._attr_unique_id = f"{entry_id}_battery"
        self._attr_device_class = "battery"
        self._attr_native_unit_of_measurement = "%"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT events when the entity is added."""
        await mqtt.async_subscribe(
            self.hass,
            self._topic,
            self._handle_mqtt_message,
            qos=0,
        )
        await super().async_added_to_hass()

    async def _handle_mqtt_message(self, message) -> None:
        """Update the battery percentage and related metadata."""
        payload = parse_nuki_event(message.payload)
        self._device_name = device_label(payload)
        self._attr_name = f"{self._device_name} Battery"
        self._attr_unique_id = f"{self._device_name.lower().replace(' ', '_')}_battery"
        charge = payload.get(ATTR_BATTERY_CHARGE_STATE)
        self._attr_native_value = charge if isinstance(charge, (int, float)) else None
        self._attr_extra_state_attributes = {
            ATTR_BATTERY_CRITICAL: payload.get(ATTR_BATTERY_CRITICAL, False),
            ATTR_BATTERY_CHARGING: payload.get(ATTR_BATTERY_CHARGING, False),
            "device_id": payload.get("device_id"),
            "device_name": payload.get("name"),
        }
        self.async_write_ha_state()

    @property
    def icon(self):
        """Return the battery icon."""
        return "mdi:battery"
