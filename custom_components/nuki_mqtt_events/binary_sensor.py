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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC, DEFAULT_TOPIC, DOMAIN
from .parser import device_key, device_label, parse_nuki_event


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
    """Set up binary sensors as Nuki devices publish values."""
    topic = config_entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
    manager = NukiBinarySensorManager(config_entry.entry_id, async_add_entities)
    unsubscribe = await mqtt.async_subscribe(
        hass,
        topic,
        manager.async_handle_mqtt_message,
        qos=0,
    )
    config_entry.async_on_unload(unsubscribe)


class NukiBinarySensorManager:
    """Create and update a separate binary sensor set for every Nuki device."""

    def __init__(
        self,
        entry_id: str,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize the binary sensor manager."""
        self._entry_id = entry_id
        self._async_add_entities = async_add_entities
        self._entities: dict[tuple[str, str], NukiPayloadBinarySensor] = {}
        self._labels: dict[str, str] = {}

    async def async_handle_mqtt_message(self, message) -> None:
        """Route an MQTT message to the matching device binary sensors."""
        payload = parse_nuki_event(message.payload, message.topic)
        key = device_key(payload, message.topic)

        name = payload.get("name")
        if isinstance(name, str) and name.strip():
            self._labels[key] = name.strip()
            for (entity_key, _), entity in self._entities.items():
                if entity_key == key:
                    entity.update_device_label(name.strip())
        else:
            self._labels.setdefault(key, device_label(payload))

        new_entities = []
        for description in BINARY_SENSORS:
            value = payload.get(description.payload_key)
            if not isinstance(value, bool):
                continue

            entity_id = (key, description.key)
            entity = self._entities.get(entity_id)
            if entity is None:
                entity = NukiPayloadBinarySensor(
                    self._entry_id,
                    key,
                    self._labels[key],
                    description,
                )
                self._entities[entity_id] = entity
                new_entities.append(entity)
            entity.update_value(value, write_state=entity not in new_entities)

        if new_entities:
            self._async_add_entities(new_entities)


class NukiPayloadBinarySensor(BinarySensorEntity):
    """Expose one boolean field from the latest Nuki MQTT payload."""

    _attr_has_entity_name = False

    def __init__(
        self,
        entry_id: str,
        device_key: str,
        device_label: str,
        description: NukiBinarySensorDescription,
    ) -> None:
        """Initialize the payload binary sensor."""
        self._entry_id = entry_id
        self._device_key = device_key
        self._device_label = device_label
        self.entity_description = description
        self._attr_name = f"{device_label} {description.name}"
        self._attr_unique_id = f"{entry_id}_{device_key}_{description.key}"
        self._attr_is_on = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the Home Assistant device associated with this sensor."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_{self._device_key}")},
            name=self._device_label,
            manufacturer="Nuki",
        )

    def update_device_label(self, label: str) -> None:
        """Apply a more useful device name learned from an MQTT payload."""
        if label == self._device_label:
            return
        self._device_label = label
        self._attr_name = f"{label} {self.entity_description.name}"
        if self.hass is not None:
            self.async_write_ha_state()

    def update_value(self, value: bool, *, write_state: bool) -> None:
        """Update the binary sensor value."""
        self._attr_is_on = value
        if write_state:
            self.async_write_ha_state()
