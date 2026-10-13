"""Binary sensor platform for the Nuki MQTT Events integration."""

from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_CONNECTED, CONF_TOPIC, DEFAULT_TOPIC, DOMAIN
from .parser import device_label, parse_nuki_event


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities from a config entry."""
    topic = config_entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
    async_add_entities([NukiMqttConnectionBinarySensor(config_entry.entry_id, topic)])


class NukiMqttConnectionBinarySensor(BinarySensorEntity):
    """Represent the Nuki device connected state."""

    _attr_has_entity_name = True

    def __init__(self, entry_id: str, topic: str) -> None:
        self._entry_id = entry_id
        self._topic = topic
        self._device_name = "Nuki"
        self._attr_name = "Connection"
        self._attr_unique_id = f"{entry_id}_connection"
        self._attr_is_on = False
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
        """Update the connection status and extra attributes from the latest payload."""
        payload = parse_nuki_event(message.payload)
        self._device_name = device_label(payload)
        self._attr_name = f"{self._device_name} Connection"
        self._attr_unique_id = f"{self._device_name.lower().replace(' ', '_')}_connection"
        self._attr_is_on = bool(payload.get(ATTR_CONNECTED, False))
        self._attr_extra_state_attributes = {
            key: value for key, value in payload.items() if key != "event"
        }
        self.async_write_ha_state()

    @property
    def icon(self):
        """Return the connection icon."""
        return "mdi:connection"
