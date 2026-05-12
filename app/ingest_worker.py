from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import sleep

import click
from flask import current_app
from flask.cli import with_appcontext

from .alert_archive import close_alert_instance_with_archive
from .alert_explainability import (
    build_alert_rule_explanation,
    build_alert_rule_reason,
)
from .alert_history import record_alert_history
from .alert_rule_evaluator import (
    EVENT_SIGNAL_TYPE_GROUPED_REPEAT,
    LATEST_STATE_SIGNAL_TYPE,
    THRESHOLD_FIRING_LEVELS,
    alert_rule_value_key,
    event_family_key,
    evaluate_threshold_candidates,
    evaluate_threshold_rule,
    metric_value_for_state,
    normalize_rule_conditions,
    summarize_threshold_decision,
    threshold_family_key,
)
from .db import get_db

VALID_EVENT_TYPES = {
    "process_started",
    "process_stopped",
    "process_restarted",
    "agent_heartbeat_lost",
}
ALERT_OPEN_STATUSES = {"warning", "down"}
ALERT_OPEN_SEVERITIES = {"warning", "critical"}
ALERT_ACTIVE_STATUSES = {"open", "in_progress", "suppressed"}
TIME_DERIVED_THRESHOLD_METRIC_KEYS = {"heartbeat_age_seconds"}


@dataclass(frozen=True)
class IngestWorkerCycleResult:
    processed_batches: int
    failed_batches: int
    processed_items: int
    sleep_seconds: float
    had_error: bool
    error_message: str | None = None


@dataclass(frozen=True)
class IngestWorkerRunSummary:
    cycles: int
    processed_batches: int
    failed_batches: int
    processed_items: int


@dataclass(frozen=True)
class RetentionCleanupSummary:
    raw_events_deleted: int
    grouped_events_deleted: int
    debug_payload_logs_deleted: int
    ingest_inbox_deleted: int
    started_at: str | None = None
    finished_at: str | None = None


def now_iso() -> str:
    return now_dt().isoformat(timespec="milliseconds")


def now_dt() -> datetime:
    provider = current_app.config.get("CURRENT_TIME_PROVIDER")
    if callable(provider):
        value = provider()
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.astimezone()
    return datetime.now().astimezone()


def format_iso(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="milliseconds")


def parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.astimezone()


def is_older_than(timestamp: str | None, cutoff: datetime) -> bool:
    if not timestamp:
        return False
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed < cutoff


def resolve_view_node_id(target_id: str):
    row = get_db().execute(
        """
        SELECT id
        FROM view_nodes
        WHERE target_id = ? AND is_deleted = 0
        ORDER BY id
        LIMIT 1
        """,
        (target_id,),
    ).fetchone()
    return row["id"] if row else None


def resolve_monitored_object_id(target_id: str):
    row = get_db().execute(
        """
        SELECT id
        FROM monitored_objects
        WHERE runtime_binding_key = ?
        ORDER BY id
        LIMIT 1
        """,
        (target_id,),
    ).fetchone()
    return row["id"] if row else None


def normalize_alert_severity(severity: str | None, status: str) -> str:
    if severity in {"critical", "warning", "normal", "info"}:
        return severity
    if status == "down":
        return "critical"
    return "warning"


def alert_code_for_state(*, state_type: str, status: str, severity: str | None) -> str | None:
    if status in ALERT_OPEN_STATUSES:
        return f"{state_type}.{status}"
    if severity in ALERT_OPEN_SEVERITIES:
        return f"{state_type}.{severity}"
    return None


def alert_message_for_state(*, state_type: str, status: str, state: dict) -> str:
    if state.get("message"):
        return str(state["message"])
    if state.get("event_type"):
        return f"{state_type} {state['event_type']}"
    return f"{state_type} status changed to {status}"


