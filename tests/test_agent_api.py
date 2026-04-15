from __future__ import annotations

from app.db import get_db
from app.ingest_worker import process_pending_ingest


def agent_headers(agent_id: str = "agent_local", token: str = "dev-agent-token") -> dict[str, str]:
    return {
        "X-Agent-Id": agent_id,
        "X-Agent-Token": token,
    }


def sample_batch() -> dict:
    return {
        "agent_id": "agent_local",
        "boot_id": "boot_001",
        "seq_start": 10,
        "seq_end": 13,
        "sent_at": "2026-04-10T10:20:00.150+09:00",
        "items": [
            {
                "seq": 10,
                "payload_type": "agent_state",
                "occurred_at": "2026-04-10T10:20:00.100+09:00",
                "target_id": "agent_local",
                "payload": {
                    "heartbeat_time": "2026-04-10T10:20:00.100+09:00",
                    "outbox_queue_depth": 0,
                    "backend_connection_status": "connected",
                },
            },
            {
                "seq": 11,
                "payload_type": "host_snapshot",
                "occurred_at": "2026-04-10T10:20:00.100+09:00",
                "target_id": "agent_local:host",
                "payload": {
                    "hostname": "host-alpha",
                    "cpu_usage": 12.5,
                    "loadavg_1": 0.11,
                    "loadavg_5": 0.15,
                    "loadavg_15": 0.20,
                    "memory_total": 16777216,
                    "memory_available": 8388608,
                    "memory_used": 8388608,
                },
            },
            {
                "seq": 12,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T10:20:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 3.2,
                    "memory_rss": 10485760,
                },
            },
            {
                "seq": 13,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T10:21:10.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_stopped",
                    "message": "process not found",
                },
            },
        ],
    }


def overlapping_batch() -> dict:
    return {
        "agent_id": "agent_local",
        "boot_id": "boot_001",
        "seq_start": 12,
        "seq_end": 14,
        "sent_at": "2026-04-10T10:22:00.150+09:00",
        "items": [
            {
                "seq": 12,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T10:20:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 3.2,
                    "memory_rss": 10485760,
                },
            },
            {
                "seq": 13,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T10:21:10.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_stopped",
                    "message": "process not found",
                },
            },
            {
                "seq": 14,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T10:22:10.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_restarted",
                    "severity": "warning",
                    "message": "process restarted",
                },
            },
        ],
    }


def invalid_event_batch() -> dict:
    return {
        "agent_id": "agent_local",
        "boot_id": "boot_invalid",
        "seq_start": 21,
        "seq_end": 22,
        "sent_at": "2026-04-10T10:23:00.150+09:00",
        "items": [
            {
                "seq": 21,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T10:23:00.100+09:00",
                "target_id": "broken_process",
                "payload": {
                    "pid": 2222,
                    "state": "running",
                    "cpu_usage": 1.1,
                    "memory_rss": 2048,
                },
            },
            {
                "seq": 22,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T10:23:01.100+09:00",
                "target_id": "broken_process",
                "payload": {
                    "event_type": "unknown_event",
                    "message": "bad event",
                },
            },
        ],
    }


