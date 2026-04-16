from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import sleep

import click
from flask import current_app
from flask.cli import with_appcontext

from .alert_history import record_alert_history
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
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


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


def resolve_alert_rows(*, rows, occurred_at: str, received_at: str, note: str, payload: dict) -> None:
    db_conn = get_db()
    for row in rows:
        db_conn.execute(
            """
            UPDATE alert_instances
            SET status = 'resolved',
                resolved_at = COALESCE(resolved_at, ?),
                resolved_by_user_id = NULL,
                status_updated_at = ?,
                status_updated_by_user_id = NULL,
                updated_at = ?,
                last_occurred_at = ?
            WHERE id = ?
            """,
            (received_at, received_at, received_at, occurred_at, row["id"]),
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
            payload=payload,
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
            SELECT id, status, acknowledged_at
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
        )
        return

    normalized_severity = normalize_alert_severity(severity, status)
    latest_message = alert_message_for_state(state_type=state_type, status=status, state=state)
    metadata_json = json.dumps(state, ensure_ascii=False)

    rows_to_resolve = db_conn.execute(
        """
        SELECT id, status, acknowledged_at
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


def threshold_level(metric_value: float | None, rule) -> str | None:
    if metric_value is None:
        return None

    comparison = rule["comparison"]
    warning_threshold = rule["warning_threshold"]
    critical_threshold = rule["critical_threshold"]

    def matches(value: float, threshold: float | None) -> bool:
        if threshold is None:
            return False
        return value >= threshold if comparison == "gte" else value <= threshold

    if matches(metric_value, critical_threshold):
        return "critical"
    if matches(metric_value, warning_threshold):
        return "warning"
    return None


def threshold_message(rule, metric_value: float, level: str) -> str:
    threshold = rule["critical_threshold"] if level == "critical" else rule["warning_threshold"]
    operator = ">=" if rule["comparison"] == "gte" else "<="
    return f"{rule['metric_key']}={metric_value:.3f} {operator} {threshold:.3f}"


def sync_threshold_alerts(
    *,
    monitored_object_id: int | None,
    state_type: str,
    state: dict,
    occurred_at: str,
    received_at: str,
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
        SELECT id, scope_type, object_type, monitored_object_id, state_type, metric_key, comparison,
               warning_threshold, critical_threshold, is_enabled, description
        FROM alert_rules
        WHERE is_enabled = 1
          AND state_type = ?
          AND (
                (scope_type = 'monitored_object' AND monitored_object_id = ?)
             OR (scope_type = 'object_type' AND object_type = ?)
          )
        ORDER BY scope_type DESC, id ASC
        """,
        (state_type, monitored_object_id, object_row["object_type"]),
    ).fetchall()

    for rule in rules:
        metric_value = numeric_metric_value(state, rule["metric_key"])
        level = threshold_level(metric_value, rule)
        alert_code = f"rule.{rule['id']}"

        if level is None:
            rows_to_resolve = db_conn.execute(
                """
                SELECT id, status, acknowledged_at
                FROM alert_instances
                WHERE monitored_object_id = ?
                  AND alert_code = ?
                  AND status != 'resolved'
                """,
                (monitored_object_id, alert_code),
            ).fetchall()
            resolve_alert_rows(
                rows=rows_to_resolve,
                occurred_at=occurred_at,
                received_at=received_at,
                note="threshold no longer matched",
                payload={"source": "worker", "reason": "threshold_cleared", "rule_id": rule["id"]},
            )
            continue

        latest_message = threshold_message(rule, metric_value, level)
        metadata_json = json.dumps(
            {
                "rule_id": rule["id"],
                "metric_key": rule["metric_key"],
                "metric_value": metric_value,
                "comparison": rule["comparison"],
                "warning_threshold": rule["warning_threshold"],
                "critical_threshold": rule["critical_threshold"],
                "scope_type": rule["scope_type"],
            },
            ensure_ascii=False,
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
                source_rule_id=rule["id"],
                severity=level,
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
                rule["id"],
                level,
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
