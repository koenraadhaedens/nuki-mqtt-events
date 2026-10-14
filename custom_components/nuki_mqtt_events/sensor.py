"""Sensor platform for the Nuki MQTT Events integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components import mqtt
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC, DEFAULT_TOPIC, DOMAIN
from .parser import device_key, device_label, parse_nuki_event


@dataclass(frozen=True)
class NukiSensorDescription(SensorEntityDescription):
    """Describe one value published in a Nuki MQTT payload."""

    as_text: bool = False


SENSORS = (
    NukiSensorDescription(key="event", name="State", icon="mdi:lock", as_text=True),
    NukiSensorDescription(key="name", name="Device name", icon="mdi:door", as_text=True),
    NukiSensorDescription(key="device_type", name="Device type", icon="mdi:devices", as_text=True),
    NukiSensorDescription(
        key="timestamp", name="Last update", icon="mdi:clock-outline", as_text=True
    ),
    NukiSensorDescription(
        key="firmware", name="Firmware", icon="mdi:information-outline", as_text=True
    ),
    NukiSensorDescription(
        key="batteryChargeState",
        name="Battery",
        icon="mdi:battery",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
    ),
    NukiSensorDescription(key="mode", name="Mode", icon="mdi:cog-outline"),
    NukiSensorDescription(
        key="lockActionEvent", name="Lock action event", icon="mdi:lock-clock", as_text=True
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Nuki payload sensors as devices publish values."""
    topic = config_entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
    manager = NukiSensorManager(config_entry.entry_id, async_add_entities)
    unsubscribe = await mqtt.async_subscribe(
        hass,
        topic,
        manager.async_handle_mqtt_message,
        qos=0,
    )
    config_entry.async_on_unload(unsubscribe)


class NukiSensorManager:
    """Create and update a separate sensor set for every Nuki device."""

    def __init__(
        self,
        entry_id: str,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize the sensor manager."""
        self._entry_id = entry_id
        self._async_add_entities = async_add_entities
        self._entities: dict[tuple[str, str], NukiPayloadSensor] = {}
        self._labels: dict[str, str] = {}

    async def async_handle_mqtt_message(self, message) -> None:
        """Route an MQTT message to the matching device sensors."""
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
        for description in SENSORS:
            value = payload.get(description.key)
            if value is None or (description.key == "event" and value == "unknown"):
                continue

            entity_id = (key, description.key)
            entity = self._entities.get(entity_id)
            if entity is None:
                entity = NukiPayloadSensor(
                    self._entry_id,
                    key,
                    self._labels[key],
                    description,
                )
                self._entities[entity_id] = entity
                new_entities.append(entity)
            entity.update_value(value, payload, write_state=entity not in new_entities)

        if new_entities:
            self._async_add_entities(new_entities)


class NukiPayloadSensor(SensorEntity):
    """Expose a single field from the latest Nuki MQTT payload."""

    _attr_has_entity_name = False

    def __init__(
        self,
        entry_id: str,
        device_key: str,
        device_label: str,
        description: NukiSensorDescription,
    ) -> None:
        """Initialize the payload sensor."""
        self._entry_id = entry_id
        self._device_key = device_key
        self._device_label = device_label
        self.entity_description = description
        self._attr_name = f"{device_label} {description.name}"
        self._attr_unique_id = f"{entry_id}_{device_key}_{description.key}"
        self._attr_icon = description.icon
        self._attr_native_value = None
        if description.native_unit_of_measurement is not None:
            self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        if description.device_class is not None:
            self._attr_device_class = description.device_class

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

    def update_value(
        self,
        value: object,
        payload: dict[str, object],
        *,
        write_state: bool,
    ) -> None:
        """Update this sensor from a parsed MQTT payload."""
        if self.entity_description.as_text and value is not None:
            value = ",".join(map(str, value)) if isinstance(value, list) else str(value)
        self._attr_native_value = value
        self._attr_extra_state_attributes = (
            {"nuki_state_code": payload.get("state")}
            if self.entity_description.key == "event"
            else {}
        )
        if write_state:
            self.async_write_ha_state()
