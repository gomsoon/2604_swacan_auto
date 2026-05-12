from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import current_app, has_app_context


def get_current_time() -> datetime:
    provider = current_app.config.get("CURRENT_TIME_PROVIDER")
    if callable(provider):
        value = provider()
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.astimezone()
    return datetime.now().astimezone()


def _heartbeat_thresholds(
    *,
    warning_seconds: int | None = None,
    down_seconds: int | None = None,
) -> tuple[int, int]:
    if warning_seconds is None:
        warning_seconds = (
            int(current_app.config.get("AGENT_HEARTBEAT_WARNING_SECONDS", 15))
            if has_app_context()
            else 15
        )
    if down_seconds is None:
        down_seconds = (
            int(current_app.config.get("AGENT_HEARTBEAT_DOWN_SECONDS", 30))
            if has_app_context()
            else 30
        )
    return int(warning_seconds), int(down_seconds)


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.astimezone()


def derive_agent_heartbeat_state(
    state: dict[str, Any],
    *,
    occurred_at: str | None = None,
    now: datetime | None = None,
    warning_seconds: int | None = None,
    down_seconds: int | None = None,
) -> dict[str, Any]:
    derived_state = dict(state)
    heartbeat_at = parse_timestamp(derived_state.get("heartbeat_time") or occurred_at)
    if heartbeat_at is None:
        return derived_state

    current_time = now or get_current_time()
    warning_seconds, down_seconds = _heartbeat_thresholds(
        warning_seconds=warning_seconds,
        down_seconds=down_seconds,
    )
    age_seconds = max((current_time - heartbeat_at).total_seconds(), 0.0)
    derived_state["heartbeat_age_seconds"] = round(age_seconds, 3)
    derived_state["heartbeat_warning_seconds"] = warning_seconds
    derived_state["heartbeat_down_seconds"] = down_seconds

    if age_seconds >= down_seconds:
        derived_state["heartbeat_timeout_level"] = "down"
        derived_state["heartbeat_timeout_message"] = "heartbeat timeout"
    elif age_seconds >= warning_seconds:
        derived_state["heartbeat_timeout_level"] = "warning"
        derived_state["heartbeat_timeout_message"] = "heartbeat delayed"
    else:
        derived_state["heartbeat_timeout_level"] = "normal"
        derived_state.pop("heartbeat_timeout_message", None)

    return derived_state


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

    now = get_current_time()
    state = derive_agent_heartbeat_state(payload["state"], occurred_at=payload["occurred_at"], now=now)
    timeout_level = state.get("heartbeat_timeout_level")

    if timeout_level == "down":
        payload["status"] = "down"
        payload["severity"] = "critical"
    elif timeout_level == "warning":
        payload["status"] = "warning"
        payload["severity"] = "warning"

    payload["state"] = state
    return payload
