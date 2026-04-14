from __future__ import annotations

import json
from datetime import datetime

from app.db import get_db
from app.ingest_worker import cleanup_runtime_data


def seed_retention_rows(app) -> None:
    with app.app_context():
        db_conn = get_db()

        db_conn.execute(
            """
            INSERT INTO raw_events (
                id, agent_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                201,
                "agent_local",
                "old_target",
                "process_stopped",
                "warning",
                "old event",
                json.dumps({"source": "old"}),
                "2026-04-01T09:00:00.000+09:00",
                "2026-04-01T09:00:00.100+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO raw_events (
                id, agent_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                202,
                "agent_local",
                "fresh_target",
                "process_started",
                "normal",
                "fresh event",
                json.dumps({"source": "fresh"}),
                "2026-04-13T09:00:00.000+09:00",
                "2026-04-13T09:00:00.100+09:00",
            ),
        )

        db_conn.execute(
            """
            INSERT INTO debug_payload_logs (
                id, channel, direction, endpoint_or_topic, agent_id, user_id, session_id,
                trace_id, status_code, payload_json, payload_size, is_redacted, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                301,
                "agent_backend",
                "request",
                "/api/agents/ingest",
                "agent_local",
                None,
                None,
                "old-trace",
                202,
                json.dumps({"old": True}),
                len(json.dumps({"old": True}).encode("utf-8")),
                1,
                "2026-04-13T07:00:00.000+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO debug_payload_logs (
                id, channel, direction, endpoint_or_topic, agent_id, user_id, session_id,
                trace_id, status_code, payload_json, payload_size, is_redacted, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                302,
                "agent_backend",
                "response",
                "/api/agents/ingest",
                "agent_local",
                None,
                None,
                "fresh-trace",
                202,
                json.dumps({"fresh": True}),
                len(json.dumps({"fresh": True}).encode("utf-8")),
                1,
                "2026-04-14T06:30:00.000+09:00",
            ),
        )

        db_conn.execute(
            """
            INSERT INTO ingest_inbox (
                id, agent_id, boot_id, seq_start, seq_end, received_at, payload_json, status, processed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                401,
                "agent_local",
                "boot_old",
                1,
                2,
                "2026-04-01T08:00:00.000+09:00",
                json.dumps({"items": [{"seq": 1}, {"seq": 2}]}),
                "processed",
                "2026-04-01T08:01:00.000+09:00",
                None,
            ),
        )
        db_conn.execute(
            """
            INSERT INTO processed_item_receipts (
                id, agent_id, boot_id, item_seq, payload_type, target_id, inbox_id, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                501,
                "agent_local",
                "boot_old",
                1,
                "process_snapshot",
                "old_target",
                401,
                "2026-04-01T08:01:00.000+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO ingest_inbox (
                id, agent_id, boot_id, seq_start, seq_end, received_at, payload_json, status, processed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                402,
                "agent_local",
                "boot_pending_keep",
                3,
                3,
                "2026-04-01T08:00:00.000+09:00",
                json.dumps({"items": [{"seq": 3}]}),
                "pending",
                None,
                None,
            ),
        )
        db_conn.execute(
            """
            INSERT INTO ingest_inbox (
                id, agent_id, boot_id, seq_start, seq_end, received_at, payload_json, status, processed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                403,
                "agent_local",
                "boot_recent",
                4,
                4,
                "2026-04-13T08:00:00.000+09:00",
                json.dumps({"items": [{"seq": 4}]}),
                "failed",
                "2026-04-13T08:01:00.000+09:00",
                "recent failure",
            ),
        )
        db_conn.commit()


def test_cleanup_runtime_data_removes_only_expired_rows(app) -> None:
    seed_retention_rows(app)

    with app.app_context():
        summary = cleanup_runtime_data(
            current_time=datetime.fromisoformat("2026-04-14T08:00:00.000+09:00"),
            raw_event_retention_days=7,
            debug_payload_retention_hours=24,
            ingest_inbox_retention_days=7,
        )
        assert summary.raw_events_deleted == 1
        assert summary.debug_payload_logs_deleted == 1
        assert summary.ingest_inbox_deleted == 1

        db_conn = get_db()
        raw_ids = {row["id"] for row in db_conn.execute("SELECT id FROM raw_events").fetchall()}
        debug_ids = {row["id"] for row in db_conn.execute("SELECT id FROM debug_payload_logs").fetchall()}
        inbox_ids = {row["id"] for row in db_conn.execute("SELECT id FROM ingest_inbox").fetchall()}
        receipt_ids = {
            row["id"] for row in db_conn.execute("SELECT id FROM processed_item_receipts").fetchall()
        }
        cleanup_runs = db_conn.execute(
            """
            SELECT raw_events_deleted, debug_payload_logs_deleted, ingest_inbox_deleted
            FROM cleanup_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        assert raw_ids == {202}
        assert debug_ids == {302}
        assert inbox_ids == {402, 403}
        assert receipt_ids == set()
        assert cleanup_runs is not None
        assert cleanup_runs["raw_events_deleted"] == 1
        assert cleanup_runs["debug_payload_logs_deleted"] == 1
        assert cleanup_runs["ingest_inbox_deleted"] == 1


def test_cleanup_runtime_data_command_uses_app_config(app, runner) -> None:
    app.config.update(
        CURRENT_TIME_PROVIDER=lambda: datetime.fromisoformat("2026-04-14T08:00:00.000+09:00"),
        RAW_EVENT_RETENTION_DAYS=7,
        DEBUG_PAYLOAD_RETENTION_HOURS=24,
        INGEST_INBOX_RETENTION_DAYS=7,
    )
    seed_retention_rows(app)

    result = runner.invoke(args=["cleanup-runtime-data"])

    assert result.exit_code == 0
    assert "raw_events_deleted=1" in result.output
    assert "debug_payload_logs_deleted=1" in result.output
    assert "ingest_inbox_deleted=1" in result.output
