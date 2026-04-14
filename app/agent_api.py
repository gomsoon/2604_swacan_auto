from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from flask import Blueprint, current_app, request

from .auth import error_response
from .db import get_db

bp = Blueprint("agent_api", __name__, url_prefix="/api/agents")

SUPPORTED_PAYLOAD_TYPES = {"agent_state", "host_snapshot", "process_snapshot", "process_event", "agent_event"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def log_debug_payload(
    *,
    channel: str,
    direction: str,
    endpoint_or_topic: str,
    payload_json: str,
    occurred_at: str,
    agent_id: str | None = None,
    status_code: int | None = None,
) -> None:
    if not current_app.config.get("DEBUG_PAYLOAD_LOGGING", False):
        return

    get_db().execute(
        """
        INSERT INTO debug_payload_logs (
            channel, direction, endpoint_or_topic, agent_id, user_id, session_id,
            trace_id, status_code, payload_json, payload_size, is_redacted, occurred_at
        ) VALUES (?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, 1, ?)
        """,
        (
            channel,
            direction,
            endpoint_or_topic,
            agent_id,
            status_code,
            payload_json,
            len(payload_json.encode("utf-8")),
            occurred_at,
        ),
    )


def validate_batch_payload(header_agent_id: str, payload: dict[str, Any]) -> str | None:
    required = {"agent_id", "boot_id", "seq_start", "seq_end", "items"}
    missing = required - payload.keys()
    if missing:
        return f"payload is missing required fields: {', '.join(sorted(missing))}"

    if payload["agent_id"] != header_agent_id:
        return "header agent id and payload agent id must match"

    if not isinstance(payload["seq_start"], int) or not isinstance(payload["seq_end"], int):
        return "seq_start and seq_end must be integers"

    items = payload.get("items")
    if not isinstance(items, list):
        return "items must be a list"

    for item in items:
        if not isinstance(item, dict):
            return "each item must be an object"
        item_missing = {"seq", "payload_type", "occurred_at", "target_id", "payload"} - item.keys()
        if item_missing:
            return f"item is missing required fields: {', '.join(sorted(item_missing))}"
        if not isinstance(item["seq"], int):
            return "item seq must be an integer"
        if item["payload_type"] not in SUPPORTED_PAYLOAD_TYPES:
            return "unsupported payload_type"
        if not isinstance(item["payload"], dict):
            return "item payload must be an object"

    return None


@bp.post("/ingest")
def ingest_batch():
    header_agent_id = request.headers.get("X-Agent-Id")
    header_token = request.headers.get("X-Agent-Token")

    if not header_agent_id or not header_token:
        return error_response("unauthorized", "agent credentials are required", 401)

    expected_token = current_app.config.get("AGENT_TOKENS", {}).get(header_agent_id)
    if expected_token is None or expected_token != header_token:
        return error_response("unauthorized", "invalid agent credentials", 401)

    payload = request.get_json(silent=True) or {}
    validation_error = validate_batch_payload(header_agent_id, payload)
    if validation_error:
        return error_response("validation_error", validation_error, 400)

    received_at = now_iso()
    payload_json = json.dumps(payload, ensure_ascii=False)

    db_conn = get_db()
    is_duplicate = False
    try:
        db_conn.execute(
            """
            INSERT INTO ingest_inbox (
                agent_id, boot_id, seq_start, seq_end, received_at, payload_json, status, processed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', NULL, NULL)
            """,
            (
                payload["agent_id"],
                payload["boot_id"],
                payload["seq_start"],
                payload["seq_end"],
                received_at,
                payload_json,
            ),
        )
    except sqlite3.IntegrityError:
        existing = db_conn.execute(
            """
            SELECT id
            FROM ingest_inbox
            WHERE agent_id = ? AND boot_id = ? AND seq_start = ? AND seq_end = ?
            """,
            (
                payload["agent_id"],
                payload["boot_id"],
                payload["seq_start"],
                payload["seq_end"],
            ),
        ).fetchone()
        if existing is None:
            raise
        is_duplicate = True

    log_debug_payload(
        channel="agent_backend",
        direction="request",
        endpoint_or_topic="/api/agents/ingest",
        payload_json=payload_json,
        occurred_at=received_at,
        agent_id=payload["agent_id"],
    )

    response = {
        "ack_seq": payload["seq_end"],
        "accepted_count": len(payload["items"]),
        "server_time": received_at,
        "duplicate": is_duplicate,
    }
    response_json = json.dumps(response, ensure_ascii=False)
    log_debug_payload(
        channel="agent_backend",
        direction="response",
        endpoint_or_topic="/api/agents/ingest",
        payload_json=response_json,
        occurred_at=received_at,
        agent_id=payload["agent_id"],
        status_code=202,
    )

    db_conn.commit()
    return response, 202
