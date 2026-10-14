"""Helpers for parsing Nuki MQTT event payloads."""

from __future__ import annotations

import re
import json


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

NukiFieldNames = {
    "connected": "connected",
    "timestamp": "timestamp",
    "devicetype": "deviceType",
    "name": "name",
    "firmware": "firmware",
    "batterychargestate": "batteryChargeState",
    "batterycritical": "batteryCritical",
    "batterycharging": "batteryCharging",
    "keypadbatterycritical": "keypadBatteryCritical",
    "doorsensorbatterycritical": "doorSensorBatteryCritical",
    "state": "state",
    "mode": "mode",
    "lockactionevent": "lockActionEvent",
}


def device_label(parsed: dict[str, object]) -> str:
    """Return the most useful display label for the device."""
    if "name" in parsed and isinstance(parsed["name"], str) and parsed["name"].strip():
        return str(parsed["name"]).strip()
    if "device_id" in parsed and str(parsed["device_id"]).strip():
        return str(parsed["device_id"]).strip()
    return "Nuki"


def device_key(parsed: dict[str, object], topic: str) -> str:
    """Return a stable key that separates devices sharing a subscription."""
    device_id = parsed.get("device_id")
    if device_id is not None and str(device_id).strip():
        return str(device_id).strip()

    topic_parts = [part for part in topic.strip("/").split("/") if part]
    if topic_parts:
        return topic_parts[-1]

    name = parsed.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "nuki"


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

    return "unknown"


def parse_nuki_event(raw: str | bytes | None, topic: str | None = None) -> dict[str, object]:
    """Parse a multiline Nuki payload or an individual topic/value message."""
    if raw is None:
        return {"event": "unknown", "raw": ""}

    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")

    text = raw.strip()
    if not text:
        return {"event": "unknown", "raw": ""}

    parsed: dict[str, object] = {"raw": text}
    device_id = None

    # Some Nuki MQTT bridges publish one field per topic, e.g.
    # nuki/4CFF3164/connected with payload "true". Recognize that shape.
    if topic:
        topic_parts = [part for part in topic.strip("/").split("/") if part]
        if topic_parts:
            topic_key = NukiFieldNames.get(topic_parts[-1].lower())
            if topic_key:
                parsed[topic_key] = _coerce_value(text)
                if len(topic_parts) > 1:
                    candidate_id = topic_parts[-2]
                    if candidate_id.lower() not in NukiFieldNames:
                        device_id = candidate_id
            elif len(topic_parts) > 1:
                # Some brokers publish one complete payload on nuki/<device-id>.
                device_id = topic_parts[-1]

    try:
        json_payload = json.loads(text)
    except json.JSONDecodeError:
        json_payload = None

    if isinstance(json_payload, dict):
        for key, value in json_payload.items():
            normalized_key = NukiFieldNames.get(str(key).lower(), str(key))
            parsed[normalized_key] = value

    elif not parsed.keys() - {"raw"}:
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

            normalized_key = NukiFieldNames.get(key.lower(), key)
            parsed[normalized_key] = _coerce_value(value)

    if device_id:
        parsed["device_id"] = device_id

    if "deviceType" in parsed and isinstance(parsed["deviceType"], (int, float)):
        parsed["device_type"] = NukiDeviceTypes.get(int(parsed["deviceType"]), "unknown")

    parsed["event"] = _state_from_payload(parsed)
    return parsed
