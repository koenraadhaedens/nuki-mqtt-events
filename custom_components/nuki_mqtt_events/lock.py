"""Lock control for devices using the native Nuki MQTT API."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC, DEFAULT_TOPIC, DOMAIN
from .parser import NukiFieldNames, device_key, device_label, parse_nuki_event

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up lock entities as Nuki devices publish their state."""
    manager = NukiLockManager(
        config_entry.entry_id, async_add_entities, mqtt.is_connected(hass)
    )
    config_entry.async_on_unload(
        mqtt.async_subscribe_connection_status(
            hass, manager.async_connection_status_changed
        )
    )
    unsubscribe = await mqtt.async_subscribe(
        hass,
        config_entry.data.get(CONF_TOPIC, DEFAULT_TOPIC),
        manager.async_handle_mqtt_message,
        qos=0,
    )
    config_entry.async_on_unload(unsubscribe)


class NukiLockManager:
    """Discover locks and retain metadata arriving on separate MQTT topics."""

    def __init__(
        self,
        entry_id: str,
        async_add_entities: AddEntitiesCallback,
        broker_connected: bool,
    ) -> None:
        """Initialize the lock manager."""
        self._entry_id = entry_id
        self._async_add_entities = async_add_entities
        self._broker_connected = broker_connected
        self._entities: dict[str, NukiMqttLock] = {}
        self._payloads: dict[str, dict[str, object]] = {}

    @callback
    def async_connection_status_changed(self, connected: bool) -> None:
        """Update lock availability when Home Assistant loses its broker."""
        self._broker_connected = connected
        for entity in self._entities.values():
            entity.update_broker_connection(connected)

    async def async_handle_mqtt_message(self, message: mqtt.ReceiveMessage) -> None:
        """Create or update a lock without interpreting command echoes as state."""
        payload = parse_nuki_event(message.payload, message.topic)
        if not {"state", "name", "connected"}.intersection(payload):
            return

        parts = message.topic.split("/")
        if parts[-1].lower() in NukiFieldNames:
            parts = parts[:-1]
        key = device_key(payload, message.topic)
        if (
            len(parts) < 2
            or any(not part or "+" in part or "#" in part for part in parts)
            or parts[-1] != key
        ):
            _LOGGER.warning(
                "Cannot determine a safe Nuki command topic from %s", message.topic
            )
            return

        command_topic = "/".join((*parts, "lockAction"))
        entity = self._entities.get(key)
        if entity is not None and entity.command_topic != command_topic:
            _LOGGER.warning("Ignoring conflicting MQTT command topic for Nuki %s", key)
            return

        cached = self._payloads.setdefault(key, {})
        for field in ("state", "connected", "name"):
            if field not in payload:
                continue
            value = payload[field]
            if (
                (field == "state" and type(value) is int)
                or (field == "connected" and isinstance(value, bool))
                or (field == "name" and isinstance(value, str) and value.strip())
            ):
                cached[field] = value
            else:
                _LOGGER.warning("Invalid Nuki %s value on %s", field, message.topic)
                if field == "state":
                    cached.pop("state", None)

        is_new = entity is None
        if entity is None:
            if "state" not in cached:
                return
            entity = NukiMqttLock(
                self._entry_id,
                key,
                device_label({**cached, "device_id": key}),
                command_topic,
                self._broker_connected,
            )
            self._entities[key] = entity
        entity.update_payload(cached, write_state=not is_new)
        if is_new:
            self._async_add_entities([entity])


class NukiMqttLock(LockEntity):
    """Control a Nuki lock while using reported, not optimistic, state."""

    _attr_has_entity_name = False
    _attr_should_poll = False

    def __init__(
        self,
        entry_id: str,
        device_key: str,
        label: str,
        command_topic: str,
        broker_connected: bool,
    ) -> None:
        """Initialize a lock on the same device as its existing sensors."""
        self._entry_id = entry_id
        self._device_key = device_key
        self._device_label = label
        self.command_topic = command_topic
        self._broker_connected = broker_connected
        self._device_connected = True
        self._attr_name = f"{label} Lock"
        self._attr_unique_id = f"{entry_id}_{device_key}_lock"
        self._attr_available = broker_connected

    @property
    def device_info(self) -> DeviceInfo:
        """Return the shared Nuki device identity."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_{self._device_key}")},
            name=self._device_label,
            manufacturer="Nuki",
        )

    def update_payload(self, payload: dict[str, object], *, write_state: bool) -> None:
        """Apply native Nuki state codes and preserve unrelated values."""
        name = payload.get("name")
        if isinstance(name, str) and name.strip():
            self._device_label = name.strip()
            self._attr_name = f"{self._device_label} Lock"
        connected = payload.get("connected")
        if isinstance(connected, bool):
            self._device_connected = connected
        state = payload.get("state")
        self._attr_is_locked = state == 1 if state in (1, 3, 5, 6) else None
        self._attr_is_locking = state == 4
        self._attr_is_unlocking = state in (2, 7)
        self._attr_is_jammed = state == 254
        self._attr_available = self._broker_connected and self._device_connected
        self._attr_extra_state_attributes = {"nuki_state_code": state}
        if write_state and self.hass is not None:
            self.async_write_ha_state()

    @callback
    def update_broker_connection(self, connected: bool) -> None:
        """Refresh availability without changing the last reported lock state."""
        self._broker_connected = connected
        self._attr_available = connected and self._device_connected
        if self.hass is not None:
            self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        """Request locking; confirmation arrives on the state topic."""
        await self._async_send_action("2")

    async def async_unlock(self, **kwargs: Any) -> None:
        """Request unlocking without sending an unlatch command."""
        await self._async_send_action("1")

    async def _async_send_action(self, action: str) -> None:
        """Never retain commands or queue them while known to be offline."""
        if not self._attr_available or not mqtt.is_connected(self.hass):
            raise HomeAssistantError("Cannot control Nuki: device or MQTT broker is offline")
        await mqtt.async_publish(
            self.hass, self.command_topic, action, qos=0, retain=False
        )