def test_ingest_requires_agent_credentials(seeded_client) -> None:
    response = seeded_client.post("/api/agents/ingest", json=sample_batch())

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_ingest_rejects_invalid_token(seeded_client) -> None:
    response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(token="wrong-token"),
        json=sample_batch(),
    )

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_ingest_persists_inbox_and_returns_ack(seeded_app, seeded_client) -> None:
    response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload["ack_seq"] == 13
    assert payload["accepted_count"] == 4
    assert payload["duplicate"] is False

    with seeded_app.app_context():
        db_conn = get_db()
        row = db_conn.execute(
            "SELECT agent_id, boot_id, seq_start, seq_end, status FROM ingest_inbox ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert row["agent_id"] == "agent_local"
    assert row["boot_id"] == "boot_001"
    assert row["seq_start"] == 10
    assert row["seq_end"] == 13
    assert row["status"] == "pending"


def test_ingest_duplicate_batch_returns_same_ack_without_new_inbox_row(seeded_app, seeded_client) -> None:
    first_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )
    second_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert second_response.get_json()["ack_seq"] == 13
    assert second_response.get_json()["accepted_count"] == 4
    assert second_response.get_json()["duplicate"] is True

    with seeded_app.app_context():
        db_conn = get_db()
        row = db_conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM ingest_inbox
            WHERE agent_id = ? AND boot_id = ? AND seq_start = ? AND seq_end = ?
            """,
            ("agent_local", "boot_001", 10, 13),
        ).fetchone()

    assert row["count"] == 1


def test_process_pending_ingest_updates_states_and_events(seeded_app, seeded_client) -> None:
    ingest_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )
    assert ingest_response.status_code == 202

    with seeded_app.app_context():
        result = process_pending_ingest(limit=10)
        db_conn = get_db()
        inbox_row = db_conn.execute(
            "SELECT status, processed_at FROM ingest_inbox ORDER BY id DESC LIMIT 1"
        ).fetchone()
        state_rows = db_conn.execute(
            "SELECT target_id, monitored_object_id, state_type, status FROM latest_states ORDER BY id"
        ).fetchall()
        event_rows = db_conn.execute(
            "SELECT target_id, monitored_object_id, event_type, severity FROM raw_events ORDER BY id"
        ).fetchall()

    assert result == {
        "processed_batches": 1,
        "failed_batches": 0,
        "processed_items": 4,
    }
    assert inbox_row["status"] == "processed"
    assert inbox_row["processed_at"] is not None
    assert [(row["target_id"], row["monitored_object_id"], row["state_type"], row["status"]) for row in state_rows] == [
        ("agent_local", 1303, "agent", "up"),
        ("agent_local:host", 1304, "host", "up"),
        ("app_main", 1302, "process", "down"),
    ]
    assert [(row["target_id"], row["monitored_object_id"], row["event_type"], row["severity"]) for row in event_rows] == [
        ("app_main", 1302, "process_stopped", "warning"),
    ]


def test_duplicate_batch_is_processed_only_once(seeded_app, seeded_client) -> None:
    first_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )
    second_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )
    assert first_response.status_code == 202
    assert second_response.status_code == 202

    with seeded_app.app_context():
        result = process_pending_ingest(limit=10)
        db_conn = get_db()
        inbox_count = db_conn.execute("SELECT COUNT(*) AS count FROM ingest_inbox").fetchone()["count"]
        event_count = db_conn.execute("SELECT COUNT(*) AS count FROM raw_events").fetchone()["count"]

    assert result == {
        "processed_batches": 1,
        "failed_batches": 0,
        "processed_items": 4,
    }
    assert inbox_count == 1
    assert event_count == 1


def test_overlapping_batch_processes_only_new_items(seeded_app, seeded_client) -> None:
    first_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )
    second_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=overlapping_batch(),
    )
    assert first_response.status_code == 202
    assert second_response.status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        event_rows = db_conn.execute(
            "SELECT event_type, message FROM raw_events ORDER BY id"
        ).fetchall()
        latest_process = db_conn.execute(
            "SELECT status, severity, state_json FROM latest_states WHERE target_id = ? AND state_type = 'process'",
            ("app_main",),
        ).fetchone()
        receipt_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM processed_item_receipts WHERE agent_id = ? AND boot_id = ?",
            ("agent_local", "boot_001"),
        ).fetchone()["count"]

    assert first_result == {
        "processed_batches": 1,
        "failed_batches": 0,
        "processed_items": 4,
    }
    assert second_result == {
        "processed_batches": 1,
        "failed_batches": 0,
        "processed_items": 1,
    }
    assert [(row["event_type"], row["message"]) for row in event_rows] == [
        ("process_stopped", "process not found"),
        ("process_restarted", "process restarted"),
    ]
    assert latest_process["status"] == "warning"
    assert latest_process["severity"] == "warning"
    assert "process_restarted" in latest_process["state_json"]
    assert receipt_count == 5


def test_failed_batch_rolls_back_all_item_side_effects(seeded_app, seeded_client) -> None:
    response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=invalid_event_batch(),
    )
    assert response.status_code == 202

    with seeded_app.app_context():
        result = process_pending_ingest(limit=1)
        db_conn = get_db()
        inbox_row = db_conn.execute(
            "SELECT status, error_message FROM ingest_inbox WHERE boot_id = ? ORDER BY id DESC LIMIT 1",
            ("boot_invalid",),
        ).fetchone()
        latest_state = db_conn.execute(
            "SELECT COUNT(*) AS count FROM latest_states WHERE target_id = ?",
            ("broken_process",),
        ).fetchone()["count"]
        raw_event_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM raw_events WHERE target_id = ?",
            ("broken_process",),
        ).fetchone()["count"]
        receipt_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM processed_item_receipts WHERE boot_id = ?",
            ("boot_invalid",),
        ).fetchone()["count"]

    assert result == {
        "processed_batches": 0,
        "failed_batches": 1,
        "processed_items": 0,
    }
    assert inbox_row["status"] == "failed"
    assert "unsupported event_type" in inbox_row["error_message"]
    assert latest_state == 0
    assert raw_event_count == 0
    assert receipt_count == 0


def test_unmapped_target_keeps_monitored_object_id_null(seeded_app, seeded_client) -> None:
    payload = {
        "agent_id": "agent_local",
        "boot_id": "boot_unmapped",
        "seq_start": 31,
        "seq_end": 31,
        "sent_at": "2026-04-10T10:30:00.150+09:00",
        "items": [
            {
                "seq": 31,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T10:30:00.100+09:00",
                "target_id": "unknown_process_target",
                "payload": {
                    "pid": 4321,
                    "state": "running",
                    "cpu_usage": 2.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }

    response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=payload,
    )
    assert response.status_code == 202

    with seeded_app.app_context():
        result = process_pending_ingest(limit=10)
        db_conn = get_db()
        state_row = db_conn.execute(
            """
            SELECT target_id, monitored_object_id, status
            FROM latest_states
            WHERE target_id = ?
            """,
            ("unknown_process_target",),
        ).fetchone()

    assert result == {
        "processed_batches": 1,
        "failed_batches": 0,
        "processed_items": 1,
    }
    assert state_row["target_id"] == "unknown_process_target"
    assert state_row["monitored_object_id"] is None
    assert state_row["status"] == "up"


def test_alert_instance_opens_and_repeats_for_abnormal_process_state(seeded_app, seeded_client) -> None:
    warning_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_alerts",
        "seq_start": 41,
        "seq_end": 41,
        "sent_at": "2026-04-10T10:40:00.150+09:00",
        "items": [
            {
                "seq": 41,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T10:40:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_restarted",
                    "severity": "warning",
                    "message": "process restarted",
                },
            }
        ],
    }

    first_response = seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=warning_batch)
    assert first_response.status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=10)
        db_conn = get_db()
        first_alert = db_conn.execute(
            """
            SELECT monitored_object_id, alert_code, severity, status, repeat_count, latest_message
            FROM alert_instances
            WHERE monitored_object_id = 1302
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert first_result == {
        "processed_batches": 1,
        "failed_batches": 0,
        "processed_items": 1,
    }
    assert first_alert["alert_code"] == "process.warning"
    assert first_alert["severity"] == "warning"
    assert first_alert["status"] == "open"
    assert first_alert["repeat_count"] == 1
    assert first_alert["latest_message"] == "process restarted"

    repeat_batch = {
        **warning_batch,
        "seq_start": 42,
        "seq_end": 42,
        "items": [
            {
                **warning_batch["items"][0],
                "seq": 42,
                "occurred_at": "2026-04-10T10:41:00.100+09:00",
            }
        ],
    }
    second_response = seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=repeat_batch)
    assert second_response.status_code == 202

    with seeded_app.app_context():
        second_result = process_pending_ingest(limit=10)
        db_conn = get_db()
        second_alert = db_conn.execute(
            """
            SELECT alert_code, status, repeat_count
            FROM alert_instances
            WHERE monitored_object_id = 1302 AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        open_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM alert_instances WHERE monitored_object_id = 1302 AND status = 'open'"
        ).fetchone()["count"]

    assert second_result == {
        "processed_batches": 1,
        "failed_batches": 0,
        "processed_items": 1,
    }
    assert second_alert["alert_code"] == "process.warning"
    assert second_alert["repeat_count"] == 2
    assert open_count == 1


def test_alert_instance_resolves_when_process_recovers(seeded_app, seeded_client) -> None:
    down_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_alert_resolve",
        "seq_start": 51,
        "seq_end": 51,
        "sent_at": "2026-04-10T10:50:00.150+09:00",
        "items": [
            {
                "seq": 51,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T10:50:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_stopped",
                    "severity": "warning",
                    "message": "process not found",
                },
            }
        ],
    }

    up_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_alert_resolve",
        "seq_start": 52,
        "seq_end": 52,
        "sent_at": "2026-04-10T10:51:00.150+09:00",
        "items": [
            {
                "seq": 52,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T10:51:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_started",
                    "severity": "info",
                    "message": "process started",
                },
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=down_batch).status_code == 202
    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=10)
        open_count = get_db().execute(
            "SELECT COUNT(*) AS count FROM alert_instances WHERE monitored_object_id = 1302 AND status = 'open'"
        ).fetchone()["count"]
    assert first_result["processed_items"] == 1
    assert open_count == 1

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=up_batch).status_code == 202
    with seeded_app.app_context():
        second_result = process_pending_ingest(limit=10)
        db_conn = get_db()
        open_count_after = db_conn.execute(
            "SELECT COUNT(*) AS count FROM alert_instances WHERE monitored_object_id = 1302 AND status = 'open'"
        ).fetchone()["count"]
        resolved_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM alert_instances WHERE monitored_object_id = 1302 AND status = 'resolved'"
        ).fetchone()["count"]

    assert second_result["processed_items"] == 1
    assert open_count_after == 0
    assert resolved_count == 1


def test_process_ingest_cli_command(seeded_client, seeded_runner) -> None:
    ingest_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )
    assert ingest_response.status_code == 202

    result = seeded_runner.invoke(args=["process-ingest", "--limit", "10"])

    assert result.exit_code == 0
    assert "processed_batches=1" in result.output
    assert "processed_items=4" in result.output


def test_run_ingest_worker_cli_command(seeded_client, seeded_runner) -> None:
    ingest_response = seeded_client.post(
        "/api/agents/ingest",
        headers=agent_headers(),
        json=sample_batch(),
    )
    assert ingest_response.status_code == 202

    result = seeded_runner.invoke(
        args=["run-ingest-worker", "--limit", "10", "--max-cycles", "1", "--idle-sleep", "0.1"]
    )

    assert result.exit_code == 0
    assert "cycles=1" in result.output
    assert "processed_batches=1" in result.output
    assert "processed_items=4" in result.output
