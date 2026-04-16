from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import Blueprint, current_app, g, request

from .alert_history import record_alert_history
from .auth import admin_required, error_response
from .db import get_db
from .runtime_state import derive_latest_state

bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
ALLOWED_INGEST_STATUSES = {"pending", "processing", "processed", "failed"}
ALLOWED_DEBUG_DIRECTIONS = {"request", "response"}
ALLOWED_STATE_TYPES = {"agent", "host", "process"}
ALLOWED_STATE_STATUSES = {"up", "warning", "down"}
ALLOWED_ALERT_SCOPE_TYPES = {"object_type", "monitored_object"}
ALLOWED_ALERT_COMPARISONS = {"gte", "lte"}
ALERT_INSTANCE_STATUSES = {"open", "in_progress", "suppressed", "resolved"}
ALERT_ACTIVE_STATUSES = {"open", "in_progress", "suppressed"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def parse_limit() -> tuple[int | None, Any | None]:
    limit_raw = request.args.get("limit", default=str(DEFAULT_LIMIT))
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        return None, error_response("validation_error", "limit must be an integer", 400)

    if limit <= 0 or limit > MAX_LIMIT:
        return None, error_response("validation_error", f"limit must be between 1 and {MAX_LIMIT}", 400)

    return limit, None


def fetch_count(sql: str, params: tuple[Any, ...] = ()) -> int:
    row = get_db().execute(sql, params).fetchone()
    return int(row[0]) if row is not None else 0


def parse_json_or_text(raw_value: str | None) -> Any:
    if raw_value is None:
        return None

    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def get_payload_item_count(payload_json: str) -> int | None:
    payload = parse_json_or_text(payload_json)
    if not isinstance(payload, dict):
        return None

    items = payload.get("items")
    if isinstance(items, list):
        return len(items)

    return None


def serialize_ingest_row(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "boot_id": row["boot_id"],
        "seq_start": row["seq_start"],
        "seq_end": row["seq_end"],
        "status": row["status"],
        "received_at": row["received_at"],
        "processed_at": row["processed_at"],
        "error_message": row["error_message"],
        "item_count": get_payload_item_count(row["payload_json"]),
    }


def serialize_raw_event(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "monitored_object_id": row["monitored_object_id"],
        "target_id": row["target_id"],
        "event_type": row["event_type"],
        "severity": row["severity"],
        "message": row["message"],
        "occurred_at": row["occurred_at"],
        "received_at": row["received_at"],
    }
    if row["event_json"]:
        payload["event"] = parse_json_or_text(row["event_json"])
    return payload


def serialize_grouped_event(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "monitored_object_id": row["monitored_object_id"],
        "target_id": row["target_id"],
        "event_type": row["event_type"],
        "severity": row["severity"],
        "first_occurred_at": row["first_occurred_at"],
        "last_occurred_at": row["last_occurred_at"],
        "repeat_count": row["repeat_count"],
        "latest_message": row["latest_message"],
    }
    if row["latest_event_json"]:
        payload["event"] = parse_json_or_text(row["latest_event_json"])
    return payload


def load_grouped_event_raw_rows(grouped_event_row, limit: int):
    clauses = [
        "event_type = ?",
        "severity = ?",
        "occurred_at >= ?",
        "occurred_at <= ?",
    ]
    params: list[Any] = [
        grouped_event_row["event_type"],
        grouped_event_row["severity"],
        grouped_event_row["first_occurred_at"],
        grouped_event_row["last_occurred_at"],
    ]

    if grouped_event_row["monitored_object_id"] is not None:
        clauses.append("monitored_object_id = ?")
        params.append(grouped_event_row["monitored_object_id"])
    else:
        clauses.append("monitored_object_id IS NULL")
        clauses.append("target_id = ?")
        params.append(grouped_event_row["target_id"])

    params.append(limit)
    return get_db().execute(
        f"""
        SELECT id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
        FROM raw_events
        WHERE {' AND '.join(clauses)}
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
        """,
        tuple(params),
    ).fetchall()


def serialize_debug_payload(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "channel": row["channel"],
        "direction": row["direction"],
        "endpoint_or_topic": row["endpoint_or_topic"],
        "agent_id": row["agent_id"],
        "user_id": row["user_id"],
        "username": row["username"],
        "session_id": row["session_id"],
        "trace_id": row["trace_id"],
        "status_code": row["status_code"],
        "payload_size": row["payload_size"],
        "is_redacted": bool(row["is_redacted"]),
        "occurred_at": row["occurred_at"],
        "payload": parse_json_or_text(row["payload_json"]),
    }


def serialize_latest_state_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "monitored_object_id": payload["monitored_object_id"],
        "target_id": payload["target_id"],
        "state_type": payload["state_type"],
        "status": payload["status"],
        "severity": payload["severity"],
        "occurred_at": payload["occurred_at"],
        "received_at": payload["received_at"],
        "state": payload["state"],
    }


def serialize_cleanup_run(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "raw_events_deleted": row["raw_events_deleted"],
        "grouped_events_deleted": row["grouped_events_deleted"],
        "debug_payload_logs_deleted": row["debug_payload_logs_deleted"],
        "ingest_inbox_deleted": row["ingest_inbox_deleted"],
    }


