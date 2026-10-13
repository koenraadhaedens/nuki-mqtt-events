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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC, DEFAULT_TOPIC
from .parser import parse_nuki_event


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
    """Set up all Nuki payload sensor entities."""
    topic = config_entry.data.get(CONF_TOPIC, DEFAULT_TOPIC)
    async_add_entities(
        NukiPayloadSensor(config_entry.entry_id, topic, description)
        for description in SENSORS
    )


class NukiPayloadSensor(SensorEntity):
    """Expose a single field from the latest Nuki MQTT payload."""

    _attr_has_entity_name = True

    def __init__(self, entry_id: str, topic: str, description: NukiSensorDescription) -> None:
        """Initialize the payload sensor."""
        self._topic = topic
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_icon = description.icon
        self._attr_native_value = None
        if description.native_unit_of_measurement is not None:
            self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        if description.device_class is not None:
            self._attr_device_class = description.device_class

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
        """Update this sensor from the latest payload."""
        payload = parse_nuki_event(message.payload)
        value = payload.get(self.entity_description.key)
        if self.entity_description.as_text and value is not None:
            value = ",".join(map(str, value)) if isinstance(value, list) else str(value)
        self._attr_native_value = value
        self._attr_extra_state_attributes = (
            {"nuki_state_code": payload.get("state")}
            if self.entity_description.key == "event"
            else {}
        )
        self.async_write_ha_state()