def create_alert_instance(
    *,
    monitored_object_id: int,
    alert_code: str,
    severity: str,
    occurred_at: str,
    received_at: str,
    latest_message: str,
    metadata_json: str,
    source_rule_id: int | None = None,
) -> None:
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO alert_instances (
            monitored_object_id, alert_code, source_rule_id, severity, status,
            status_updated_at, status_updated_by_user_id, status_note,
            first_occurred_at, last_occurred_at, repeat_count,
            latest_message, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'open', ?, NULL, NULL, ?, ?, 1, ?, ?, ?, ?)
        """,
        (
            monitored_object_id,
            alert_code,
            source_rule_id,
            severity,
            received_at,
            occurred_at,
            occurred_at,
            latest_message,
            metadata_json,
            received_at,
            received_at,
        ),
    )
    record_alert_history(
        db_conn,
        alert_instance_id=cursor.lastrowid,
        action_type="created",
        created_at=received_at,
        previous_status=None,
        new_status="open",
        previous_acknowledged=False,
        new_acknowledged=False,
        payload={
            "source": "worker",
            "alert_code": alert_code,
            "source_rule_id": source_rule_id,
        },
    )


def resolve_alert_rows(
    *,
    rows,
    occurred_at: str,
    received_at: str,
    note: str,
    payload: dict,
    resolution_source: str,
    resolution_reason: str,
) -> None:
    db_conn = get_db()
    for row in rows:
        archive_id = close_alert_instance_with_archive(
            db_conn,
            alert_row=row,
            resolved_at=received_at,
            last_occurred_at=occurred_at,
            status_note=note,
            resolution_source=resolution_source,
            resolution_reason=resolution_reason,
            resolved_by_user_id=None,
        )
        record_alert_history(
            db_conn,
            alert_instance_id=row["id"],
            action_type="resolved",
            created_at=received_at,
            previous_status=row["status"],
            new_status="resolved",
            previous_acknowledged=row["acknowledged_at"] is not None,
            new_acknowledged=row["acknowledged_at"] is not None,
            note=note,
            payload={
                **payload,
                "resolution_source": resolution_source,
                "archive_id": archive_id,
            },
        )


def sync_latest_state_alert(
    *,
    monitored_object_id: int | None,
    state_type: str,
    status: str,
    severity: str | None,
    state: dict,
    occurred_at: str,
    received_at: str,
) -> None:
    if monitored_object_id is None:
        return

    db_conn = get_db()
    alert_prefix = f"{state_type}."
    alert_code = alert_code_for_state(state_type=state_type, status=status, severity=severity)

    if alert_code is None:
        rows_to_resolve = db_conn.execute(
            """
            SELECT id, monitored_object_id, alert_code, source_rule_id, severity, status,
                   acknowledged_at, acknowledged_by_user_id,
                   first_occurred_at, last_occurred_at, repeat_count,
                   latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = ?
              AND status != 'resolved'
              AND alert_code LIKE ?
            """,
            (monitored_object_id, f"{alert_prefix}%"),
        ).fetchall()
        resolve_alert_rows(
            rows=rows_to_resolve,
            occurred_at=occurred_at,
            received_at=received_at,
            note="state normalized",
            payload={"source": "worker", "reason": "state_normalized", "state_type": state_type},
            resolution_source="auto_recovery",
            resolution_reason="state_normalized",
        )
        return

    normalized_severity = normalize_alert_severity(severity, status)
    latest_message = alert_message_for_state(state_type=state_type, status=status, state=state)
    metadata_json = json.dumps(state, ensure_ascii=False)

    rows_to_resolve = db_conn.execute(
        """
        SELECT id, monitored_object_id, alert_code, source_rule_id, severity, status,
               acknowledged_at, acknowledged_by_user_id,
               first_occurred_at, last_occurred_at, repeat_count,
               latest_message, metadata_json
        FROM alert_instances
        WHERE monitored_object_id = ?
          AND status != 'resolved'
          AND alert_code LIKE ?
          AND alert_code != ?
        """,
        (monitored_object_id, f"{alert_prefix}%", alert_code),
    ).fetchall()
    resolve_alert_rows(
        rows=rows_to_resolve,
        occurred_at=occurred_at,
        received_at=received_at,
        note="superseded by new state",
        payload={
            "source": "worker",
            "reason": "superseded",
            "state_type": state_type,
            "active_alert_code": alert_code,
        },
        resolution_source="system_cleanup",
        resolution_reason="superseded",
    )

    existing = db_conn.execute(
        """
        SELECT id, status
        FROM alert_instances
        WHERE monitored_object_id = ?
          AND alert_code = ?
          AND status != 'resolved'
        ORDER BY id DESC
        LIMIT 1
        """,
        (monitored_object_id, alert_code),
    ).fetchone()

    if existing is None:
        create_alert_instance(
            monitored_object_id=monitored_object_id,
            alert_code=alert_code,
            severity=normalized_severity,
            occurred_at=occurred_at,
            received_at=received_at,
            latest_message=latest_message,
            metadata_json=metadata_json,
        )
        return

    db_conn.execute(
        """
        UPDATE alert_instances
        SET severity = ?,
            last_occurred_at = ?,
            repeat_count = repeat_count + 1,
            latest_message = ?,
            metadata_json = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            normalized_severity,
            occurred_at,
            latest_message,
            metadata_json,
            received_at,
            existing["id"],
        ),
    )


def numeric_metric_value(state: dict, metric_key: str) -> float | None:
    return metric_value_for_state(state, metric_key)


def threshold_level(metric_value: float | None, rule) -> str | None:
    evaluation = evaluate_threshold_rule(metric_value, rule)
    return evaluation["threshold_level"] if evaluation["threshold_level"] in THRESHOLD_FIRING_LEVELS else None


def threshold_message(rule, metric_value: float, level: str) -> str:
    return build_alert_rule_reason(
        rule,
        threshold_level=level,
        metric_value=metric_value,
    ) or "-"


def fetch_open_alert_rows_for_rule_ids(*, monitored_object_id: int, rule_ids: list[int]):
    if not rule_ids:
        return []

    placeholders = ", ".join("?" for _ in rule_ids)
    return get_db().execute(
        f"""
        SELECT id, monitored_object_id, alert_code, source_rule_id, severity, status,
               acknowledged_at, acknowledged_by_user_id,
               first_occurred_at, last_occurred_at, repeat_count,
               latest_message, metadata_json
        FROM alert_instances
        WHERE monitored_object_id = ?
          AND status != 'resolved'
          AND source_rule_id IN ({placeholders})
        """,
        (monitored_object_id, *rule_ids),
    ).fetchall()


def build_threshold_alert_metadata(rule, metric_value: float, level: str, family_key: tuple[str, str | None, str | None, str | None]) -> str:
    cond_mode, warning_condition, critical_condition = normalize_rule_conditions(rule)
    reason = build_alert_rule_reason(
        rule,
        threshold_level=level,
        metric_value=metric_value,
    )
    explanation = build_alert_rule_explanation(
        rule,
        threshold_level=level,
        reason=reason,
        winning_condition_trace=rule.get("_winning_condition_trace"),
        family_key=family_key,
        winner_rule_key=rule.get("rule_key"),
        suppressed_rule_keys=rule.get("_suppressed_rule_keys"),
        resolution_reason=None,
    )
    return json.dumps(
        {
            "rule_id": rule["id"],
            "rule_key": rule.get("rule_key"),
            "display_name": rule.get("display_name"),
            "metric_key": rule["metric_key"],
            "metric_value": metric_value,
            "comparison": rule["comparison"],
            "warning_threshold": rule["warning_threshold"],
            "critical_threshold": rule["critical_threshold"],
            "scope_type": rule["scope_type"],
            "threshold_level": level,
            "cond_mode": cond_mode,
            "warning_condition": warning_condition,
            "critical_condition": critical_condition,
            "reason": reason,
            "winning_condition_trace": rule.get("_winning_condition_trace"),
            "winner_rule_key": rule.get("rule_key"),
            "suppressed_rule_keys": rule.get("_suppressed_rule_keys") or [],
            "family_key": list(family_key),
            "explanation": explanation,
        },
        ensure_ascii=False,
    )


