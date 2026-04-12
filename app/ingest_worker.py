from __future__ import annotations

import json
from datetime import datetime

import click
from flask.cli import with_appcontext

from .db import get_db

VALID_EVENT_TYPES = {
    "process_started",
    "process_stopped",
    "process_restarted",
    "agent_heartbeat_lost",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


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


def upsert_latest_state(*, target_id: str, state_type: str, status: str, severity: str | None, state: dict, occurred_at: str, received_at: str) -> None:
    db_conn = get_db()
    existing = db_conn.execute(
        "SELECT id FROM latest_states WHERE target_id = ? AND state_type = ?",
        (target_id, state_type),
    ).fetchone()
    payload_json = json.dumps(state, ensure_ascii=False)
    view_node_id = resolve_view_node_id(target_id)

    if existing is None:
        next_id = db_conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM latest_states").fetchone()["next_id"]
        db_conn.execute(
            """
            INSERT INTO latest_states (
                id, view_node_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_id,
                view_node_id,
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
        return

    db_conn.execute(
        """
        UPDATE latest_states
        SET view_node_id = ?, status = ?, severity = ?, state_json = ?, occurred_at = ?, received_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            view_node_id,
            status,
            severity,
            payload_json,
            occurred_at,
            received_at,
            received_at,
            existing["id"],
        ),
    )


def insert_raw_event(*, agent_id: str, target_id: str, event_type: str, severity: str, message: str | None, event_payload: dict, occurred_at: str, received_at: str) -> None:
    get_db().execute(
        """
        INSERT INTO raw_events (
            agent_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            target_id,
            event_type,
            severity,
            message,
            json.dumps(event_payload, ensure_ascii=False),
            occurred_at,
            received_at,
        ),
    )


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
        SELECT id, agent_id, received_at, payload_json
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
            for item in payload["items"]:
                process_item(row["agent_id"], item, row["received_at"])
                processed_items += 1
            db_conn.execute(
                "UPDATE ingest_inbox SET status = 'processed', processed_at = ?, error_message = NULL WHERE id = ?",
                (now_iso(), row["id"]),
            )
            db_conn.commit()
            processed_batches += 1
        except Exception as exc:
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


@click.command("process-ingest")
@click.option("--limit", default=100, show_default=True, type=int)
@with_appcontext
def process_ingest_command(limit: int) -> None:
    result = process_pending_ingest(limit=limit)
    click.echo(
        f"processed_batches={result['processed_batches']} failed_batches={result['failed_batches']} processed_items={result['processed_items']}"
    )


def init_app(app) -> None:
    app.cli.add_command(process_ingest_command)
