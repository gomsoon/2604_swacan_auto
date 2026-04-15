from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import current_app


def get_current_time() -> datetime:
    provider = current_app.config.get("CURRENT_TIME_PROVIDER")
    if callable(provider):
        value = provider()
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.astimezone()
    return datetime.now().astimezone()


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.astimezone()


def derive_latest_state(state_row) -> dict[str, Any]:
    payload = {
        "monitored_object_id": state_row["monitored_object_id"],
        "target_id": state_row["target_id"],
        "state_type": state_row["state_type"],
        "status": state_row["status"],
        "severity": state_row["severity"],
        "occurred_at": state_row["occurred_at"],
        "received_at": state_row["received_at"],
        "state": json.loads(state_row["state_json"]),
    }

    if payload["state_type"] != "agent":
        return payload

    state = dict(payload["state"])
    warning_seconds = int(current_app.config.get("AGENT_HEARTBEAT_WARNING_SECONDS", 15))
    down_seconds = int(current_app.config.get("AGENT_HEARTBEAT_DOWN_SECONDS", 30))
    heartbeat_at = parse_timestamp(state.get("heartbeat_time") or payload["occurred_at"])
    now = get_current_time()

    if heartbeat_at is None:
        payload["state"] = state
        return payload

    age_seconds = max((now - heartbeat_at).total_seconds(), 0.0)
    state["heartbeat_age_seconds"] = round(age_seconds, 3)
    state["heartbeat_warning_seconds"] = warning_seconds
    state["heartbeat_down_seconds"] = down_seconds

    if age_seconds >= down_seconds:
        payload["status"] = "down"
        payload["severity"] = "critical"
        state["heartbeat_timeout_level"] = "down"
        state["heartbeat_timeout_message"] = "heartbeat timeout"
    elif age_seconds >= warning_seconds:
        payload["status"] = "warning"
        payload["severity"] = "warning"
        state["heartbeat_timeout_level"] = "warning"
        state["heartbeat_timeout_message"] = "heartbeat delayed"
    else:
        state["heartbeat_timeout_level"] = "normal"

    payload["state"] = state
    return payload