def load_recent_grouped_event(*, monitored_object_id: int, signal_key: str, received_at: str) -> dict | None:
    row = get_db().execute(
        """
        SELECT id, event_type, severity, repeat_count, first_occurred_at, last_occurred_at, latest_message
        FROM grouped_events
        WHERE monitored_object_id = ?
          AND event_type = ?
        ORDER BY last_occurred_at DESC, id DESC
        LIMIT 1
        """,
        (monitored_object_id, signal_key),
    ).fetchone()
    if row is None:
        return None

    try:
        received_dt = parse_iso(received_at)
        last_dt = parse_iso(row["last_occurred_at"])
    except (TypeError, ValueError):
        return None

    window_seconds = int(current_app.config.get("GROUPED_EVENT_WINDOW_SECONDS", 60))
    if abs((received_dt - last_dt).total_seconds()) > window_seconds:
        return None
    return dict(row)


def event_message(rule, repeat_count: float, level: str) -> str:
    return build_alert_rule_reason(
        rule,
        threshold_level=level,
        metric_value=repeat_count,
    ) or "-"


def build_event_alert_metadata(rule, grouped_event: dict, level: str, family_key: tuple[str, str | None, str | None, str | None]) -> str:
    reason = build_alert_rule_reason(
        rule,
        threshold_level=level,
        grouped_event=grouped_event,
    )
    explanation = build_alert_rule_explanation(
        rule,
        threshold_level=level,
        reason=reason,
        winning_condition_trace=rule.get("_winning_condition_trace"),
        family_key=family_key,
        winner_rule_key=rule.get("rule_key"),
        suppressed_rule_keys=rule.get("_suppressed_rule_keys"),
        resolution_reason=None,
    )
    return json.dumps(
        {
            "rule_id": rule["id"],
            "rule_key": rule.get("rule_key"),
            "display_name": rule.get("display_name"),
            "signal_type": rule.get("signal_type"),
            "signal_key": rule.get("signal_key"),
            "repeat_count": grouped_event["repeat_count"],
            "first_occurred_at": grouped_event["first_occurred_at"],
            "last_occurred_at": grouped_event["last_occurred_at"],
            "latest_message": grouped_event.get("latest_message"),
            "comparison": rule["comparison"],
            "warning_threshold": rule["warning_threshold"],
            "critical_threshold": rule["critical_threshold"],
            "scope_type": rule["scope_type"],
            "threshold_level": level,
            "cond_mode": "scalar",
            "reason": reason,
            "winning_condition_trace": rule.get("_winning_condition_trace"),
            "winner_rule_key": rule.get("rule_key"),
            "suppressed_rule_keys": rule.get("_suppressed_rule_keys") or [],
            "family_key": list(family_key),
            "explanation": explanation,
        },
        ensure_ascii=False,
    )


