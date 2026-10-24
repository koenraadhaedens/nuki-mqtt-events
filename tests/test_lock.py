"""Tests for MQTT lock discovery, state, availability, and command safety."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch


INTEGRATION_PATH = (
    Path(__file__).parents[1] / "custom_components" / "nuki_mqtt_events"
)


class LockEntityStub:
    """Stub only the Home Assistant base entity, not integration behavior."""

    hass = None

    def async_write_ha_state(self):
        """Record state writes in place of Home Assistant's state machine."""
        self.state_writes = getattr(self, "state_writes", 0) + 1


class HomeAssistantErrorStub(Exception):
    """Stand in for the Home Assistant service error."""


def load_lock():
    """Load the real lock platform with framework imports stubbed."""
    package_name = "nuki_mqtt_events_lock_test"
    package = ModuleType(package_name)
    package.__path__ = [str(INTEGRATION_PATH)]
    modules = {
        name: ModuleType(name)
        for name in (
            "homeassistant",
            "homeassistant.components",
            "homeassistant.components.mqtt",
            "homeassistant.components.lock",
            "homeassistant.config_entries",
            "homeassistant.core",
            "homeassistant.exceptions",
            "homeassistant.helpers",
            "homeassistant.helpers.device_registry",
            "homeassistant.helpers.entity_platform",
        )
    }
    modules[package_name] = package
    mqtt = modules["homeassistant.components.mqtt"]
    mqtt.async_publish = AsyncMock()
    mqtt.async_subscribe = AsyncMock(return_value=Mock())
    mqtt.async_subscribe_connection_status = Mock(return_value=Mock())
    mqtt.is_connected = Mock(return_value=True)
    modules["homeassistant.components"].mqtt = mqtt
    modules["homeassistant.components.lock"].LockEntity = LockEntityStub
    modules["homeassistant.config_entries"].ConfigEntry = object
    modules["homeassistant.core"].HomeAssistant = object
    modules["homeassistant.core"].callback = lambda method: method
    modules["homeassistant.exceptions"].HomeAssistantError = HomeAssistantErrorStub
    modules["homeassistant.helpers.device_registry"].DeviceInfo = dict
    modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = object
    spec = spec_from_file_location(
        f"{package_name}.lock", INTEGRATION_PATH / "lock.py"
    )
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