def serialize_alert_instance(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "monitored_object_id": row["monitored_object_id"],
        "runtime_binding_key": row["runtime_binding_key"],
        "semantic_type_code": row["semantic_type_code"],
        "display_name": row["display_name"],
        "alert_code": row["alert_code"],
        "source_rule_id": row["source_rule_id"],
        "source_rule_metric_key": row["source_rule_metric_key"],
        "source_rule_scope_type": row["source_rule_scope_type"],
        "source_rule_target_label": row["source_rule_target_label"],
        "severity": row["severity"],
        "status": row["status"],
        "is_acknowledged": bool(row["acknowledged_at"]),
        "acknowledged_at": row["acknowledged_at"],
        "acknowledged_by_user_id": row["acknowledged_by_user_id"],
        "acknowledged_by_username": row["acknowledged_by_username"],
        "ack_note": row["ack_note"],
        "status_updated_at": row["status_updated_at"],
        "status_updated_by_user_id": row["status_updated_by_user_id"],
        "status_updated_by_username": row["status_updated_by_username"],
        "status_note": row["status_note"],
        "resolved_at": row["resolved_at"],
        "resolved_by_user_id": row["resolved_by_user_id"],
        "resolved_by_username": row["resolved_by_username"],
        "first_occurred_at": row["first_occurred_at"],
        "last_occurred_at": row["last_occurred_at"],
        "repeat_count": row["repeat_count"],
        "latest_message": row["latest_message"],
    }
    if row["metadata_json"]:
        payload["metadata"] = parse_json_or_text(row["metadata_json"])
    return payload


def serialize_alert_history_row(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "alert_instance_id": row["alert_instance_id"],
        "action_type": row["action_type"],
        "previous_status": row["previous_status"],
        "new_status": row["new_status"],
        "previous_acknowledged": None if row["previous_acknowledged"] is None else bool(row["previous_acknowledged"]),
        "new_acknowledged": None if row["new_acknowledged"] is None else bool(row["new_acknowledged"]),
        "performed_by_user_id": row["performed_by_user_id"],
        "performed_by_username": row["performed_by_username"],
        "note": row["note"],
        "created_at": row["created_at"],
    }
    if row["payload_json"]:
        payload["payload"] = parse_json_or_text(row["payload_json"])
    return payload


def fetch_alert_instance_row(alert_id: int):
    return get_db().execute(
        """
        SELECT alerts.id, alerts.monitored_object_id, mo.runtime_binding_key, mo.object_type AS semantic_type_code,
               mo.display_name, alerts.alert_code, alerts.severity, alerts.status,
               alerts.source_rule_id, rules.metric_key AS source_rule_metric_key, rules.scope_type AS source_rule_scope_type,
               COALESCE(rule_mo.display_name, rules.object_type) AS source_rule_target_label,
               alerts.acknowledged_at, alerts.acknowledged_by_user_id, ack_user.username AS acknowledged_by_username,
               alerts.ack_note,
               alerts.status_updated_at, alerts.status_updated_by_user_id, status_user.username AS status_updated_by_username,
               alerts.status_note,
               alerts.resolved_at, alerts.resolved_by_user_id, resolved_user.username AS resolved_by_username,
               alerts.first_occurred_at, alerts.last_occurred_at, alerts.repeat_count,
               alerts.latest_message, alerts.metadata_json
        FROM alert_instances AS alerts
        JOIN monitored_objects AS mo ON mo.id = alerts.monitored_object_id
        LEFT JOIN alert_rules AS rules ON rules.id = alerts.source_rule_id
        LEFT JOIN monitored_objects AS rule_mo ON rule_mo.id = rules.monitored_object_id
        LEFT JOIN users AS ack_user ON ack_user.id = alerts.acknowledged_by_user_id
        LEFT JOIN users AS status_user ON status_user.id = alerts.status_updated_by_user_id
        LEFT JOIN users AS resolved_user ON resolved_user.id = alerts.resolved_by_user_id
        WHERE alerts.id = ?
        """,
        (alert_id,),
    ).fetchone()


