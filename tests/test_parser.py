"""Tests for Nuki MQTT payload parsing."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest


PARSER_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "nuki_mqtt_events"
    / "parser.py"
)
SPEC = spec_from_file_location("nuki_mqtt_events_parser", PARSER_PATH)
assert SPEC is not None and SPEC.loader is not None
PARSER = module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)


class ParseLockActionEventTest(unittest.TestCase):
    """Verify readable lock action event decoding."""

    def test_app_authorization_name(self) -> None:
        result = PARSER.parse_lock_action_event(
            "1,0,87501,0,0", {"87501": "Koenraad"}
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Unlock by Koenraad via app")
        self.assertEqual(result["authorization_id"], 87501)

    def test_keypad_code_name(self) -> None:
        result = PARSER.parse_lock_action_event(
            [1, 0, 87501, 8192, 1],
            {"87501": "Administrator"},
            {"8192": "Koenraad"},
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "Unlock by Koenraad via keypad")
        self.assertEqual(result["keypad_source"], "code")

    def test_invalid_event_is_ignored(self) -> None:
        self.assertIsNone(PARSER.parse_lock_action_event("1,2,3"))
        self.assertIsNone(PARSER.parse_lock_action_event("1,2,user,4,5"))


class ParseStateTest(unittest.TestCase):
    """Keep sensor labels aligned with the native MQTT lock state codes."""

    def test_native_state_labels(self) -> None:
        for code, label in {
            0: "uncalibrated",
            1: "locked",
            2: "unlocking",
            3: "unlocked",
            4: "locking",
            5: "unlatched",
            6: "unlocked_lock_n_go",
            7: "unlatching",
            253: "boot_run",
            254: "motor_blocked",
            255: "undefined",
            999: "unknown",
        }.items():
            with self.subTest(code=code):
                result = PARSER.parse_nuki_event(str(code), "nuki/ABC/state")
                self.assertEqual(result["event"], label)


if __name__ == "__main__":
    unittest.main()
