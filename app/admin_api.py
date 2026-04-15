from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import Blueprint, current_app, request

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
        "severity": row["severity"],
        "status": row["status"],
        "first_occurred_at": row["first_occurred_at"],
        "last_occurred_at": row["last_occurred_at"],
        "repeat_count": row["repeat_count"],
        "latest_message": row["latest_message"],
    }
    if row["metadata_json"]:
        payload["metadata"] = parse_json_or_text(row["metadata_json"])
    return payload


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
        "open_alerts": fetch_count("SELECT COUNT(*) FROM alert_instances WHERE status = 'open'"),
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
        SELECT id, started_at, finished_at, raw_events_deleted, debug_payload_logs_deleted, ingest_inbox_deleted
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
        SELECT id, started_at, finished_at, raw_events_deleted, debug_payload_logs_deleted, ingest_inbox_deleted
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

    status = request.args.get("status", "open")
    if status not in {"open", "resolved"}:
        return error_response("validation_error", "invalid status filter", 400)

    severity = request.args.get("severity")
    if severity and severity not in {"critical", "warning", "normal", "info"}:
        return error_response("validation_error", "invalid severity filter", 400)

    clauses = ["alerts.status = ?"]
    params: list[Any] = [status]
    if severity:
        clauses.append("alerts.severity = ?")
        params.append(severity)

    sql = """
        SELECT alerts.id, alerts.monitored_object_id, mo.runtime_binding_key, mo.object_type AS semantic_type_code,
               mo.display_name, alerts.alert_code, alerts.severity, alerts.status,
               alerts.first_occurred_at, alerts.last_occurred_at, alerts.repeat_count,
               alerts.latest_message, alerts.metadata_json
        FROM alert_instances AS alerts
        JOIN monitored_objects AS mo ON mo.id = alerts.monitored_object_id
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
