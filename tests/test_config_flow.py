"""Tests for preventing duplicate Nuki MQTT Events config entries."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


INTEGRATION_PATH = (
    Path(__file__).parents[1] / "custom_components" / "nuki_mqtt_events"
)


class ConfigFlowStub:
    """Allow loading the flow without installing Home Assistant."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()


def load_config_flow():
    """Load the real config flow with only its framework imports stubbed."""
    package_name = "nuki_mqtt_events_test"
    package = ModuleType(package_name)
    package.__path__ = [str(INTEGRATION_PATH)]
    homeassistant = ModuleType("homeassistant")
    homeassistant.config_entries = SimpleNamespace(
        ConfigFlow=ConfigFlowStub, OptionsFlow=object
    )
    flow_module_name = f"{package_name}.config_flow"
    spec = spec_from_file_location(
        flow_module_name, INTEGRATION_PATH / "config_flow.py"
    )
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {
            package_name: package,
            "homeassistant": homeassistant,
            "homeassistant.data_entry_flow": ModuleType(
                "homeassistant.data_entry_flow"
            ),
            "voluptuous": ModuleType("voluptuous"),
        },
    ):
        sys.modules["homeassistant.data_entry_flow"].FlowResult = dict
        spec.loader.exec_module(module)
    return module


class ConfigFlowTest(unittest.IsolatedAsyncioTestCase):
    """Verify first-time setup and rejection of existing entries."""

    def setUp(self) -> None:
        self.flow = load_config_flow().NukiMqttEventsConfigFlow()
        self.flow._async_current_entries = Mock(return_value=[])
        self.flow.async_create_entry = Mock(
            side_effect=lambda **kwargs: {"type": "create_entry", **kwargs}
        )
        self.flow.async_abort = Mock(
            side_effect=lambda **kwargs: {"type": "abort", **kwargs}
        )

    async def test_first_setup_creates_entry(self) -> None:
        result = await self.flow.async_step_user()

        self.assertEqual(
            result,
            {
                "type": "create_entry",
                "title": "Nuki MQTT Events",
                "data": {"topic": "nuki/#"},
            },
        )
        self.flow.async_abort.assert_not_called()

    async def test_existing_entry_aborts(self) -> None:
        for unique_id in (None, "nuki_mqtt_events"):
            with self.subTest(unique_id=unique_id):
                self.flow._async_current_entries.return_value = [
                    SimpleNamespace(unique_id=unique_id)
                ]

                result = await self.flow.async_step_user()

                self.assertEqual(
                    result, {"type": "abort", "reason": "already_configured"}
                )
                self.flow.async_create_entry.assert_not_called()


if __name__ == "__main__":
    unittest.main()