def serialize_alert_rule(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "scope_type": row["scope_type"],
        "object_type": row["object_type"],
        "monitored_object_id": row["monitored_object_id"],
        "target_display_name": row["target_display_name"],
        "target_runtime_binding_key": row["target_runtime_binding_key"],
        "state_type": row["state_type"],
        "metric_key": row["metric_key"],
        "comparison": row["comparison"],
        "warning_threshold": row["warning_threshold"],
        "critical_threshold": row["critical_threshold"],
        "is_enabled": bool(row["is_enabled"]),
        "description": row["description"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_monitored_object(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "object_type": row["object_type"],
        "display_name": row["display_name"],
        "runtime_binding_key": row["runtime_binding_key"],
        "active_view_count": row["active_view_count"],
        "active_node_count": row["active_node_count"],
        "open_alert_count": row["open_alert_count"],
    }


def preview_metric_value(state: dict[str, Any], metric_key: str) -> float | None:
    if metric_key == "memory_used_ratio":
        total = state.get("memory_total")
        used = state.get("memory_used")
        try:
            total_value = float(total)
            used_value = float(used)
        except (TypeError, ValueError):
            return None
        if total_value <= 0:
            return None
        return (used_value / total_value) * 100.0

    value = state.get(metric_key)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def preview_threshold_level(
    metric_value: float | None,
    comparison: str,
    warning_threshold: float | None,
    critical_threshold: float | None,
) -> str:
    if metric_value is None:
        return "unknown"

    def matches(value: float, threshold: float | None) -> bool:
        if threshold is None:
            return False
        return value >= threshold if comparison == "gte" else value <= threshold

    if matches(metric_value, critical_threshold):
        return "critical"
    if matches(metric_value, warning_threshold):
        return "warning"
    return "normal"


def parse_optional_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("threshold must be a number") from None


def parse_optional_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value in {0, 1}:
        return bool(value)
    raise ValueError("is_enabled must be a boolean")


def parse_optional_string(value: Any, *, field_name: str, max_length: int | None = None) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        return None
    if max_length is not None and len(normalized) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return normalized


def parse_boolean_query_param(value: str | None, *, field_name: str) -> tuple[bool | None, Any | None]:
    if value in (None, ""):
        return None, None
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True, None
    if normalized in {"false", "0"}:
        return False, None
    return None, error_response("validation_error", f"{field_name} must be true/false", 400)


def parse_alert_status_filter(value: str | None) -> tuple[str, Any | None]:
    normalized = (value or "active").strip().lower()
    if normalized == "active" or normalized in ALERT_INSTANCE_STATUSES:
        return normalized, None
    return normalized, error_response("validation_error", "invalid status filter", 400)


def validate_alert_rule_payload(data: dict[str, Any], *, partial: bool = False) -> tuple[dict[str, Any] | None, Any | None]:
    payload = dict(data)

    if not partial or "scope_type" in payload:
        scope_type = payload.get("scope_type")
        if scope_type not in ALLOWED_ALERT_SCOPE_TYPES:
            return None, error_response("validation_error", "scope_type is invalid", 400)

    if not partial or "state_type" in payload:
        state_type = payload.get("state_type")
        if state_type not in ALLOWED_STATE_TYPES:
            return None, error_response("validation_error", "state_type is invalid", 400)

    if not partial or "comparison" in payload:
        comparison = payload.get("comparison")
        if comparison not in ALLOWED_ALERT_COMPARISONS:
            return None, error_response("validation_error", "comparison is invalid", 400)

    if not partial or "metric_key" in payload:
        metric_key = payload.get("metric_key")
        if not isinstance(metric_key, str) or not metric_key.strip():
            return None, error_response("validation_error", "metric_key is required", 400)
        payload["metric_key"] = metric_key.strip()

    try:
        if "warning_threshold" in payload:
            payload["warning_threshold"] = parse_optional_float(payload.get("warning_threshold"))
        if "critical_threshold" in payload:
            payload["critical_threshold"] = parse_optional_float(payload.get("critical_threshold"))
    except ValueError as exc:
        return None, error_response("validation_error", str(exc), 400)

    try:
        if not partial or "is_enabled" in payload:
            payload["is_enabled"] = parse_optional_bool(payload.get("is_enabled"))
    except ValueError as exc:
        return None, error_response("validation_error", str(exc), 400)

    scope_type = payload.get("scope_type")
    if scope_type == "object_type":
        object_type = payload.get("object_type")
        if not isinstance(object_type, str) or not object_type.strip():
            return None, error_response("validation_error", "object_type is required for object_type scope", 400)
        payload["object_type"] = object_type.strip()
        payload["monitored_object_id"] = None
    elif scope_type == "monitored_object":
        monitored_object_id = payload.get("monitored_object_id")
        if not isinstance(monitored_object_id, int):
            return None, error_response("validation_error", "monitored_object_id is required for monitored_object scope", 400)
        row = get_db().execute("SELECT id FROM monitored_objects WHERE id = ?", (monitored_object_id,)).fetchone()
        if row is None:
            return None, error_response("validation_error", "monitored_object_id not found", 400)
        payload["object_type"] = None

    warning_threshold = payload.get("warning_threshold")
    critical_threshold = payload.get("critical_threshold")
    if warning_threshold is None and critical_threshold is None:
        return None, error_response("validation_error", "at least one threshold is required", 400)

    description = payload.get("description")
    if description is not None:
        if not isinstance(description, str):
            return None, error_response("validation_error", "description must be a string", 400)
        payload["description"] = description.strip() or None

    comparison = payload.get("comparison")
    if warning_threshold is not None and critical_threshold is not None:
        if comparison == "gte" and critical_threshold < warning_threshold:
            return None, error_response("validation_error", "critical_threshold must be greater than or equal to warning_threshold", 400)
        if comparison == "lte" and critical_threshold > warning_threshold:
            return None, error_response("validation_error", "critical_threshold must be less than or equal to warning_threshold", 400)

    return payload, None


def load_derived_latest_states(state_type: str | None = None) -> list[dict[str, Any]]:
    sql = """
        SELECT monitored_object_id, target_id, state_type, status, severity, state_json, occurred_at, received_at
        FROM latest_states
    """
    params: list[Any] = []
    if state_type:
        sql += " WHERE state_type = ?"
        params.append(state_type)
    sql += " ORDER BY received_at DESC, id DESC"

    rows = get_db().execute(sql, tuple(params)).fetchall()
    return [derive_latest_state(row) for row in rows]


@bp.get("/summary")
@admin_required
def get_summary():
    db_conn = get_db()
    counts = {
        "users": fetch_count("SELECT COUNT(*) FROM users"),
        "views": fetch_count("SELECT COUNT(*) FROM views"),
        "view_nodes": fetch_count("SELECT COUNT(*) FROM view_nodes WHERE is_deleted = 0"),
        "view_edges": fetch_count("SELECT COUNT(*) FROM view_edges WHERE is_deleted = 0"),
        "latest_states": fetch_count("SELECT COUNT(*) FROM latest_states"),
        "raw_events": fetch_count("SELECT COUNT(*) FROM raw_events"),
        "grouped_events": fetch_count("SELECT COUNT(*) FROM grouped_events"),
        "open_alerts": fetch_count("SELECT COUNT(*) FROM alert_instances WHERE status != 'resolved'"),
        "alert_rules": fetch_count("SELECT COUNT(*) FROM alert_rules"),
        "debug_payload_logs": fetch_count("SELECT COUNT(*) FROM debug_payload_logs"),
        "cleanup_runs": fetch_count("SELECT COUNT(*) FROM cleanup_runs"),
    }

    ingest_status_counts = {status: 0 for status in sorted(ALLOWED_INGEST_STATUSES)}
    for row in db_conn.execute(
        "SELECT status, COUNT(*) AS count FROM ingest_inbox GROUP BY status ORDER BY status"
    ).fetchall():
        ingest_status_counts[row["status"]] = row["count"]

    failed_rows = db_conn.execute(
        """
        SELECT id, agent_id, boot_id, seq_start, seq_end, payload_json, status, received_at, processed_at, error_message
        FROM ingest_inbox
        WHERE status = 'failed'
        ORDER BY received_at DESC, id DESC
        LIMIT 5
        """
    ).fetchall()

    derived_latest_states = load_derived_latest_states()
    state_type_counts = {state_type: 0 for state_type in sorted(ALLOWED_STATE_TYPES)}
    runtime_status_counts = {status: 0 for status in sorted(ALLOWED_STATE_STATUSES)}
    runtime_status_counts["other"] = 0
    stale_agents: list[dict[str, Any]] = []

    for payload in derived_latest_states:
        state_type_counts[payload["state_type"]] = state_type_counts.get(payload["state_type"], 0) + 1
        if payload["status"] in runtime_status_counts:
            runtime_status_counts[payload["status"]] += 1
        else:
            runtime_status_counts["other"] += 1

        if payload["state_type"] == "agent" and payload["status"] in {"warning", "down"}:
            stale_agents.append(serialize_latest_state_payload(payload))

    last_cleanup_row = db_conn.execute(
        """
        SELECT id, started_at, finished_at, raw_events_deleted, grouped_events_deleted, debug_payload_logs_deleted, ingest_inbox_deleted
        FROM cleanup_runs
        ORDER BY finished_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()

    return {
        "service_status": "ok",
        "generated_at": now_iso(),
        "debug_payload_logging_enabled": bool(current_app.config.get("DEBUG_PAYLOAD_LOGGING", False)),
        "counts": counts,
        "ingest_inbox": {
            "status_counts": ingest_status_counts,
            "recent_failed": [serialize_ingest_row(row) for row in failed_rows],
        },
        "runtime": {
            "state_type_counts": state_type_counts,
            "status_counts": runtime_status_counts,
            "stale_agent_count": len(stale_agents),
        },
        "stale_agents": stale_agents[:5],
        "retention_policy": {
            "raw_events_days": int(current_app.config.get("RAW_EVENT_RETENTION_DAYS", 7)),
            "grouped_events_days": int(current_app.config.get("GROUPED_EVENT_RETENTION_DAYS", 7)),
            "debug_payload_hours": int(current_app.config.get("DEBUG_PAYLOAD_RETENTION_HOURS", 24)),
            "ingest_inbox_days": int(current_app.config.get("INGEST_INBOX_RETENTION_DAYS", 7)),
        },
        "last_cleanup": serialize_cleanup_run(last_cleanup_row) if last_cleanup_row else None,
    }


@bp.get("/ingest-inbox")
@admin_required
def list_ingest_inbox():
    limit, error = parse_limit()
    if error:
        return error

    status_filter = request.args.get("status")
    clauses: list[str] = []
    params: list[Any] = []

    if status_filter:
        if status_filter not in ALLOWED_INGEST_STATUSES:
            return error_response("validation_error", "invalid status filter", 400)
        clauses.append("status = ?")
        params.append(status_filter)

    sql = """
        SELECT id, agent_id, boot_id, seq_start, seq_end, payload_json, status, received_at, processed_at, error_message
        FROM ingest_inbox
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY received_at DESC, id DESC LIMIT ?"
    params.append(limit)

    rows = get_db().execute(sql, tuple(params)).fetchall()
    return {"items": [serialize_ingest_row(row) for row in rows]}


@bp.get("/raw-events")
@admin_required
def list_raw_events():
    limit, error = parse_limit()
    if error:
        return error

    rows = get_db().execute(
        """
        SELECT id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
        FROM raw_events
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return {"items": [serialize_raw_event(row) for row in rows]}


@bp.get("/grouped-events")
@admin_required
def list_grouped_events():
    limit, error = parse_limit()
    if error:
        return error

    rows = get_db().execute(
        """
        SELECT id, monitored_object_id, target_id, event_type, severity,
               first_occurred_at, last_occurred_at, repeat_count, latest_message, latest_event_json
        FROM grouped_events
        ORDER BY last_occurred_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return {"items": [serialize_grouped_event(row) for row in rows]}


@bp.get("/grouped-events/<int:grouped_event_id>/raw-events")
@admin_required
def list_grouped_event_raw_events(grouped_event_id: int):
    limit, error = parse_limit()
    if error:
        return error

    grouped_event_row = get_db().execute(
        """
        SELECT id, monitored_object_id, target_id, event_type, severity,
               first_occurred_at, last_occurred_at, repeat_count, latest_message, latest_event_json
        FROM grouped_events
        WHERE id = ?
        """,
        (grouped_event_id,),
    ).fetchone()
    if grouped_event_row is None:
        return error_response("not_found", "grouped event not found", 404)

    raw_rows = load_grouped_event_raw_rows(grouped_event_row, limit)
    return {
        "grouped_event": serialize_grouped_event(grouped_event_row),
        "items": [serialize_raw_event(row) for row in raw_rows],
    }


@bp.get("/latest-states")
@admin_required
def list_latest_states():
    limit, error = parse_limit()
    if error:
        return error

    state_type = request.args.get("state_type")
    if state_type and state_type not in ALLOWED_STATE_TYPES:
        return error_response("validation_error", "invalid state_type filter", 400)

    status = request.args.get("status")
    if status and status not in ALLOWED_STATE_STATUSES:
        return error_response("validation_error", "invalid status filter", 400)

    target_id = request.args.get("target_id")

    items = load_derived_latest_states(state_type=state_type)
    if target_id:
        items = [item for item in items if item["target_id"] == target_id]
    if status:
        items = [item for item in items if item["status"] == status]

    return {"items": [serialize_latest_state_payload(item) for item in items[:limit]]}


@bp.get("/debug-payloads")
@admin_required
def list_debug_payloads():
    limit, error = parse_limit()
    if error:
        return error

    channel = request.args.get("channel")
    direction = request.args.get("direction")
    agent_id = request.args.get("agent_id")
    user_id_raw = request.args.get("user_id")
    trace_id = request.args.get("trace_id")
    endpoint_or_topic = request.args.get("endpoint_or_topic")

    clauses: list[str] = []
    params: list[Any] = []

    if channel:
        clauses.append("logs.channel = ?")
        params.append(channel)

    if direction:
        if direction not in ALLOWED_DEBUG_DIRECTIONS:
            return error_response("validation_error", "invalid direction filter", 400)
        clauses.append("logs.direction = ?")
        params.append(direction)

    if agent_id:
        clauses.append("logs.agent_id = ?")
        params.append(agent_id)

    if user_id_raw:
        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            return error_response("validation_error", "user_id must be an integer", 400)
        clauses.append("logs.user_id = ?")
        params.append(user_id)

    if trace_id:
        clauses.append("logs.trace_id = ?")
        params.append(trace_id)

    if endpoint_or_topic:
        clauses.append("logs.endpoint_or_topic = ?")
        params.append(endpoint_or_topic)

    sql = """
        SELECT logs.id, logs.channel, logs.direction, logs.endpoint_or_topic, logs.agent_id,
               logs.user_id, users.username, logs.session_id, logs.trace_id, logs.status_code,
               logs.payload_json, logs.payload_size, logs.is_redacted, logs.occurred_at
        FROM debug_payload_logs AS logs
        LEFT JOIN users ON users.id = logs.user_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY logs.occurred_at DESC, logs.id DESC LIMIT ?"
    params.append(limit)

    rows = get_db().execute(sql, tuple(params)).fetchall()
    return {
        "debug_payload_logging_enabled": bool(current_app.config.get("DEBUG_PAYLOAD_LOGGING", False)),
        "items": [serialize_debug_payload(row) for row in rows],
    }


@bp.get("/cleanup-runs")
@admin_required
def list_cleanup_runs():
    limit, error = parse_limit()
    if error:
        return error

    rows = get_db().execute(
        """
        SELECT id, started_at, finished_at, raw_events_deleted, grouped_events_deleted, debug_payload_logs_deleted, ingest_inbox_deleted
        FROM cleanup_runs
        ORDER BY finished_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return {"items": [serialize_cleanup_run(row) for row in rows]}


@bp.get("/alerts")
@admin_required
def list_alert_instances():
    limit, error = parse_limit()
    if error:
        return error

    status, status_error = parse_alert_status_filter(request.args.get("status", "active"))
    if status_error:
        return status_error

    severity = request.args.get("severity")
    if severity and severity not in {"critical", "warning", "normal", "info"}:
        return error_response("validation_error", "invalid severity filter", 400)

    is_acknowledged, ack_error = parse_boolean_query_param(
        request.args.get("is_acknowledged"),
        field_name="is_acknowledged",
    )
    if ack_error:
        return ack_error

    clauses: list[str] = []
    params: list[Any] = []
    if status == "active":
        clauses.append("alerts.status != 'resolved'")
    else:
        clauses.append("alerts.status = ?")
        params.append(status)
    if severity:
        clauses.append("alerts.severity = ?")
        params.append(severity)
    if is_acknowledged is True:
        clauses.append("alerts.acknowledged_at IS NOT NULL")
    elif is_acknowledged is False:
        clauses.append("alerts.acknowledged_at IS NULL")

    sql = """
        SELECT alerts.id, alerts.monitored_object_id, mo.runtime_binding_key, mo.object_type AS semantic_type_code,
               mo.display_name, alerts.alert_code, alerts.severity, alerts.status,
               alerts.source_rule_id, rules.metric_key AS source_rule_metric_key, rules.scope_type AS source_rule_scope_type,
               COALESCE(rule_mo.display_name, rules.object_type) AS source_rule_target_label,
               alerts.acknowledged_at, alerts.acknowledged_by_user_id, ack_user.username AS acknowledged_by_username,
               alerts.ack_note,
               alerts.status_updated_at, alerts.status_updated_by_user_id, status_user.username AS status_updated_by_username,
               alerts.status_note,
               alerts.resolved_at, alerts.resolved_by_user_id, resolved_user.username AS resolved_by_username,
               alerts.first_occurred_at, alerts.last_occurred_at, alerts.repeat_count,
               alerts.latest_message, alerts.metadata_json
        FROM alert_instances AS alerts
        JOIN monitored_objects AS mo ON mo.id = alerts.monitored_object_id
        LEFT JOIN alert_rules AS rules ON rules.id = alerts.source_rule_id
        LEFT JOIN monitored_objects AS rule_mo ON rule_mo.id = rules.monitored_object_id
        LEFT JOIN users AS ack_user ON ack_user.id = alerts.acknowledged_by_user_id
        LEFT JOIN users AS status_user ON status_user.id = alerts.status_updated_by_user_id
        LEFT JOIN users AS resolved_user ON resolved_user.id = alerts.resolved_by_user_id
        WHERE {where_clause}
        ORDER BY
            CASE alerts.severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
            alerts.last_occurred_at DESC,
            alerts.id DESC
        LIMIT ?
    """.format(where_clause=" AND ".join(clauses))
    params.append(limit)

    rows = get_db().execute(sql, tuple(params)).fetchall()
    return {"items": [serialize_alert_instance(row) for row in rows]}


@bp.get("/alerts/<int:alert_id>/history")
@admin_required
def get_alert_history(alert_id: int):
    limit, error = parse_limit()
    if error:
        return error

    alert_row = get_db().execute(
        "SELECT id FROM alert_instances WHERE id = ?",
        (alert_id,),
    ).fetchone()
    if alert_row is None:
        return error_response("not_found", "alert not found", 404)

    rows = get_db().execute(
        """
        SELECT history.id, history.alert_instance_id, history.action_type,
               history.previous_status, history.new_status,
               history.previous_acknowledged, history.new_acknowledged,
               history.performed_by_user_id, users.username AS performed_by_username,
               history.note, history.payload_json, history.created_at
        FROM alert_history AS history
        LEFT JOIN users ON users.id = history.performed_by_user_id
        WHERE history.alert_instance_id = ?
        ORDER BY history.created_at DESC, history.id DESC
        LIMIT ?
        """,
        (alert_id, limit),
    ).fetchall()
    return {"items": [serialize_alert_history_row(row) for row in rows]}


@bp.patch("/alerts/<int:alert_id>")
@admin_required
def update_alert_instance(alert_id: int):
    db_conn = get_db()
    existing = db_conn.execute(
        """
        SELECT id, status, acknowledged_at, acknowledged_by_user_id, ack_note
        FROM alert_instances
        WHERE id = ?
        """,
        (alert_id,),
    ).fetchone()
    if existing is None:
        return error_response("not_found", "alert not found", 404)

    data = request.get_json(silent=True) or {}
    if "acknowledged" not in data:
        return error_response("validation_error", "acknowledged is required", 400)

    try:
        acknowledged = parse_optional_bool(data.get("acknowledged"))
        ack_note = parse_optional_string(data.get("ack_note"), field_name="ack_note", max_length=500)
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    if existing["status"] == "resolved":
        return error_response("invalid_state", "resolved alert cannot be acknowledged", 409)

    timestamp = now_iso()
    previous_acknowledged = existing["acknowledged_at"] is not None
    if acknowledged:
        db_conn.execute(
            """
            UPDATE alert_instances
            SET acknowledged_at = ?, acknowledged_by_user_id = ?, ack_note = ?, updated_at = ?
            WHERE id = ?
            """,
            (timestamp, g.user["id"], ack_note, timestamp, alert_id),
        )
    else:
        db_conn.execute(
            """
            UPDATE alert_instances
            SET acknowledged_at = NULL, acknowledged_by_user_id = NULL, ack_note = NULL, updated_at = ?
            WHERE id = ?
            """,
            (timestamp, alert_id),
        )

    record_alert_history(
        db_conn,
        alert_instance_id=alert_id,
        action_type="acknowledged" if acknowledged else "unacknowledged",
        created_at=timestamp,
        performed_by_user_id=g.user["id"],
        previous_status=existing["status"],
        new_status=existing["status"],
        previous_acknowledged=previous_acknowledged,
        new_acknowledged=acknowledged,
        note=ack_note if acknowledged else None,
        payload={
            "source": "admin",
            "previous_acknowledged_at": existing["acknowledged_at"],
            "previous_ack_note": existing["ack_note"],
        },
    )
    db_conn.commit()

    row = fetch_alert_instance_row(alert_id)
    return {"alert": serialize_alert_instance(row)}


@bp.patch("/alerts/<int:alert_id>/status")
@admin_required
def update_alert_status(alert_id: int):
    db_conn = get_db()
    existing = db_conn.execute(
        """
        SELECT id, status
        FROM alert_instances
        WHERE id = ?
        """,
        (alert_id,),
    ).fetchone()
    if existing is None:
        return error_response("not_found", "alert not found", 404)

    data = request.get_json(silent=True) or {}
    next_status = data.get("status")
    if next_status not in ALERT_INSTANCE_STATUSES:
        return error_response("validation_error", "status is invalid", 400)

    try:
        status_note = parse_optional_string(data.get("status_note"), field_name="status_note", max_length=500)
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    timestamp = now_iso()
    previous_status = existing["status"]
    resolved_at = timestamp if next_status == "resolved" else None
    resolved_by_user_id = g.user["id"] if next_status == "resolved" else None

    db_conn.execute(
        """
        UPDATE alert_instances
        SET status = ?,
            status_updated_at = ?,
            status_updated_by_user_id = ?,
            status_note = ?,
            resolved_at = ?,
            resolved_by_user_id = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            next_status,
            timestamp,
            g.user["id"],
            status_note,
            resolved_at,
            resolved_by_user_id,
            timestamp,
            alert_id,
        ),
    )
    record_alert_history(
        db_conn,
        alert_instance_id=alert_id,
        action_type="resolved" if next_status == "resolved" else "status_changed",
        created_at=timestamp,
        performed_by_user_id=g.user["id"],
        previous_status=previous_status,
        new_status=next_status,
        note=status_note,
        payload={"source": "admin"},
    )
    db_conn.commit()

    row = fetch_alert_instance_row(alert_id)
    return {"alert": serialize_alert_instance(row)}


@bp.get("/alert-rules")
@admin_required
def list_alert_rules():
    scope_type = request.args.get("scope_type")
    if scope_type and scope_type not in ALLOWED_ALERT_SCOPE_TYPES:
        return error_response("validation_error", "scope_type is invalid", 400)

    state_type = request.args.get("state_type")
    if state_type and state_type not in ALLOWED_STATE_TYPES:
        return error_response("validation_error", "state_type is invalid", 400)

    object_type = request.args.get("object_type")

    is_enabled, enabled_error = parse_boolean_query_param(request.args.get("is_enabled"), field_name="is_enabled")
    if enabled_error:
        return enabled_error

    clauses: list[str] = []
    params: list[Any] = []
    if scope_type:
        clauses.append("rules.scope_type = ?")
        params.append(scope_type)
    if state_type:
        clauses.append("rules.state_type = ?")
        params.append(state_type)
    if object_type:
        clauses.append("COALESCE(rules.object_type, mo.object_type) = ?")
        params.append(object_type)
    if is_enabled is not None:
        clauses.append("rules.is_enabled = ?")
        params.append(int(is_enabled))

    sql = """
        SELECT rules.id, rules.scope_type, rules.object_type, rules.monitored_object_id, rules.state_type, rules.metric_key, rules.comparison,
               rules.warning_threshold, rules.critical_threshold, rules.is_enabled, rules.description, rules.created_at, rules.updated_at,
               mo.display_name AS target_display_name, mo.runtime_binding_key AS target_runtime_binding_key
        FROM alert_rules AS rules
        LEFT JOIN monitored_objects AS mo ON mo.id = rules.monitored_object_id
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY rules.is_enabled DESC, rules.state_type ASC, rules.id ASC"

    rows = get_db().execute(sql, tuple(params)).fetchall()
    return {"items": [serialize_alert_rule(row) for row in rows]}


@bp.get("/monitored-objects")
@admin_required
def list_monitored_objects():
    limit, error = parse_limit()
    if error:
        return error

    object_type = request.args.get("object_type")
    query = request.args.get("query")

    clauses: list[str] = []
    params: list[Any] = []
    if object_type:
        clauses.append("mo.object_type = ?")
        params.append(object_type)
    if query:
        clauses.append("(mo.display_name LIKE ? OR COALESCE(mo.runtime_binding_key, '') LIKE ?)")
        pattern = f"%{query.strip()}%"
        params.extend([pattern, pattern])

    sql = """
        SELECT
            mo.id,
            mo.object_type,
            mo.display_name,
            mo.runtime_binding_key,
            (
                SELECT COUNT(DISTINCT vv.view_id)
                FROM node_bindings AS nb
                JOIN view_version_nodes AS vn ON vn.id = nb.view_version_node_id
                JOIN view_versions AS vv ON vv.id = vn.view_version_id
                WHERE nb.monitored_object_id = mo.id
                  AND vv.status = 'active'
            ) AS active_view_count,
            (
                SELECT COUNT(*)
                FROM node_bindings AS nb
                JOIN view_version_nodes AS vn ON vn.id = nb.view_version_node_id
                JOIN view_versions AS vv ON vv.id = vn.view_version_id
                WHERE nb.monitored_object_id = mo.id
                  AND vv.status = 'active'
            ) AS active_node_count,
              (
                  SELECT COUNT(*)
                  FROM alert_instances AS alerts
                  WHERE alerts.monitored_object_id = mo.id
                    AND alerts.status != 'resolved'
              ) AS open_alert_count
        FROM monitored_objects AS mo
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY mo.display_name ASC, mo.id ASC LIMIT ?"
    params.append(limit)

    rows = get_db().execute(sql, tuple(params)).fetchall()
    return {"items": [serialize_monitored_object(row) for row in rows]}


@bp.get("/alert-rules/<int:rule_id>/targets-preview")
@admin_required
def get_alert_rule_targets_preview(rule_id: int):
    limit, error = parse_limit()
    if error:
        return error

    row = get_db().execute(
        """
        SELECT rules.id, rules.scope_type, rules.object_type, rules.monitored_object_id, rules.state_type, rules.metric_key, rules.comparison,
               rules.warning_threshold, rules.critical_threshold, rules.is_enabled, rules.description, rules.created_at, rules.updated_at,
               mo.display_name AS target_display_name, mo.runtime_binding_key AS target_runtime_binding_key
        FROM alert_rules AS rules
        LEFT JOIN monitored_objects AS mo ON mo.id = rules.monitored_object_id
        WHERE rules.id = ?
        """,
        (rule_id,),
    ).fetchone()
    if row is None:
        return error_response("not_found", "alert rule not found", 404)

    clauses: list[str] = []
    params: list[Any] = []
    if row["scope_type"] == "monitored_object":
        clauses.append("mo.id = ?")
        params.append(row["monitored_object_id"])
    else:
        clauses.append("mo.object_type = ?")
        params.append(row["object_type"])

    preview_rows = get_db().execute(
        f"""
        SELECT
            mo.id AS monitored_object_id,
            mo.display_name,
            mo.runtime_binding_key,
            mo.object_type,
            (
                SELECT COUNT(DISTINCT vv.view_id)
                FROM node_bindings AS nb
                JOIN view_version_nodes AS vn ON vn.id = nb.view_version_node_id
                JOIN view_versions AS vv ON vv.id = vn.view_version_id
                WHERE nb.monitored_object_id = mo.id
                  AND vv.status = 'active'
            ) AS active_view_count,
            (
                SELECT COUNT(*)
                FROM node_bindings AS nb
                JOIN view_version_nodes AS vn ON vn.id = nb.view_version_node_id
                JOIN view_versions AS vv ON vv.id = vn.view_version_id
                WHERE nb.monitored_object_id = mo.id
                  AND vv.status = 'active'
            ) AS active_node_count,
            (
                SELECT COUNT(*)
                FROM alert_instances AS alerts
                WHERE alerts.monitored_object_id = mo.id
                  AND alerts.status != 'resolved'
            ) AS open_alert_count,
            (
                SELECT COUNT(*)
                FROM alert_instances AS alerts
                WHERE alerts.monitored_object_id = mo.id
                  AND alerts.status != 'resolved'
                  AND alerts.source_rule_id = ?
            ) AS source_rule_open_alert_count,
            ls.status AS latest_state_status,
            ls.severity AS latest_state_severity,
            ls.received_at AS latest_received_at,
            ls.state_json AS latest_state_json
        FROM monitored_objects AS mo
        LEFT JOIN latest_states AS ls ON ls.id = (
            SELECT ls2.id
            FROM latest_states AS ls2
            WHERE ls2.monitored_object_id = mo.id
              AND ls2.state_type = ?
            ORDER BY ls2.received_at DESC, ls2.id DESC
            LIMIT 1
        )
        WHERE {' AND '.join(clauses)}
        ORDER BY mo.display_name ASC, mo.id ASC
        """,
        (row["id"], row["state_type"], *params),
    ).fetchall()

    all_items: list[dict[str, Any]] = []
    monitored_object_ids: list[int] = []
    warning_match_count = 0
    critical_match_count = 0
    metric_available_count = 0

    for preview_row in preview_rows:
        state = parse_json_or_text(preview_row["latest_state_json"])
        if not isinstance(state, dict):
            state = {}
        current_metric_value = preview_metric_value(state, row["metric_key"])
        threshold_level = preview_threshold_level(
            current_metric_value,
            row["comparison"],
            row["warning_threshold"],
            row["critical_threshold"],
        )
        if current_metric_value is not None:
            metric_available_count += 1
        if threshold_level == "critical":
            critical_match_count += 1
            warning_match_count += 1
        elif threshold_level == "warning":
            warning_match_count += 1

        monitored_object_ids.append(preview_row["monitored_object_id"])
        all_items.append(
            {
                "monitored_object_id": preview_row["monitored_object_id"],
                "display_name": preview_row["display_name"],
                "runtime_binding_key": preview_row["runtime_binding_key"],
                "object_type": preview_row["object_type"],
                "active_view_count": preview_row["active_view_count"],
                "active_node_count": preview_row["active_node_count"],
                "open_alert_count": preview_row["open_alert_count"],
                "source_rule_open_alert_count": preview_row["source_rule_open_alert_count"],
                "latest_state_status": preview_row["latest_state_status"],
                "latest_state_severity": preview_row["latest_state_severity"],
                "latest_received_at": preview_row["latest_received_at"],
                "current_metric_value": current_metric_value,
                "threshold_level": threshold_level,
            }
        )

    distinct_active_view_count = 0
    total_active_node_count = sum(int(item["active_node_count"]) for item in all_items)
    total_open_alert_count = sum(int(item["open_alert_count"]) for item in all_items)
    total_source_rule_open_alert_count = sum(int(item["source_rule_open_alert_count"]) for item in all_items)

    if monitored_object_ids:
        placeholders = ", ".join("?" for _ in monitored_object_ids)
        distinct_active_view_count = int(
            get_db()
            .execute(
                f"""
                SELECT COUNT(DISTINCT vv.view_id)
                FROM node_bindings AS nb
                JOIN view_version_nodes AS vn ON vn.id = nb.view_version_node_id
                JOIN view_versions AS vv ON vv.id = vn.view_version_id
                WHERE nb.monitored_object_id IN ({placeholders})
                  AND vv.status = 'active'
                """,
                tuple(monitored_object_ids),
            )
            .fetchone()[0]
        )

    return {
        "rule": serialize_alert_rule(row),
        "summary": {
            "matched_object_count": len(all_items),
            "active_view_count": distinct_active_view_count,
            "active_node_count": total_active_node_count,
            "open_alert_count": total_open_alert_count,
            "source_rule_open_alert_count": total_source_rule_open_alert_count,
            "metric_available_count": metric_available_count,
            "warning_match_count": warning_match_count,
            "critical_match_count": critical_match_count,
        },
        "items": all_items[:limit],
    }


@bp.post("/alert-rules")
@admin_required
def create_alert_rule():
    data = request.get_json(silent=True) or {}
    payload, error = validate_alert_rule_payload(data, partial=False)
    if error:
        return error

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO alert_rules (
            scope_type, object_type, monitored_object_id, state_type, metric_key, comparison,
            warning_threshold, critical_threshold, is_enabled, description, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["scope_type"],
            payload.get("object_type"),
            payload.get("monitored_object_id"),
            payload["state_type"],
            payload["metric_key"],
            payload["comparison"],
            payload.get("warning_threshold"),
            payload.get("critical_threshold"),
            int(payload["is_enabled"]),
            payload.get("description"),
            timestamp,
            timestamp,
        ),
    )
    db_conn.commit()
    row = db_conn.execute(
        """
        SELECT rules.id, rules.scope_type, rules.object_type, rules.monitored_object_id, rules.state_type, rules.metric_key, rules.comparison,
               rules.warning_threshold, rules.critical_threshold, rules.is_enabled, rules.description, rules.created_at, rules.updated_at,
               mo.display_name AS target_display_name, mo.runtime_binding_key AS target_runtime_binding_key
        FROM alert_rules AS rules
        LEFT JOIN monitored_objects AS mo ON mo.id = rules.monitored_object_id
        WHERE rules.id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return {"rule": serialize_alert_rule(row)}, 201


@bp.patch("/alert-rules/<int:rule_id>")
@admin_required
def update_alert_rule(rule_id: int):
    db_conn = get_db()
    existing = db_conn.execute(
        """
        SELECT rules.id, rules.scope_type, rules.object_type, rules.monitored_object_id, rules.state_type, rules.metric_key, rules.comparison,
               rules.warning_threshold, rules.critical_threshold, rules.is_enabled, rules.description, rules.created_at, rules.updated_at,
               mo.display_name AS target_display_name, mo.runtime_binding_key AS target_runtime_binding_key
        FROM alert_rules AS rules
        LEFT JOIN monitored_objects AS mo ON mo.id = rules.monitored_object_id
        WHERE rules.id = ?
        """,
        (rule_id,),
    ).fetchone()
    if existing is None:
        return error_response("not_found", "alert rule not found", 404)

    data = request.get_json(silent=True) or {}
    merged = dict(existing)
    merged.update(data)
    payload, error = validate_alert_rule_payload(merged, partial=False)
    if error:
        return error

    timestamp = now_iso()
    db_conn.execute(
        """
        UPDATE alert_rules
        SET scope_type = ?, object_type = ?, monitored_object_id = ?, state_type = ?, metric_key = ?,
            comparison = ?, warning_threshold = ?, critical_threshold = ?, is_enabled = ?,
            description = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            payload["scope_type"],
            payload.get("object_type"),
            payload.get("monitored_object_id"),
            payload["state_type"],
            payload["metric_key"],
            payload["comparison"],
            payload.get("warning_threshold"),
            payload.get("critical_threshold"),
            int(payload["is_enabled"]),
            payload.get("description"),
            timestamp,
            rule_id,
        ),
    )
    db_conn.commit()
    row = db_conn.execute(
        """
        SELECT rules.id, rules.scope_type, rules.object_type, rules.monitored_object_id, rules.state_type, rules.metric_key, rules.comparison,
               rules.warning_threshold, rules.critical_threshold, rules.is_enabled, rules.description, rules.created_at, rules.updated_at,
               mo.display_name AS target_display_name, mo.runtime_binding_key AS target_runtime_binding_key
        FROM alert_rules AS rules
        LEFT JOIN monitored_objects AS mo ON mo.id = rules.monitored_object_id
        WHERE rules.id = ?
        """,
        (rule_id,),
    ).fetchone()
    return {"rule": serialize_alert_rule(row)}
