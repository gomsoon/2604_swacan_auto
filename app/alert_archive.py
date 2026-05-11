from __future__ import annotations

import json
from typing import Any


RESOLUTION_SOURCES = {
    "auto_recovery",
    "manual_operator",
    "auto_policy_timeout",
    "system_cleanup",
}


def _resolve_archive_rule_snapshot(db_conn, alert_row) -> tuple[str | None, str | None]:
    source_rule_key = alert_row["source_rule_key"] if "source_rule_key" in alert_row.keys() else None
    source_rule_display_name_snapshot = (
        alert_row["source_rule_display_name_snapshot"]
        if "source_rule_display_name_snapshot" in alert_row.keys()
        else None
    )
    source_rule_id = alert_row["source_rule_id"] if "source_rule_id" in alert_row.keys() else None

    if (source_rule_key or source_rule_display_name_snapshot) or source_rule_id is None:
        return source_rule_key, source_rule_display_name_snapshot

    row = db_conn.execute(
        "SELECT rule_key, display_name FROM alert_rules WHERE id = ?",
        (source_rule_id,),
    ).fetchone()
    if row is None:
        return None, None
    return row["rule_key"], row["display_name"]


def insert_alert_history_archive(
    db_conn,
    *,
    alert_row,
    resolved_at: str,
    resolution_source: str,
    resolution_reason: str | None,
    resolved_by_user_id: int | None,
) -> int:
    if resolution_source not in RESOLUTION_SOURCES:
        raise ValueError("invalid resolution_source")

    source_rule_key, source_rule_display_name_snapshot = _resolve_archive_rule_snapshot(db_conn, alert_row)

    cursor = db_conn.execute(
        """
        INSERT INTO alert_history_archive (
            monitored_object_id,
            alert_code,
            source_rule_id,
            source_rule_key,
            source_rule_display_name_snapshot,
            opened_at,
            resolved_at,
            first_severity,
            highest_severity,
            final_severity,
            final_status,
            repeat_count,
            was_acknowledged,
            last_acknowledged_at,
            last_acknowledged_by_user_id,
            resolution_source,
            resolution_reason,
            resolved_by_user_id,
            latest_message,
            metadata_json,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            alert_row["monitored_object_id"],
            alert_row["alert_code"],
            alert_row["source_rule_id"],
            source_rule_key,
            source_rule_display_name_snapshot,
            alert_row["first_occurred_at"],
            resolved_at,
            alert_row["severity"],
            alert_row["severity"],
            alert_row["severity"],
            "resolved",
            alert_row["repeat_count"],
            1 if alert_row["acknowledged_at"] else 0,
            alert_row["acknowledged_at"],
            alert_row["acknowledged_by_user_id"],
            resolution_source,
            resolution_reason,
            resolved_by_user_id,
            alert_row["latest_message"],
            alert_row["metadata_json"],
            resolved_at,
            resolved_at,
        ),
    )
    return int(cursor.lastrowid)


def serialize_alert_archive_row(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "monitored_object_id": row["monitored_object_id"],
        "runtime_binding_key": row["runtime_binding_key"],
        "display_name": row["display_name"],
        "semantic_type_code": row["semantic_type_code"],
        "alert_code": row["alert_code"],
        "source_rule_id": row["source_rule_id"],
        "source_rule_key": row["source_rule_key"],
        "source_rule_display_name_snapshot": row["source_rule_display_name_snapshot"],
        "source_rule_metric_key": row["source_rule_metric_key"],
        "source_rule_scope_type": row["source_rule_scope_type"],
        "source_rule_target_label": row["source_rule_target_label"],
        "opened_at": row["opened_at"],
        "resolved_at": row["resolved_at"],
        "first_severity": row["first_severity"],
        "highest_severity": row["highest_severity"],
        "final_severity": row["final_severity"],
        "final_status": row["final_status"],
        "repeat_count": row["repeat_count"],
        "was_acknowledged": bool(row["was_acknowledged"]),
        "last_acknowledged_at": row["last_acknowledged_at"],
        "last_acknowledged_by_user_id": row["last_acknowledged_by_user_id"],
        "last_acknowledged_by_username": row["last_acknowledged_by_username"],
        "resolution_source": row["resolution_source"],
        "resolution_reason": row["resolution_reason"],
        "resolved_by_user_id": row["resolved_by_user_id"],
        "resolved_by_username": row["resolved_by_username"],
        "latest_message": row["latest_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if row["metadata_json"]:
        try:
            payload["metadata"] = json.loads(row["metadata_json"])
        except json.JSONDecodeError:
            payload["metadata"] = row["metadata_json"]
    return payload
