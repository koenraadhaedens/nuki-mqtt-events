"""Helpers for parsing Nuki MQTT event payloads."""

from __future__ import annotations

import re


NukiStateNames = {
    0: "unknown",
    1: "locked",
    2: "unlocked",
    3: "unlatched",
    4: "locking",
    5: "unlocking",
    6: "unlocked_lock_n_go",
    7: "unlatched_lock_n_go",
}

NukiDeviceTypes = {
    0: "unknown",
    1: "smart_lock",
    2: "smart_lock",
    3: "smart_lock",
    4: "smart_lock",
    5: "door",
    6: "door",
}


def device_label(parsed: dict[str, object]) -> str:
    """Return the most useful display label for the device."""
    if "name" in parsed and isinstance(parsed["name"], str) and parsed["name"].strip():
        return str(parsed["name"]).strip()
    if "device_id" in parsed and str(parsed["device_id"]).strip():
        return str(parsed["device_id"]).strip()
    return "Nuki"


def _coerce_value(value: str):
    """Convert a text value to a useful Python value."""
    cleaned = value.strip()
    if not cleaned:
        return ""

    lower = cleaned.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower in {"null", "none"}:
        return None

    if re.fullmatch(r"-?\d+", cleaned):
        return int(cleaned)

    if re.fullmatch(r"-?\d+\.\d+", cleaned):
        return float(cleaned)

    if "," in cleaned and all(part.strip().replace("-", "").isdigit() for part in cleaned.split(",")):
        return [int(part.strip()) for part in cleaned.split(",")]

    return cleaned


def _state_from_payload(parsed: dict[str, object]) -> str:
    """Convert a Nuki payload into a Home Assistant-friendly state."""
    if "state" in parsed and isinstance(parsed["state"], (int, float)):
        state_value = int(parsed["state"])
        state_name = NukiStateNames.get(state_value, "unknown")
        if state_name != "unknown":
            return state_name

    if "connected" in parsed and parsed["connected"] is False:
        return "disconnected"

    if "batteryChargeState" in parsed and isinstance(parsed["batteryChargeState"], (int, float)):
        charge = int(parsed["batteryChargeState"])
        if charge <= 10:
            return "battery_low"

    if "name" in parsed:
        return str(parsed["name"])

    if "device_id" in parsed:
        return str(parsed["device_id"])

    return "unknown"


def parse_nuki_event(raw: str | bytes | None) -> dict[str, object]:
    """Parse a raw Nuki MQTT payload into a structured dictionary."""
    if raw is None:
        return {"event": "unknown", "raw": ""}

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")

    text = raw.strip()
    if not text:
        return {"event": "unknown", "raw": ""}

    parsed: dict[str, object] = {"raw": text, "event": "unknown"}
    device_id = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("▼"):
            match = re.search(r"▼\s*([A-Fa-f0-9]+)", line)
            if match:
                device_id = match.group(1)
            continue

        if "=" not in line:
            continue

        key, value = [part.strip() for part in line.split("=", 1)]
        if not key:
            continue

        normalized_key = key
        if key.lower() == "doorsensorbatterycritical":
            normalized_key = "doorSensorBatteryCritical"
        parsed[normalized_key] = _coerce_value(value)

    if device_id:
        parsed["device_id"] = device_id

    if "deviceType" in parsed and isinstance(parsed["deviceType"], (int, float)):
        parsed["device_type"] = NukiDeviceTypes.get(int(parsed["deviceType"]), "unknown")

    parsed["event"] = _state_from_payload(parsed)
    return parsed
