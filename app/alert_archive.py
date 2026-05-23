from __future__ import annotations

import json
from typing import Any

from .alert_explainability import build_alert_explanation_from_metadata
from .alert_identity import ALERT_IDENTITY_KIND_RULE, build_rule_identity_key


RESOLUTION_SOURCES = {
    "auto_recovery",
    "manual_operator",
    "auto_policy_timeout",
    "system_cleanup",
}

RESOLUTION_REASON_MANUAL_RESOLVED = "manual_resolved"
RESOLUTION_REASON_STATUS_API = "resolved_from_status_api"
RESOLUTION_REASON_THRESHOLD_CLEARED = "threshold_cleared"
RESOLUTION_REASON_SUPPRESSED_BY_PRECEDENCE = "suppressed_by_precedence"
RESOLUTION_REASON_STATE_NORMALIZED = "state_normalized"
RESOLUTION_REASON_SUPERSEDED = "superseded"


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


def _resolve_archive_opening_rule_snapshot(
    db_conn,
    alert_row,
    source_rule_key: str | None,
    source_rule_display_name_snapshot: str | None,
) -> tuple[int | None, str | None, str | None]:
    row_keys = set(alert_row.keys()) if hasattr(alert_row, "keys") else set()
    opening_rule_id = alert_row["opening_rule_id"] if "opening_rule_id" in row_keys else None
    opening_rule_key = alert_row["opening_rule_key"] if "opening_rule_key" in row_keys else None
    opening_rule_display_name_snapshot = (
        alert_row["opening_rule_display_name_snapshot"]
        if "opening_rule_display_name_snapshot" in row_keys
        else None
    )
    if (opening_rule_key or opening_rule_display_name_snapshot) or opening_rule_id is None:
        if opening_rule_id is None and "source_rule_id" in row_keys:
            opening_rule_id = alert_row["source_rule_id"]
        if opening_rule_key is None:
            opening_rule_key = source_rule_key
        if opening_rule_display_name_snapshot is None:
            opening_rule_display_name_snapshot = source_rule_display_name_snapshot
        return opening_rule_id, opening_rule_key, opening_rule_display_name_snapshot

    row = db_conn.execute(
        "SELECT rule_key, display_name FROM alert_rules WHERE id = ?",
        (opening_rule_id,),
    ).fetchone()
    if row is None:
        return opening_rule_id, source_rule_key, source_rule_display_name_snapshot
    return opening_rule_id, row["rule_key"], row["display_name"]


def _build_winner_transition_summary(
    *,
    opening_rule_id: int | None,
    opening_rule_key: str | None,
    opening_rule_display_name_snapshot: str | None,
    winner_rule_id: int | None,
    winner_rule_key: str | None,
    winner_rule_display_name_snapshot: str | None,
    winner_transition_count: int,
    last_winner_transition_at: str | None,
) -> dict[str, Any]:
    normalized_opening_rule_id = opening_rule_id
    normalized_opening_rule_key = opening_rule_key
    normalized_opening_rule_display_name_snapshot = opening_rule_display_name_snapshot
    if (
        normalized_opening_rule_id is None
        and normalized_opening_rule_key is None
        and normalized_opening_rule_display_name_snapshot is None
        and winner_transition_count == 0
    ):
        normalized_opening_rule_id = winner_rule_id
        normalized_opening_rule_key = winner_rule_key
        normalized_opening_rule_display_name_snapshot = winner_rule_display_name_snapshot
    return {
        "opening_rule": {
            "id": normalized_opening_rule_id,
            "rule_key": normalized_opening_rule_key,
            "display_name": normalized_opening_rule_display_name_snapshot,
        },
        "winner_rule": {
            "id": winner_rule_id,
            "rule_key": winner_rule_key,
            "display_name": winner_rule_display_name_snapshot,
        },
        "transition_count": winner_transition_count,
        "last_transition_at": last_winner_transition_at,
    }


def _merge_archive_metadata_json(raw_metadata_json: str | None, resolution_note: str | None) -> str | None:
    if not resolution_note:
        return raw_metadata_json
    if not raw_metadata_json:
        return json.dumps({"resolution_note": resolution_note})
    try:
        payload = json.loads(raw_metadata_json)
    except json.JSONDecodeError:
        return raw_metadata_json
    if not isinstance(payload, dict):
        return raw_metadata_json
    merged = dict(payload)
    merged["resolution_note"] = resolution_note
    return json.dumps(merged)