def sync_threshold_alerts(
    *,
    monitored_object_id: int | None,
    state_type: str,
    state: dict,
    occurred_at: str,
    received_at: str,
    allowed_metric_keys: set[str] | None = None,
    increment_repeat_count: bool = True,
) -> None:
    if monitored_object_id is None:
        return

    db_conn = get_db()
    object_row = db_conn.execute(
        "SELECT object_type FROM monitored_objects WHERE id = ?",
        (monitored_object_id,),
    ).fetchone()
    if object_row is None:
        return

    rules = db_conn.execute(
        """
        SELECT id, rule_key, display_name, status, scope_type, object_type, monitored_object_id,
               state_type, signal_type, signal_key, metric_key, comparison, warning_threshold, critical_threshold,
               cond_mode,
               warning_logical_op, warning_cl1_comp, warning_cl1_val, warning_cl2_comp, warning_cl2_val,
               critical_logical_op, critical_cl1_comp, critical_cl1_val, critical_cl2_comp, critical_cl2_val,
               is_enabled, description, created_at, updated_at
        FROM alert_rules
        WHERE is_enabled = 1
          AND status = 'published'
          AND signal_type = ?
          AND state_type = ?
          AND (
                (scope_type = 'monitored_object' AND monitored_object_id = ?)
             OR (scope_type = 'object_type' AND object_type = ?)
          )
        ORDER BY id ASC
        """,
        (LATEST_STATE_SIGNAL_TYPE, state_type, monitored_object_id, object_row["object_type"]),
    ).fetchall()

    families: dict[tuple[str, str | None, str | None, str | None], list] = {}
    for rule_row in rules:
        rule = dict(rule_row)
        metric_key = rule.get("metric_key")
        if allowed_metric_keys is not None and metric_key not in allowed_metric_keys:
            continue
        families.setdefault(threshold_family_key(rule), []).append(rule)

    for family_key, family_rules in families.items():
        metric_value = numeric_metric_value(state, family_rules[0]["metric_key"])
        candidates = evaluate_threshold_candidates(metric_value, [{**dict(rule), "_origin": "runtime_rule"} for rule in family_rules])
        decision = summarize_threshold_decision(candidates)
        winner_rule = decision["winner_rule"]
        firing_rule_ids = [rule_id for rule_id in decision["firing_rule_ids"] if isinstance(rule_id, int)]
        winner_rule_id = decision["winner_rule_id"] if isinstance(decision["winner_rule_id"], int) else None
        losing_rule_ids = [rule_id for rule_id in firing_rule_ids if rule_id != winner_rule_id]
        non_firing_rule_ids = [
            rule["id"]
            for rule in family_rules
            if isinstance(rule["id"], int) and rule["id"] not in firing_rule_ids
        ]

        if non_firing_rule_ids:
            resolve_alert_rows(
                rows=fetch_open_alert_rows_for_rule_ids(
                    monitored_object_id=monitored_object_id,
                    rule_ids=non_firing_rule_ids,
                ),
                occurred_at=occurred_at,
                received_at=received_at,
                note="threshold no longer matched",
                payload={
                    "source": "worker",
                    "reason": "threshold_cleared",
                    "family_key": list(family_key),
                },
                resolution_source="auto_recovery",
                resolution_reason="threshold_cleared",
            )

        if losing_rule_ids:
            resolve_alert_rows(
                rows=fetch_open_alert_rows_for_rule_ids(
                    monitored_object_id=monitored_object_id,
                    rule_ids=losing_rule_ids,
                ),
                occurred_at=occurred_at,
                received_at=received_at,
                note="suppressed by threshold precedence",
                payload={
                    "source": "worker",
                    "reason": "suppressed_by_precedence",
                    "family_key": list(family_key),
                    "winner_rule_id": winner_rule_id,
                },
                resolution_source="system_cleanup",
                resolution_reason="suppressed_by_precedence",
            )

        if winner_rule is None or metric_value is None or winner_rule_id is None:
            continue

        winner_level = winner_rule["_threshold_level"]
        winner_rule["_suppressed_rule_keys"] = decision["suppressed_rule_keys"]
        latest_message = threshold_message(winner_rule, metric_value, winner_level)
        metadata_json = build_threshold_alert_metadata(winner_rule, metric_value, winner_level, family_key)
        alert_code = f"rule.{winner_rule_id}"
        existing = db_conn.execute(
            """
            SELECT id, status, severity, last_occurred_at, latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = ?
              AND source_rule_id = ?
              AND status != 'resolved'
            ORDER BY id DESC
            LIMIT 1
            """,
            (monitored_object_id, winner_rule_id),
        ).fetchone()

        if existing is None:
            create_alert_instance(
                monitored_object_id=monitored_object_id,
                alert_code=alert_code,
                source_rule_id=winner_rule_id,
                severity=winner_level,
                occurred_at=occurred_at,
                received_at=received_at,
                latest_message=latest_message,
                metadata_json=metadata_json,
            )
            continue

        if increment_repeat_count:
            db_conn.execute(
                """
                UPDATE alert_instances
                SET source_rule_id = ?,
                    severity = ?,
                    last_occurred_at = ?,
                    repeat_count = repeat_count + 1,
                    latest_message = ?,
                    metadata_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    winner_rule_id,
                    winner_level,
                    occurred_at,
                    latest_message,
                    metadata_json,
                    received_at,
                    existing["id"],
                ),
            )
            continue

        should_refresh_last_occurred = (
            existing["severity"] != winner_level
            or existing["latest_message"] != latest_message
            or existing["metadata_json"] != metadata_json
        )
        db_conn.execute(
            """
            UPDATE alert_instances
            SET source_rule_id = ?,
                severity = ?,
                last_occurred_at = ?,
                latest_message = ?,
                metadata_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                winner_rule_id,
                winner_level,
                occurred_at if should_refresh_last_occurred else existing["last_occurred_at"],
                latest_message,
                metadata_json,
                received_at,
                existing["id"],
            ),
        )