class NukiLockTest(unittest.IsolatedAsyncioTestCase):
    """Exercise actual platform logic without a broker or physical lock."""

    def setUp(self) -> None:
        self.platform = load_lock()
        self.entities = []
        self.manager = self.platform.NukiLockManager(
            "entry", self.entities.extend, True
        )

    async def message(self, topic, payload, *, retain=False):
        await self.manager.async_handle_mqtt_message(
            SimpleNamespace(topic=topic, payload=payload, retain=retain)
        )

    async def discover(self, device="ABC"):
        await self.message(f"nuki/{device}/state", "1", retain=True)
        entity = self.entities[-1]
        entity.hass = object()
        return entity

    async def test_setup_registers_subscription_and_cleanup_without_commands(self):
        hass = object()
        entry = SimpleNamespace(
            entry_id="entry", data={}, async_on_unload=Mock()
        )
        await self.platform.async_setup_entry(hass, entry, self.entities.extend)

        subscribe = self.platform.mqtt.async_subscribe
        self.assertEqual(subscribe.await_args.args[:2], (hass, "nuki/#"))
        self.assertEqual(subscribe.await_args.kwargs, {"qos": 0})
        entry.async_on_unload.assert_any_call(subscribe.return_value)
        entry.async_on_unload.assert_any_call(
            self.platform.mqtt.async_subscribe_connection_status.return_value
        )
        self.platform.mqtt.async_publish.assert_not_awaited()

    async def test_separate_devices_metadata_and_retained_discovery(self):
        await self.message("nuki/ABC/name", "Backdoor")
        await self.message("nuki/ABC/connected", "false")
        self.assertEqual(self.entities, [])
        backdoor = await self.discover()
        frontdoor = await self.discover("DEF")

        self.assertEqual(len(self.entities), 2)
        self.assertEqual(backdoor._attr_name, "Backdoor Lock")
        self.assertEqual(frontdoor._attr_name, "DEF Lock")
        self.assertEqual(backdoor._attr_unique_id, "entry_ABC_lock")
        self.assertEqual(
            backdoor.device_info["identifiers"],
            {("nuki_mqtt_events", "entry_ABC")},
        )
        self.assertFalse(backdoor._attr_available)
        self.assertTrue(frontdoor._attr_available)
        await self.message("nuki/ABC/state", "3")
        await self.message("nuki/ABC/name", "Garden")
        self.assertEqual(len(self.entities), 2)
        self.assertEqual(backdoor._attr_name, "Garden Lock")
        self.assertFalse(backdoor._attr_is_locked)
        self.assertTrue(frontdoor._attr_is_locked)
        self.platform.mqtt.async_publish.assert_not_awaited()

    async def test_multiline_and_json_payloads_with_independent_command_topics(self):
        await self.message(
            "nuki/ABC", "name = Backdoor\nstate = 3\nconnected = true"
        )
        await self.message(
            "custom/nuki/DEF",
            '{"name": "Frontdoor", "state": 1, "connected": true}',
        )
        self.assertEqual(self.entities[0].command_topic, "nuki/ABC/lockAction")
        self.assertEqual(
            self.entities[1].command_topic, "custom/nuki/DEF/lockAction"
        )
        self.assertFalse(self.entities[0]._attr_is_locked)
        self.assertTrue(self.entities[1]._attr_is_locked)

    async def test_native_state_codes_and_unknown_states(self):
        entity = await self.discover()
        for code, locked, locking, unlocking, jammed in (
            (1, True, False, False, False),
            (2, None, False, True, False),
            (3, False, False, False, False),
            (4, None, True, False, False),
            (5, False, False, False, False),
            (6, False, False, False, False),
            (7, None, False, True, False),
            (254, None, False, False, True),
            (0, None, False, False, False),
            (253, None, False, False, False),
            (255, None, False, False, False),
            (999, None, False, False, False),
        ):
            with self.subTest(code=code):
                await self.message("nuki/ABC/state", str(code))
                self.assertEqual(entity._attr_is_locked, locked)
                self.assertEqual(entity._attr_is_locking, locking)
                self.assertEqual(entity._attr_is_unlocking, unlocking)
                self.assertEqual(entity._attr_is_jammed, jammed)
                self.assertEqual(
                    entity._attr_extra_state_attributes, {"nuki_state_code": code}
                )

    async def test_unrelated_messages_and_command_echo_do_not_change_state(self):
        entity = await self.discover()
        for topic, payload in (
            ("nuki/ABC/batteryChargeState", "80"),
            ("nuki/ABC/lockAction", "1"),
            ("nuki/ABC/lockActionEvent", "1,172,0,0,0"),
            ("nuki/XYZ/lockAction", "2"),
            ("nuki/ABC/name", "Backdoor"),
        ):
            await self.message(topic, payload)
        self.assertTrue(entity._attr_is_locked)
        self.assertEqual(len(self.entities), 1)
        self.platform.mqtt.async_publish.assert_not_awaited()

    async def test_invalid_state_clears_old_confirmation_and_logs(self):
        entity = await self.discover()
        for payload in ("true", "false", "1.5", "broken"):
            with self.subTest(payload=payload):
                with self.assertLogs(self.platform.__name__, level="WARNING"):
                    await self.message("nuki/ABC/state", payload)
                self.assertIsNone(entity._attr_is_locked)
        self.platform.mqtt.async_publish.assert_not_awaited()

    async def test_unsafe_or_conflicting_topics_are_rejected(self):
        entity = await self.discover()
        for topic, payload in (
            ("state", "1"),
            ("nuki//ABC/state", "1"),
            ("nuki/+/ABC/state", "1"),
            ("nuki/#/ABC/state", "1"),
            ("nuki/ABC", "\u25bc DEF\nstate = 1"),
            ("other/ABC/state", "1"),
        ):
            with self.subTest(topic=topic):
                with self.assertLogs(self.platform.__name__, level="WARNING"):
                    await self.message(topic, payload)
        self.assertEqual(len(self.entities), 1)
        self.assertEqual(entity.command_topic, "nuki/ABC/lockAction")

    async def test_commands_use_correct_device_payload_qos_and_no_retain(self):
        entity = await self.discover()
        await self.discover("DEF")
        await entity.async_unlock()
        self.platform.mqtt.async_publish.assert_awaited_once_with(
            entity.hass, "nuki/ABC/lockAction", "1", qos=0, retain=False
        )
        self.assertTrue(entity._attr_is_locked)
        await self.message("nuki/ABC/state", "3")
        self.assertFalse(entity._attr_is_locked)
        self.platform.mqtt.async_publish.reset_mock()
        await entity.async_lock()
        self.platform.mqtt.async_publish.assert_awaited_once_with(
            entity.hass, "nuki/ABC/lockAction", "2", qos=0, retain=False
        )
        self.assertFalse(entity._attr_is_locked)

    async def test_device_and_broker_availability_block_offline_commands(self):
        entity = await self.discover()
        await self.message("nuki/ABC/connected", "false")
        self.assertFalse(entity._attr_available)
        with self.assertRaisesRegex(HomeAssistantErrorStub, "offline"):
            await entity.async_unlock()

        self.manager.async_connection_status_changed(False)
        await self.message("nuki/ABC/connected", "true")
        self.assertFalse(entity._attr_available)
        with self.assertRaisesRegex(HomeAssistantErrorStub, "offline"):
            await entity.async_lock()
        self.manager.async_connection_status_changed(True)
        self.assertTrue(entity._attr_available)
        self.assertTrue(entity._attr_is_locked)

        self.platform.mqtt.is_connected.return_value = False
        with self.assertRaisesRegex(HomeAssistantErrorStub, "offline"):
            await entity.async_unlock()
        self.platform.mqtt.async_publish.assert_not_awaited()

    async def test_publish_failure_propagates_without_changing_state(self):
        entity = await self.discover()
        self.platform.mqtt.async_publish.side_effect = HomeAssistantErrorStub(
            "publish failed"
        )
        with self.assertRaisesRegex(HomeAssistantErrorStub, "publish failed"):
            await entity.async_unlock()
        self.assertTrue(entity._attr_is_locked)


if __name__ == "__main__":
    unittest.main()