def insert_alert_history_archive(
    db_conn,
    *,
    alert_row,
    resolved_at: str,
    resolution_source: str,
    resolution_reason: str | None,
    resolution_note: str | None = None,
    resolved_by_user_id: int | None,
) -> int:
    if resolution_source not in RESOLUTION_SOURCES:
        raise ValueError("invalid resolution_source")

    source_rule_key, source_rule_display_name_snapshot = _resolve_archive_rule_snapshot(db_conn, alert_row)
    (
        opening_rule_id,
        opening_rule_key,
        opening_rule_display_name_snapshot,
    ) = _resolve_archive_opening_rule_snapshot(
        db_conn,
        alert_row,
        source_rule_key,
        source_rule_display_name_snapshot,
    )
    metadata_json = _merge_archive_metadata_json(alert_row["metadata_json"], resolution_note)
    row_keys = set(alert_row.keys()) if hasattr(alert_row, "keys") else set()
    identity_kind = (
        alert_row["identity_kind"] if "identity_kind" in row_keys else ALERT_IDENTITY_KIND_RULE
    )
    identity_key = (
        alert_row["identity_key"]
        if "identity_key" in row_keys
        else build_rule_identity_key(
            source_rule_id=alert_row["source_rule_id"],
            alert_code=alert_row["alert_code"],
        )
    )
    winner_transition_count = (
        int(alert_row["winner_transition_count"])
        if "winner_transition_count" in row_keys and alert_row["winner_transition_count"] is not None
        else 0
    )
    last_winner_transition_at = (
        alert_row["last_winner_transition_at"] if "last_winner_transition_at" in row_keys else None
    )

    cursor = db_conn.execute(
        """
        INSERT INTO alert_history_archive (
            monitored_object_id,
            alert_code,
            source_rule_id,
            source_rule_key,
            source_rule_display_name_snapshot,
            identity_kind,
            identity_key,
            origin_alert_instance_id,
            opening_rule_id,
            opening_rule_key,
            opening_rule_display_name_snapshot,
            winner_transition_count,
            last_winner_transition_at,
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            alert_row["monitored_object_id"],
            alert_row["alert_code"],
            alert_row["source_rule_id"],
            source_rule_key,
            source_rule_display_name_snapshot,
            identity_kind,
            identity_key,
            alert_row["id"] if "id" in row_keys else None,
            opening_rule_id,
            opening_rule_key,
            opening_rule_display_name_snapshot,
            winner_transition_count,
            last_winner_transition_at,
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
            metadata_json,
            resolved_at,
            resolved_at,
        ),
    )
    return int(cursor.lastrowid)


def close_alert_instance_with_archive(
    db_conn,
    *,
    alert_row,
    resolved_at: str,
    last_occurred_at: str,
    status_note: str | None,
    resolution_source: str,
    resolution_reason: str | None,
    resolution_note: str | None = None,
    resolved_by_user_id: int | None,
) -> int:
    db_conn.execute(
        """
        UPDATE alert_instances
        SET status = 'resolved',
            resolved_at = COALESCE(resolved_at, ?),
            resolved_by_user_id = ?,
            status_updated_at = ?,
            status_updated_by_user_id = ?,
            status_note = ?,
            updated_at = ?,
            last_occurred_at = ?
        WHERE id = ?
        """,
        (
            resolved_at,
            resolved_by_user_id,
            resolved_at,
            resolved_by_user_id,
            status_note,
            resolved_at,
            last_occurred_at,
            alert_row["id"],
        ),
    )
    return insert_alert_history_archive(
        db_conn,
        alert_row=alert_row,
        resolved_at=resolved_at,
        resolution_source=resolution_source,
        resolution_reason=resolution_reason,
        resolution_note=resolution_note,
        resolved_by_user_id=resolved_by_user_id,
    )


def serialize_alert_archive_row(row) -> dict[str, Any]:
    winner_transition_count = (
        int(row["winner_transition_count"])
        if "winner_transition_count" in row.keys() and row["winner_transition_count"] is not None
        else 0
    )
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
        "identity_kind": row["identity_kind"] if "identity_kind" in row.keys() else None,
        "identity_key": row["identity_key"] if "identity_key" in row.keys() else None,
        "origin_alert_instance_id": (
            row["origin_alert_instance_id"] if "origin_alert_instance_id" in row.keys() else None
        ),
        "opening_rule_id": row["opening_rule_id"] if "opening_rule_id" in row.keys() else None,
        "opening_rule_key": row["opening_rule_key"] if "opening_rule_key" in row.keys() else None,
        "opening_rule_display_name_snapshot": (
            row["opening_rule_display_name_snapshot"]
            if "opening_rule_display_name_snapshot" in row.keys()
            else None
        ),
        "winner_transition_count": winner_transition_count,
        "last_winner_transition_at": (
            row["last_winner_transition_at"] if "last_winner_transition_at" in row.keys() else None
        ),
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
    metadata = None
    if row["metadata_json"]:
        try:
            metadata = json.loads(row["metadata_json"])
            payload["metadata"] = metadata
        except json.JSONDecodeError:
            metadata = row["metadata_json"]
            payload["metadata"] = metadata
    if isinstance(payload.get("metadata"), dict):
        resolution_note = payload["metadata"].get("resolution_note")
        if isinstance(resolution_note, str) and resolution_note:
            payload["resolution_note"] = resolution_note
    explanation = build_alert_explanation_from_metadata(
        metadata,
        fallback_rule_key=row["source_rule_key"],
        fallback_display_name=row["source_rule_display_name_snapshot"],
        fallback_reason=row["latest_message"],
        resolution_reason=row["resolution_reason"],
    )
    if explanation is not None:
        payload["explanation"] = explanation
    winner_rule_key = row["source_rule_key"]
    winner_rule_display_name_snapshot = row["source_rule_display_name_snapshot"]
    if explanation is not None:
        winner_rule_key = winner_rule_key or explanation.get("winner_rule_key")
        winner_rule_display_name_snapshot = (
            winner_rule_display_name_snapshot or explanation.get("winner_display_name")
        )
    payload["winner_transition_summary"] = _build_winner_transition_summary(
        opening_rule_id=payload["opening_rule_id"],
        opening_rule_key=payload["opening_rule_key"],
        opening_rule_display_name_snapshot=payload["opening_rule_display_name_snapshot"],
        winner_rule_id=row["source_rule_id"],
        winner_rule_key=winner_rule_key,
        winner_rule_display_name_snapshot=winner_rule_display_name_snapshot,
        winner_transition_count=winner_transition_count,
        last_winner_transition_at=payload["last_winner_transition_at"],
    )
    return payload