def reevaluate_time_derived_threshold_alerts(*, received_at: str) -> None:
    db_conn = get_db()
    placeholders = ", ".join("?" for _ in TIME_DERIVED_THRESHOLD_METRIC_KEYS)
    rows = db_conn.execute(
        f"""
        SELECT DISTINCT
            ls.monitored_object_id,
            ls.state_type,
            ls.state_json
        FROM latest_states AS ls
        JOIN monitored_objects AS mo ON mo.id = ls.monitored_object_id
        JOIN alert_rules AS rules
          ON rules.is_enabled = 1
         AND rules.status = 'published'
         AND rules.signal_type = ?
         AND rules.state_type = ls.state_type
         AND rules.metric_key IN ({placeholders})
         AND (
               (rules.scope_type = 'monitored_object' AND rules.monitored_object_id = ls.monitored_object_id)
            OR (rules.scope_type = 'object_type' AND rules.object_type = mo.object_type)
         )
        WHERE ls.state_type = 'agent'
        """,
        (LATEST_STATE_SIGNAL_TYPE, *TIME_DERIVED_THRESHOLD_METRIC_KEYS),
    ).fetchall()

    for row in rows:
        try:
            state = json.loads(row["state_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(state, dict):
            continue
        sync_threshold_alerts(
            monitored_object_id=row["monitored_object_id"],
            state_type=row["state_type"],
            state=state,
            occurred_at=received_at,
            received_at=received_at,
            allowed_metric_keys=TIME_DERIVED_THRESHOLD_METRIC_KEYS,
            increment_repeat_count=False,
        )


def sync_event_alerts(
    *,
    monitored_object_id: int | None,
    state_type: str,
    occurred_at: str,
    received_at: str,
) -> None:
    if monitored_object_id is None or state_type != "process":
        return

    db_conn = get_db()
    object_row = db_conn.execute(
        "SELECT object_type FROM monitored_objects WHERE id = ?",
        (monitored_object_id,),
    ).fetchone()
    if object_row is None:
        return

    rules = db_conn.execute(
        """
        SELECT id, rule_key, display_name, status, scope_type, object_type, monitored_object_id,
               state_type, signal_type, signal_key, metric_key, comparison, warning_threshold, critical_threshold,
               cond_mode,
               warning_logical_op, warning_cl1_comp, warning_cl1_val, warning_cl2_comp, warning_cl2_val,
               critical_logical_op, critical_cl1_comp, critical_cl1_val, critical_cl2_comp, critical_cl2_val,
               is_enabled, description, created_at, updated_at
        FROM alert_rules
        WHERE is_enabled = 1
          AND status = 'published'
          AND signal_type = ?
          AND state_type = ?
          AND (
                (scope_type = 'monitored_object' AND monitored_object_id = ?)
             OR (scope_type = 'object_type' AND object_type = ?)
          )
        ORDER BY id ASC
        """,
        (EVENT_SIGNAL_TYPE_GROUPED_REPEAT, state_type, monitored_object_id, object_row["object_type"]),
    ).fetchall()
    if not rules:
        return

    families: dict[tuple[str, str | None, str | None, str | None], list] = {}
    for rule_row in rules:
        rule = dict(rule_row)
        families.setdefault(event_family_key(rule), []).append(rule)

    for family_key, family_rules in families.items():
        grouped_event = load_recent_grouped_event(
            monitored_object_id=monitored_object_id,
            signal_key=family_rules[0]["signal_key"],
            received_at=received_at,
        )
        repeat_count = float(grouped_event["repeat_count"]) if grouped_event is not None else None
        candidates = evaluate_threshold_candidates(repeat_count, [{**dict(rule), "_origin": "runtime_rule"} for rule in family_rules])
        decision = summarize_threshold_decision(candidates)
        winner_rule = decision["winner_rule"]
        firing_rule_ids = [rule_id for rule_id in decision["firing_rule_ids"] if isinstance(rule_id, int)]
        winner_rule_id = decision["winner_rule_id"] if isinstance(decision["winner_rule_id"], int) else None
        losing_rule_ids = [rule_id for rule_id in firing_rule_ids if rule_id != winner_rule_id]
        non_firing_rule_ids = [
            rule["id"]
            for rule in family_rules
            if isinstance(rule["id"], int) and rule["id"] not in firing_rule_ids
        ]

        if non_firing_rule_ids:
            resolve_alert_rows(
                rows=fetch_open_alert_rows_for_rule_ids(
                    monitored_object_id=monitored_object_id,
                    rule_ids=non_firing_rule_ids,
                ),
                occurred_at=occurred_at,
                received_at=received_at,
                note="event repeat window elapsed",
                payload={
                    "source": "worker",
                    "reason": "event_window_elapsed",
                    "family_key": list(family_key),
                },
                resolution_source="auto_recovery",
                resolution_reason="event_window_elapsed",
            )

        if losing_rule_ids:
            resolve_alert_rows(
                rows=fetch_open_alert_rows_for_rule_ids(
                    monitored_object_id=monitored_object_id,
                    rule_ids=losing_rule_ids,
                ),
                occurred_at=occurred_at,
                received_at=received_at,
                note="suppressed by event precedence",
                payload={
                    "source": "worker",
                    "reason": "suppressed_by_precedence",
                    "family_key": list(family_key),
                    "winner_rule_id": winner_rule_id,
                },
                resolution_source="system_cleanup",
                resolution_reason="suppressed_by_precedence",
            )

        if winner_rule is None or repeat_count is None or grouped_event is None or winner_rule_id is None:
            continue

        winner_level = winner_rule["_threshold_level"]
        winner_rule["_suppressed_rule_keys"] = decision["suppressed_rule_keys"]
        latest_message = event_message(winner_rule, repeat_count, winner_level)
        metadata_json = build_event_alert_metadata(winner_rule, grouped_event, winner_level, family_key)
        alert_code = f"rule.{winner_rule_id}"
        existing = db_conn.execute(
            """
            SELECT id, status
            FROM alert_instances
            WHERE monitored_object_id = ?
              AND source_rule_id = ?
              AND status != 'resolved'
            ORDER BY id DESC
            LIMIT 1
            """,
            (monitored_object_id, winner_rule_id),
        ).fetchone()

        if existing is None:
            create_alert_instance(
                monitored_object_id=monitored_object_id,
                alert_code=alert_code,
                source_rule_id=winner_rule_id,
                severity=winner_level,
                occurred_at=occurred_at,
                received_at=received_at,
                latest_message=latest_message,
                metadata_json=metadata_json,
            )
            continue

        db_conn.execute(
            """
            UPDATE alert_instances
            SET source_rule_id = ?,
                severity = ?,
                last_occurred_at = ?,
                repeat_count = repeat_count + 1,
                latest_message = ?,
                metadata_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                winner_rule_id,
                winner_level,
                occurred_at,
                latest_message,
                metadata_json,
                received_at,
                existing["id"],
            ),
        )


def upsert_latest_state(*, target_id: str, state_type: str, status: str, severity: str | None, state: dict, occurred_at: str, received_at: str) -> None:
    db_conn = get_db()
    existing = db_conn.execute(
        "SELECT id FROM latest_states WHERE target_id = ? AND state_type = ?",
        (target_id, state_type),
    ).fetchone()
    payload_json = json.dumps(state, ensure_ascii=False)
    view_node_id = resolve_view_node_id(target_id)
    monitored_object_id = resolve_monitored_object_id(target_id)

    if existing is None:
        next_id = db_conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM latest_states").fetchone()["next_id"]
        db_conn.execute(
            """
            INSERT INTO latest_states (
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_id,
                view_node_id,
                monitored_object_id,
                target_id,
                state_type,
                status,
                severity,
                payload_json,
                occurred_at,
                received_at,
                received_at,
            ),
        )
        sync_latest_state_alert(
            monitored_object_id=monitored_object_id,
            state_type=state_type,
            status=status,
            severity=severity,
            state=state,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        sync_threshold_alerts(
            monitored_object_id=monitored_object_id,
            state_type=state_type,
            state=state,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        sync_event_alerts(
            monitored_object_id=monitored_object_id,
            state_type=state_type,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        return

    db_conn.execute(
        """
        UPDATE latest_states
        SET view_node_id = ?, monitored_object_id = ?, status = ?, severity = ?, state_json = ?, occurred_at = ?, received_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            view_node_id,
            monitored_object_id,
            status,
            severity,
            payload_json,
            occurred_at,
            received_at,
            received_at,
            existing["id"],
        ),
    )
    sync_latest_state_alert(
        monitored_object_id=monitored_object_id,
        state_type=state_type,
        status=status,
        severity=severity,
        state=state,
        occurred_at=occurred_at,
        received_at=received_at,
    )
    sync_threshold_alerts(
        monitored_object_id=monitored_object_id,
        state_type=state_type,
        state=state,
        occurred_at=occurred_at,
        received_at=received_at,
    )
    sync_event_alerts(
        monitored_object_id=monitored_object_id,
        state_type=state_type,
        occurred_at=occurred_at,
        received_at=received_at,
    )


def sync_grouped_event(
    *,
    monitored_object_id: int | None,
    target_id: str,
    event_type: str,
    severity: str,
    message: str | None,
    event_payload: dict,
    occurred_at: str,
    received_at: str,
) -> None:
    db_conn = get_db()
    window_seconds = int(current_app.config.get("GROUPED_EVENT_WINDOW_SECONDS", 60))

    if monitored_object_id is not None:
        existing = db_conn.execute(
            """
            SELECT id, last_occurred_at
            FROM grouped_events
            WHERE monitored_object_id = ?
              AND event_type = ?
              AND severity = ?
            ORDER BY last_occurred_at DESC, id DESC
            LIMIT 1
            """,
            (monitored_object_id, event_type, severity),
        ).fetchone()
    else:
        existing = db_conn.execute(
            """
            SELECT id, last_occurred_at
            FROM grouped_events
            WHERE monitored_object_id IS NULL
              AND target_id = ?
              AND event_type = ?
              AND severity = ?
            ORDER BY last_occurred_at DESC, id DESC
            LIMIT 1
            """,
            (target_id, event_type, severity),
        ).fetchone()

    if existing is not None:
        occurred_dt = parse_iso(occurred_at)
        last_dt = parse_iso(existing["last_occurred_at"])
        if abs((occurred_dt - last_dt).total_seconds()) <= window_seconds:
            db_conn.execute(
                """
                UPDATE grouped_events
                SET last_occurred_at = ?,
                    repeat_count = repeat_count + 1,
                    latest_message = ?,
                    latest_event_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    occurred_at,
                    message,
                    json.dumps(event_payload, ensure_ascii=False),
                    received_at,
                    existing["id"],
                ),
            )
            return

    db_conn.execute(
        """
        INSERT INTO grouped_events (
            monitored_object_id, target_id, event_type, severity, first_occurred_at, last_occurred_at,
            repeat_count, latest_message, latest_event_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """,
        (
            monitored_object_id,
            target_id,
            event_type,
            severity,
            occurred_at,
            occurred_at,
            message,
            json.dumps(event_payload, ensure_ascii=False),
            received_at,
            received_at,
        ),
    )


def insert_raw_event(*, agent_id: str, target_id: str, event_type: str, severity: str, message: str | None, event_payload: dict, occurred_at: str, received_at: str) -> None:
    monitored_object_id = resolve_monitored_object_id(target_id)
    get_db().execute(
        """
        INSERT INTO raw_events (
            agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            monitored_object_id,
            target_id,
            event_type,
            severity,
            message,
            json.dumps(event_payload, ensure_ascii=False),
            occurred_at,
            received_at,
        ),
    )
    sync_grouped_event(
        monitored_object_id=monitored_object_id,
        target_id=target_id,
        event_type=event_type,
        severity=severity,
        message=message,
        event_payload=event_payload,
        occurred_at=occurred_at,
        received_at=received_at,
    )


def process_item_if_new(*, inbox_id: int, agent_id: str, boot_id: str, item: dict, received_at: str) -> bool:
    db_conn = get_db()
    item_seq = int(item["seq"])
    cursor = db_conn.execute(
        """
        INSERT OR IGNORE INTO processed_item_receipts (
            agent_id, boot_id, item_seq, payload_type, target_id, inbox_id, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            boot_id,
            item_seq,
            item["payload_type"],
            item["target_id"],
            inbox_id,
            received_at,
        ),
    )
    if cursor.rowcount == 0:
        return False

    process_item(agent_id, item, received_at)
    return True


def process_item(agent_id: str, item: dict, received_at: str) -> None:
    payload_type = item["payload_type"]
    target_id = item["target_id"]
    occurred_at = item["occurred_at"]
    payload = item["payload"]

    if payload_type == "agent_state":
        status = payload.get("status", "up")
        severity = payload.get("severity", "normal")
        upsert_latest_state(
            target_id=target_id,
            state_type="agent",
            status=status,
            severity=severity,
            state=payload,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        return

    if payload_type == "host_snapshot":
        upsert_latest_state(
            target_id=target_id,
            state_type="host",
            status="up",
            severity=payload.get("severity", "normal"),
            state=payload,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        return

    if payload_type == "process_snapshot":
        process_state = payload.get("state")
        if process_state in ("running", "up"):
            status = "up"
            severity = payload.get("severity", "normal")
        elif process_state in ("stopped", "down"):
            status = "down"
            severity = payload.get("severity", "warning")
        else:
            status = payload.get("status", "unknown")
            severity = payload.get("severity")

        upsert_latest_state(
            target_id=target_id,
            state_type="process",
            status=status,
            severity=severity,
            state=payload,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        return

    if payload_type in {"process_event", "agent_event"}:
        event_type = payload.get("event_type")
        if event_type not in VALID_EVENT_TYPES:
            raise ValueError("unsupported event_type")

        if event_type == "process_started":
            status = "up"
            severity = payload.get("severity", "normal")
            state_type = "process"
        elif event_type == "process_stopped":
            status = "down"
            severity = payload.get("severity", "warning")
            state_type = "process"
        elif event_type == "process_restarted":
            status = "warning"
            severity = payload.get("severity", "warning")
            state_type = "process"
        else:
            status = "warning"
            severity = payload.get("severity", "warning")
            state_type = "agent"

        insert_raw_event(
            agent_id=agent_id,
            target_id=target_id,
            event_type=event_type,
            severity=severity,
            message=payload.get("message"),
            event_payload=payload,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        upsert_latest_state(
            target_id=target_id,
            state_type=state_type,
            status=status,
            severity=severity,
            state=payload,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        return

    raise ValueError("unsupported payload_type")


def process_pending_ingest(limit: int = 100) -> dict[str, int]:
    db_conn = get_db()
    rows = db_conn.execute(
        """
        SELECT id, agent_id, boot_id, received_at, payload_json
        FROM ingest_inbox
        WHERE status = 'pending'
        ORDER BY id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    processed_batches = 0
    failed_batches = 0
    processed_items = 0

    for row in rows:
        db_conn.execute(
            "UPDATE ingest_inbox SET status = 'processing' WHERE id = ?",
            (row["id"],),
        )
        db_conn.commit()

        try:
            payload = json.loads(row["payload_json"])
            db_conn.execute("BEGIN")
            batch_processed_items = 0
            for item in payload["items"]:
                if process_item_if_new(
                    inbox_id=row["id"],
                    agent_id=row["agent_id"],
                    boot_id=row["boot_id"],
                    item=item,
                    received_at=row["received_at"],
                ):
                    batch_processed_items += 1
            db_conn.execute(
                "UPDATE ingest_inbox SET status = 'processed', processed_at = ?, error_message = NULL WHERE id = ?",
                (now_iso(), row["id"]),
            )
            db_conn.commit()
            processed_batches += 1
            processed_items += batch_processed_items
        except Exception as exc:
            if db_conn.in_transaction:
                db_conn.rollback()
            db_conn.execute(
                "UPDATE ingest_inbox SET status = 'failed', error_message = ? WHERE id = ?",
                (str(exc), row["id"]),
            )
            db_conn.commit()
            failed_batches += 1

    reevaluate_time_derived_threshold_alerts(received_at=now_iso())
    db_conn.commit()

    return {
        "processed_batches": processed_batches,
        "failed_batches": failed_batches,
        "processed_items": processed_items,
    }


def cleanup_runtime_data(
    *,
    current_time: datetime | None = None,
    raw_event_retention_days: int | None = None,
    grouped_event_retention_days: int | None = None,
    debug_payload_retention_hours: int | None = None,
    ingest_inbox_retention_days: int | None = None,
) -> RetentionCleanupSummary:
    db_conn = get_db()
    now = current_time or now_dt()
    started_at = format_iso(now)
    raw_days = int(
        raw_event_retention_days
        if raw_event_retention_days is not None
        else current_app.config.get("RAW_EVENT_RETENTION_DAYS", 7)
    )
    grouped_days = int(
        grouped_event_retention_days
        if grouped_event_retention_days is not None
        else current_app.config.get("GROUPED_EVENT_RETENTION_DAYS", raw_days)
    )
    debug_hours = int(
        debug_payload_retention_hours
        if debug_payload_retention_hours is not None
        else current_app.config.get("DEBUG_PAYLOAD_RETENTION_HOURS", 24)
    )
    inbox_days = int(
        ingest_inbox_retention_days
        if ingest_inbox_retention_days is not None
        else current_app.config.get("INGEST_INBOX_RETENTION_DAYS", 7)
    )

    raw_cutoff = now - timedelta(days=raw_days)
    grouped_cutoff = now - timedelta(days=grouped_days)
    debug_cutoff = now - timedelta(hours=debug_hours)
    inbox_cutoff = now - timedelta(days=inbox_days)

    raw_rows = db_conn.execute("SELECT id, occurred_at FROM raw_events").fetchall()
    raw_delete_ids = [row["id"] for row in raw_rows if is_older_than(row["occurred_at"], raw_cutoff)]

    grouped_rows = db_conn.execute("SELECT id, last_occurred_at FROM grouped_events").fetchall()
    grouped_delete_ids = [row["id"] for row in grouped_rows if is_older_than(row["last_occurred_at"], grouped_cutoff)]

    debug_rows = db_conn.execute("SELECT id, occurred_at FROM debug_payload_logs").fetchall()
    debug_delete_ids = [row["id"] for row in debug_rows if is_older_than(row["occurred_at"], debug_cutoff)]

    inbox_rows = db_conn.execute(
        """
        SELECT id, status, received_at, processed_at
        FROM ingest_inbox
        WHERE status IN ('processed', 'failed')
        """
    ).fetchall()
    inbox_delete_ids = []
    for row in inbox_rows:
        reference_time = row["processed_at"] or row["received_at"]
        if is_older_than(reference_time, inbox_cutoff):
            inbox_delete_ids.append(row["id"])

    if raw_delete_ids:
        placeholders = ", ".join("?" for _ in raw_delete_ids)
        db_conn.execute(f"DELETE FROM raw_events WHERE id IN ({placeholders})", tuple(raw_delete_ids))

    if grouped_delete_ids:
        placeholders = ", ".join("?" for _ in grouped_delete_ids)
        db_conn.execute(f"DELETE FROM grouped_events WHERE id IN ({placeholders})", tuple(grouped_delete_ids))

    if debug_delete_ids:
        placeholders = ", ".join("?" for _ in debug_delete_ids)
        db_conn.execute(f"DELETE FROM debug_payload_logs WHERE id IN ({placeholders})", tuple(debug_delete_ids))

    if inbox_delete_ids:
        placeholders = ", ".join("?" for _ in inbox_delete_ids)
        db_conn.execute(f"DELETE FROM ingest_inbox WHERE id IN ({placeholders})", tuple(inbox_delete_ids))

    finished_at = format_iso(current_time or now_dt())
    db_conn.execute(
        """
        INSERT INTO cleanup_runs (
            started_at, finished_at, raw_events_deleted, grouped_events_deleted, debug_payload_logs_deleted, ingest_inbox_deleted
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            started_at,
            finished_at,
            len(raw_delete_ids),
            len(grouped_delete_ids),
            len(debug_delete_ids),
            len(inbox_delete_ids),
        ),
    )
    db_conn.commit()
    return RetentionCleanupSummary(
        raw_events_deleted=len(raw_delete_ids),
        grouped_events_deleted=len(grouped_delete_ids),
        debug_payload_logs_deleted=len(debug_delete_ids),
        ingest_inbox_deleted=len(inbox_delete_ids),
        started_at=started_at,
        finished_at=finished_at,
    )


class IngestWorkerLoop:
    def __init__(
        self,
        *,
        limit: int = 100,
        idle_sleep_seconds: float = 1.0,
        error_backoff_seconds: float = 5.0,
        processor=process_pending_ingest,
        cleanup_every_cycles: int | None = None,
        cleanup_func=cleanup_runtime_data,
    ) -> None:
        self.limit = limit
        self.idle_sleep_seconds = idle_sleep_seconds
        self.error_backoff_seconds = error_backoff_seconds
        self.processor = processor
        self.cleanup_every_cycles = cleanup_every_cycles if cleanup_every_cycles and cleanup_every_cycles > 0 else None
        self.cleanup_func = cleanup_func

    def run_cycle(self) -> IngestWorkerCycleResult:
        try:
            result = self.processor(limit=self.limit)
        except Exception as exc:
            return IngestWorkerCycleResult(
                processed_batches=0,
                failed_batches=0,
                processed_items=0,
                sleep_seconds=self.error_backoff_seconds,
                had_error=True,
                error_message=str(exc),
            )

        processed_batches = int(result["processed_batches"])
        failed_batches = int(result["failed_batches"])
        processed_items = int(result["processed_items"])
        should_idle = processed_batches == 0 and failed_batches == 0 and processed_items == 0
        return IngestWorkerCycleResult(
            processed_batches=processed_batches,
            failed_batches=failed_batches,
            processed_items=processed_items,
            sleep_seconds=self.idle_sleep_seconds if should_idle else 0.0,
            had_error=False,
        )

    def run_forever(self, *, max_cycles: int | None = None, sleep_func=sleep) -> IngestWorkerRunSummary:
        cycles = 0
        total_processed_batches = 0
        total_failed_batches = 0
        total_processed_items = 0

        while True:
            cycle = self.run_cycle()
            cycles += 1
            total_processed_batches += cycle.processed_batches
            total_failed_batches += cycle.failed_batches
            total_processed_items += cycle.processed_items

            if self.cleanup_every_cycles and cycles % self.cleanup_every_cycles == 0:
                self.cleanup_func()

            if max_cycles is not None and cycles >= max_cycles:
                break

            if cycle.sleep_seconds > 0:
                sleep_func(cycle.sleep_seconds)

        return IngestWorkerRunSummary(
            cycles=cycles,
            processed_batches=total_processed_batches,
            failed_batches=total_failed_batches,
            processed_items=total_processed_items,
        )


@click.command("process-ingest")
@click.option("--limit", default=100, show_default=True, type=int)
@with_appcontext
def process_ingest_command(limit: int) -> None:
    result = process_pending_ingest(limit=limit)
    click.echo(
        f"processed_batches={result['processed_batches']} failed_batches={result['failed_batches']} processed_items={result['processed_items']}"
    )


@click.command("run-ingest-worker")
@click.option("--limit", default=100, show_default=True, type=int)
@click.option("--max-cycles", default=None, type=int)
@click.option("--idle-sleep", default=1.0, show_default=True, type=float)
@click.option("--error-backoff", default=5.0, show_default=True, type=float)
@click.option("--cleanup-every-cycles", default=0, show_default=True, type=int)
@with_appcontext
def run_ingest_worker_command(
    limit: int,
    max_cycles: int | None,
    idle_sleep: float,
    error_backoff: float,
    cleanup_every_cycles: int,
) -> None:
    worker = IngestWorkerLoop(
        limit=limit,
        idle_sleep_seconds=idle_sleep,
        error_backoff_seconds=error_backoff,
        cleanup_every_cycles=cleanup_every_cycles,
    )
    summary = worker.run_forever(max_cycles=max_cycles)
    click.echo(
        f"cycles={summary.cycles} processed_batches={summary.processed_batches} "
        f"failed_batches={summary.failed_batches} processed_items={summary.processed_items}"
    )


@click.command("cleanup-runtime-data")
@with_appcontext
def cleanup_runtime_data_command() -> None:
    summary = cleanup_runtime_data()
    click.echo(
        "raw_events_deleted={0} grouped_events_deleted={1} debug_payload_logs_deleted={2} ingest_inbox_deleted={3}".format(
            summary.raw_events_deleted,
            summary.grouped_events_deleted,
            summary.debug_payload_logs_deleted,
            summary.ingest_inbox_deleted,
        )
    )


def init_app(app) -> None:
    app.cli.add_command(process_ingest_command)
    app.cli.add_command(run_ingest_worker_command)
    app.cli.add_command(cleanup_runtime_data_command)
