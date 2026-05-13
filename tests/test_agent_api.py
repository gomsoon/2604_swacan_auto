from __future__ import annotations

from datetime import datetime, timedelta
import json

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
        history_rows = db_conn.execute(
            """
            SELECT history.action_type, alerts.alert_code
            FROM alert_history AS history
            JOIN alert_instances AS alerts ON alerts.id = history.alert_instance_id
            WHERE alerts.monitored_object_id = 1302
            ORDER BY history.id
            """
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
    assert [(row["action_type"], row["alert_code"]) for row in history_rows] == [
        ("created", "process.down"),
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
        history_rows = db_conn.execute(
            """
            SELECT history.action_type, history.note, alerts.alert_code
            FROM alert_history AS history
            JOIN alert_instances AS alerts ON alerts.id = history.alert_instance_id
            WHERE alerts.monitored_object_id = 1302
            ORDER BY history.id
            """
        ).fetchall()

    assert second_result["processed_items"] == 1
    assert open_count_after == 0
    assert resolved_count == 1
    assert [(row["action_type"], row["note"], row["alert_code"]) for row in history_rows] == [
        ("created", None, "process.down"),
        ("resolved", "state normalized", "process.down"),
    ]


def test_alert_instance_preserves_manual_in_progress_status_until_resolution(seeded_app, seeded_client) -> None:
    warning_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_manual_state",
        "seq_start": 53,
        "seq_end": 53,
        "sent_at": "2026-04-10T10:52:00.150+09:00",
        "items": [
            {
                "seq": 53,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T10:52:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_restarted",
                    "severity": "warning",
                    "message": "process restarted",
                },
            }
        ],
    }
    repeat_batch = {
        **warning_batch,
        "seq_start": 54,
        "seq_end": 54,
        "items": [
            {
                **warning_batch["items"][0],
                "seq": 54,
                "occurred_at": "2026-04-10T10:52:05.100+09:00",
            }
        ],
    }
    recover_batch = {
        **warning_batch,
        "seq_start": 55,
        "seq_end": 55,
        "items": [
            {
                "seq": 55,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T10:52:10.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 1.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=warning_batch).status_code == 202
    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=10)
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE alert_instances
            SET status = 'in_progress', status_updated_at = ?, status_updated_by_user_id = ?, status_note = ?, updated_at = ?
            WHERE monitored_object_id = ? AND alert_code = 'process.warning'
            """,
            (
                "2026-04-10T10:52:02.000+09:00",
                1,
                "investigating",
                "2026-04-10T10:52:02.000+09:00",
                1302,
            ),
        )
        db_conn.commit()
    assert first_result["processed_items"] == 1

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=repeat_batch).status_code == 202
    with seeded_app.app_context():
        second_result = process_pending_ingest(limit=10)
        db_conn = get_db()
        repeated_alert = db_conn.execute(
            """
            SELECT status, repeat_count, status_note
            FROM alert_instances
            WHERE monitored_object_id = ? AND alert_code = 'process.warning'
            ORDER BY id DESC
            LIMIT 1
            """,
            (1302,),
        ).fetchone()
    assert second_result["processed_items"] == 1
    assert repeated_alert["status"] == "in_progress"
    assert repeated_alert["repeat_count"] == 2
    assert repeated_alert["status_note"] == "investigating"

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=recover_batch).status_code == 202
    with seeded_app.app_context():
        third_result = process_pending_ingest(limit=10)
        db_conn = get_db()
        resolved_alert = db_conn.execute(
            """
            SELECT status, resolved_at
            FROM alert_instances
            WHERE monitored_object_id = ? AND alert_code = 'process.warning'
            ORDER BY id DESC
            LIMIT 1
            """,
            (1302,),
        ).fetchone()
    assert third_result["processed_items"] == 1
    assert resolved_alert["status"] == "resolved"
    assert resolved_alert["resolved_at"] is not None


def test_process_threshold_alert_opens_on_exact_warning_and_critical_boundaries(seeded_app, seeded_client) -> None:
    warning_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_threshold_process",
        "seq_start": 61,
        "seq_end": 61,
        "sent_at": "2026-04-10T11:00:00.150+09:00",
        "items": [
            {
                "seq": 61,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T11:00:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 80.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }
    critical_batch = {
        **warning_batch,
        "seq_start": 62,
        "seq_end": 62,
        "items": [
            {
                **warning_batch["items"][0],
                "seq": 62,
                "occurred_at": "2026-04-10T11:00:05.100+09:00",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 95.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=warning_batch).status_code == 202
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=critical_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        rule_alert = db_conn.execute(
            """
            SELECT alert_code, severity, status, repeat_count, latest_message
            FROM alert_instances
            WHERE monitored_object_id = 1302 AND alert_code = 'rule.1501'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert first_result["processed_items"] == 1
    assert second_result["processed_items"] == 1
    assert rule_alert["alert_code"] == "rule.1501"
    assert rule_alert["severity"] == "critical"
    assert rule_alert["status"] == "open"
    assert rule_alert["repeat_count"] == 2
    assert "95.000" in rule_alert["latest_message"]


def test_host_threshold_alert_handles_exact_boundary_and_resolution(seeded_app, seeded_client) -> None:
    warning_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_threshold_host",
        "seq_start": 71,
        "seq_end": 71,
        "sent_at": "2026-04-10T11:05:00.150+09:00",
        "items": [
            {
                "seq": 71,
                "payload_type": "host_snapshot",
                "occurred_at": "2026-04-10T11:05:00.100+09:00",
                "target_id": "agent_local:host",
                "payload": {
                    "hostname": "host-alpha",
                    "cpu_usage": 10.0,
                    "loadavg_1": 0.1,
                    "loadavg_5": 0.1,
                    "loadavg_15": 0.1,
                    "memory_total": 100.0,
                    "memory_available": 15.0,
                    "memory_used": 85.0,
                },
            }
        ],
    }
    recover_batch = {
        **warning_batch,
        "seq_start": 72,
        "seq_end": 72,
        "items": [
            {
                **warning_batch["items"][0],
                "seq": 72,
                "occurred_at": "2026-04-10T11:05:05.100+09:00",
                "payload": {
                    "hostname": "host-alpha",
                    "cpu_usage": 10.0,
                    "loadavg_1": 0.1,
                    "loadavg_5": 0.1,
                    "loadavg_15": 0.1,
                    "memory_total": 100.0,
                    "memory_available": 16.0,
                    "memory_used": 84.0,
                },
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=warning_batch).status_code == 202
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=recover_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        open_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM alert_instances WHERE monitored_object_id = 1304 AND alert_code = 'rule.1503' AND status = 'open'"
        ).fetchone()["count"]
        resolved_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM alert_instances WHERE monitored_object_id = 1304 AND alert_code = 'rule.1503' AND status = 'resolved'"
        ).fetchone()["count"]

    assert first_result["processed_items"] == 1
    assert second_result["processed_items"] == 1
    assert open_count == 0
    assert resolved_count == 1


def test_agent_threshold_alert_opens_on_exact_queue_depth_boundaries(seeded_app, seeded_client) -> None:
    warning_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_threshold_agent",
        "seq_start": 81,
        "seq_end": 81,
        "sent_at": "2026-04-10T11:10:00.150+09:00",
        "items": [
            {
                "seq": 81,
                "payload_type": "agent_state",
                "occurred_at": "2026-04-10T11:10:00.100+09:00",
                "target_id": "agent_local",
                "payload": {
                    "heartbeat_time": "2026-04-10T11:10:00.100+09:00",
                    "backend_connection_status": "connected",
                    "outbox_queue_depth": 100,
                    "last_ack_seq": 80,
                },
            }
        ],
    }
    critical_batch = {
        **warning_batch,
        "seq_start": 82,
        "seq_end": 82,
        "items": [
            {
                **warning_batch["items"][0],
                "seq": 82,
                "occurred_at": "2026-04-10T11:10:05.100+09:00",
                "payload": {
                    "heartbeat_time": "2026-04-10T11:10:05.100+09:00",
                    "backend_connection_status": "connected",
                    "outbox_queue_depth": 500,
                    "last_ack_seq": 81,
                },
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=warning_batch).status_code == 202
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=critical_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        rule_alert = db_conn.execute(
            """
            SELECT severity, status, repeat_count, latest_message
            FROM alert_instances
            WHERE monitored_object_id = 1303 AND alert_code = 'rule.1502'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert first_result["processed_items"] == 1
    assert second_result["processed_items"] == 1
    assert rule_alert["severity"] == "critical"
    assert rule_alert["status"] == "open"
    assert rule_alert["repeat_count"] == 2
    assert "500.000" in rule_alert["latest_message"]


def test_agent_stale_threshold_rule_opens_without_new_ingest_and_resolves_on_fresh_heartbeat(seeded_app, seeded_client) -> None:
    seeded_app.config["AGENT_HEARTBEAT_WARNING_SECONDS"] = 10
    seeded_app.config["AGENT_HEARTBEAT_DOWN_SECONDS"] = 30

    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO alert_rules (
                id, rule_key, display_name, status, scope_type, object_type, monitored_object_id,
                state_type, signal_type, signal_key, metric_key, comparison, warning_threshold, critical_threshold,
                cond_mode, is_enabled, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1904,
                "threshold.agent.heartbeat_age_seconds.agent-heartbeat-stale",
                "Agent Heartbeat Stale",
                "published",
                "object_type",
                "MonitoringAgent",
                None,
                "agent",
                "latest_state_metric",
                None,
                "heartbeat_age_seconds",
                "gte",
                10.0,
                30.0,
                "scalar",
                1,
                "Alert when the agent heartbeat grows stale",
                "2026-04-10T11:30:00.000+09:00",
                "2026-04-10T11:30:00.000+09:00",
            ),
        )
        db_conn.commit()

    heartbeat_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_threshold_agent_stale",
        "seq_start": 91,
        "seq_end": 91,
        "sent_at": "2026-04-10T11:30:00.150+09:00",
        "items": [
            {
                "seq": 91,
                "payload_type": "agent_state",
                "occurred_at": "2026-04-10T11:30:00.100+09:00",
                "target_id": "agent_local",
                "payload": {
                    "heartbeat_time": "2026-04-10T11:30:00.100+09:00",
                    "backend_connection_status": "connected",
                    "outbox_queue_depth": 0,
                    "last_ack_seq": 90,
                },
            }
        ],
    }
    recover_batch = {
        **heartbeat_batch,
        "seq_start": 92,
        "seq_end": 92,
        "items": [
            {
                **heartbeat_batch["items"][0],
                "seq": 92,
                "occurred_at": "2026-04-10T11:30:36.100+09:00",
                "payload": {
                    "heartbeat_time": "2026-04-10T11:30:36.100+09:00",
                    "backend_connection_status": "connected",
                    "outbox_queue_depth": 0,
                    "last_ack_seq": 91,
                },
            }
        ],
    }

    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T11:30:00.100+09:00")
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=heartbeat_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        open_count = get_db().execute(
            """
            SELECT COUNT(*) AS count
            FROM alert_instances
            WHERE monitored_object_id = 1303
              AND source_rule_id = 1904
              AND status = 'open'
            """
        ).fetchone()["count"]

    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T11:30:15.100+09:00")
    with seeded_app.app_context():
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        warning_alert = db_conn.execute(
            """
            SELECT severity, status, repeat_count, latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = 1303
              AND source_rule_id = 1904
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        warning_metadata = json.loads(warning_alert["metadata_json"])

    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T11:30:35.100+09:00")
    with seeded_app.app_context():
        third_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        critical_alert = db_conn.execute(
            """
            SELECT severity, status, repeat_count, latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = 1303
              AND source_rule_id = 1904
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        critical_metadata = json.loads(critical_alert["metadata_json"])

    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T11:30:36.200+09:00")
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=recover_batch).status_code == 202

    with seeded_app.app_context():
        fourth_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        resolved_alert = db_conn.execute(
            """
            SELECT status, resolved_at
            FROM alert_instances
            WHERE monitored_object_id = 1303
              AND source_rule_id = 1904
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        archive_row = db_conn.execute(
            """
            SELECT source_rule_id, source_rule_key, source_rule_display_name_snapshot,
                   resolution_source, resolution_reason
            FROM alert_history_archive
            WHERE source_rule_id = 1904
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert first_result["processed_items"] == 1
    assert open_count == 0
    assert second_result["processed_items"] == 0
    assert warning_alert["severity"] == "warning"
    assert warning_alert["status"] == "open"
    assert warning_alert["repeat_count"] == 1
    assert warning_alert["latest_message"] == "heartbeat_age_seconds=15.000 >= 10.000"
    assert warning_metadata["metric_key"] == "heartbeat_age_seconds"
    assert warning_metadata["metric_value"] == 15.0
    assert warning_metadata["explanation"]["threshold_level"] == "warning"
    assert warning_metadata["explanation"]["reason"] == "heartbeat_age_seconds=15.000 >= 10.000"
    assert third_result["processed_items"] == 0
    assert critical_alert["severity"] == "critical"
    assert critical_alert["status"] == "open"
    assert critical_alert["repeat_count"] == 1
    assert critical_alert["latest_message"] == "heartbeat_age_seconds=35.000 >= 30.000"
    assert critical_metadata["metric_value"] == 35.0
    assert critical_metadata["explanation"]["threshold_level"] == "critical"
    assert critical_metadata["explanation"]["reason"] == "heartbeat_age_seconds=35.000 >= 30.000"
    assert fourth_result["processed_items"] == 1
    assert resolved_alert["status"] == "resolved"
    assert resolved_alert["resolved_at"] is not None
    assert archive_row["source_rule_id"] == 1904
    assert archive_row["source_rule_key"] == "threshold.agent.heartbeat_age_seconds.agent-heartbeat-stale"
    assert archive_row["source_rule_display_name_snapshot"] == "Agent Heartbeat Stale"
    assert archive_row["resolution_source"] == "auto_recovery"
    assert archive_row["resolution_reason"] == "threshold_cleared"


def test_process_no_data_threshold_rule_opens_without_new_ingest_and_resolves_on_fresh_data(seeded_app, seeded_client) -> None:
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO alert_rules (
                id, rule_key, display_name, status, scope_type, object_type, monitored_object_id,
                state_type, signal_type, signal_key, metric_key, comparison, warning_threshold, critical_threshold,
                cond_mode, is_enabled, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1905,
                "threshold.process.latest_state_age_seconds.process-no-data",
                "Process No Data",
                "published",
                "monitored_object",
                None,
                1302,
                "process",
                "latest_state_metric",
                None,
                "latest_state_age_seconds",
                "gte",
                10.0,
                30.0,
                "scalar",
                1,
                "Alert when process data stops arriving",
                "2026-04-10T11:40:00.000+09:00",
                "2026-04-10T11:40:00.000+09:00",
            ),
        )
        db_conn.commit()

    initial_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_threshold_process_no_data",
        "seq_start": 101,
        "seq_end": 101,
        "sent_at": "2026-04-10T11:40:00.150+09:00",
        "items": [
            {
                "seq": 101,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T11:40:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 10.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }
    recover_batch = {
        **initial_batch,
        "seq_start": 102,
        "seq_end": 102,
        "items": [
            {
                **initial_batch["items"][0],
                "seq": 102,
                "occurred_at": "2026-04-10T11:40:36.100+09:00",
            }
        ],
    }

    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T11:40:00.100+09:00")
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=initial_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE latest_states
            SET occurred_at = ?, received_at = ?, updated_at = ?
            WHERE monitored_object_id = ? AND state_type = ?
            """,
            (
                "2026-04-10T11:40:00.100+09:00",
                "2026-04-10T11:40:00.100+09:00",
                "2026-04-10T11:40:00.100+09:00",
                1302,
                "process",
            ),
        )
        db_conn.commit()
        open_count = db_conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1905
              AND status = 'open'
            """
        ).fetchone()["count"]

    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T11:40:15.100+09:00")
    with seeded_app.app_context():
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        warning_alert = db_conn.execute(
            """
            SELECT severity, status, repeat_count, latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1905
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        warning_metadata = json.loads(warning_alert["metadata_json"])

    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T11:40:35.100+09:00")
    with seeded_app.app_context():
        third_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        critical_alert = db_conn.execute(
            """
            SELECT severity, status, repeat_count, latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1905
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        critical_metadata = json.loads(critical_alert["metadata_json"])

    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T11:40:36.200+09:00")
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=recover_batch).status_code == 202

    with seeded_app.app_context():
        fourth_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        resolved_alert = db_conn.execute(
            """
            SELECT status, resolved_at
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1905
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        archive_row = db_conn.execute(
            """
            SELECT source_rule_id, source_rule_key, source_rule_display_name_snapshot,
                   resolution_source, resolution_reason
            FROM alert_history_archive
            WHERE source_rule_id = 1905
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert first_result["processed_items"] == 1
    assert open_count == 0
    assert second_result["processed_items"] == 0
    assert warning_alert["severity"] == "warning"
    assert warning_alert["status"] == "open"
    assert warning_alert["repeat_count"] == 1
    assert warning_alert["latest_message"] == "latest_state_age_seconds=15.000 >= 10.000"
    assert warning_metadata["metric_key"] == "latest_state_age_seconds"
    assert warning_metadata["metric_value"] == 15.0
    assert warning_metadata["explanation"]["threshold_level"] == "warning"
    assert warning_metadata["explanation"]["reason"] == "latest_state_age_seconds=15.000 >= 10.000"
    assert third_result["processed_items"] == 0
    assert critical_alert["severity"] == "critical"
    assert critical_alert["status"] == "open"
    assert critical_alert["repeat_count"] == 1
    assert critical_alert["latest_message"] == "latest_state_age_seconds=35.000 >= 30.000"
    assert critical_metadata["metric_key"] == "latest_state_age_seconds"
    assert critical_metadata["metric_value"] == 35.0
    assert critical_metadata["explanation"]["threshold_level"] == "critical"
    assert critical_metadata["explanation"]["reason"] == "latest_state_age_seconds=35.000 >= 30.000"
    assert fourth_result["processed_items"] == 1
    assert resolved_alert["status"] == "resolved"
    assert resolved_alert["resolved_at"] is not None
    assert archive_row["source_rule_id"] == 1905
    assert archive_row["source_rule_key"] == "threshold.process.latest_state_age_seconds.process-no-data"
    assert archive_row["source_rule_display_name_snapshot"] == "Process No Data"
    assert archive_row["resolution_source"] == "auto_recovery"
    assert archive_row["resolution_reason"] == "data_resumed"


def test_specific_threshold_rule_resolves_existing_general_alert_by_precedence(seeded_app, seeded_client) -> None:
    general_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_threshold_precedence",
        "seq_start": 83,
        "seq_end": 83,
        "sent_at": "2026-04-10T11:12:00.150+09:00",
        "items": [
            {
                "seq": 83,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T11:12:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 88.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }
    specific_batch = {
        **general_batch,
        "seq_start": 84,
        "seq_end": 84,
        "items": [
            {
                **general_batch["items"][0],
                "seq": 84,
                "occurred_at": "2026-04-10T11:12:05.100+09:00",
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=general_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        initial_general = db_conn.execute(
            """
            SELECT id, alert_code, severity, status
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND alert_code = 'rule.1501'
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        db_conn.execute(
            """
            INSERT INTO alert_rules (
                id, rule_key, display_name, status, scope_type, object_type, monitored_object_id,
                state_type, metric_key, comparison, warning_threshold, critical_threshold,
                cond_mode, is_enabled, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1901,
                "threshold.process.cpu_usage.app-process-cpu-override",
                "App Process CPU Override",
                "published",
                "monitored_object",
                None,
                1302,
                "process",
                "cpu_usage",
                "gte",
                80.0,
                95.0,
                "scalar",
                1,
                "Specific override for App Process",
                "2026-04-10T11:12:04.000+09:00",
                "2026-04-10T11:12:04.000+09:00",
            ),
        )
        db_conn.commit()

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=specific_batch).status_code == 202

    with seeded_app.app_context():
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        general_rows = db_conn.execute(
            """
            SELECT id, alert_code, severity, status, resolved_at
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1501
            ORDER BY id ASC
            """
        ).fetchall()
        specific_row = db_conn.execute(
            """
            SELECT alert_code, severity, status, repeat_count, latest_message
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1901
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        history_row = db_conn.execute(
            """
            SELECT note, payload_json
            FROM alert_history
            WHERE alert_instance_id = ?
              AND action_type = 'resolved'
            ORDER BY id DESC
            LIMIT 1
            """,
            (initial_general["id"],),
        ).fetchone()
        archive_row = db_conn.execute(
            """
            SELECT source_rule_id, source_rule_key, source_rule_display_name_snapshot,
                   resolution_source, resolution_reason
            FROM alert_history_archive
            WHERE source_rule_id = 1501
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert first_result["processed_items"] == 1
    assert second_result["processed_items"] == 1
    assert initial_general["alert_code"] == "rule.1501"
    assert initial_general["status"] == "open"
    assert len(general_rows) == 1
    assert general_rows[0]["status"] == "resolved"
    assert general_rows[0]["resolved_at"] is not None
    assert specific_row["alert_code"] == "rule.1901"
    assert specific_row["severity"] == "warning"
    assert specific_row["status"] == "open"
    assert specific_row["repeat_count"] == 1
    assert "88.000" in specific_row["latest_message"]
    assert history_row["note"] == "suppressed by threshold precedence"
    assert json.loads(history_row["payload_json"])["reason"] == "suppressed_by_precedence"
    assert archive_row["source_rule_id"] == 1501
    assert archive_row["source_rule_key"] == "threshold.process.cpu_usage.process-cpu-high"
    assert archive_row["source_rule_display_name_snapshot"] == "Process CPU High"
    assert archive_row["resolution_source"] == "system_cleanup"
    assert archive_row["resolution_reason"] == "suppressed_by_precedence"


def test_compound_threshold_rule_wins_at_runtime_and_resolves_on_recovery(seeded_app, seeded_client) -> None:
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO alert_rules (
                id, rule_key, display_name, status, scope_type, object_type, monitored_object_id,
                state_type, metric_key, comparison, warning_threshold, critical_threshold,
                cond_mode, warning_logical_op, warning_cl1_comp, warning_cl1_val, warning_cl2_comp, warning_cl2_val,
                critical_logical_op, critical_cl1_comp, critical_cl1_val, critical_cl2_comp, critical_cl2_val,
                is_enabled, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1902,
                "threshold.process.cpu_usage.app-process-cpu-band",
                "App Process CPU Band",
                "published",
                "monitored_object",
                None,
                1302,
                "process",
                "cpu_usage",
                "gte",
                None,
                None,
                "compound",
                "or",
                "lte",
                20.0,
                "gte",
                80.0,
                "or",
                "lte",
                10.0,
                "gte",
                90.0,
                1,
                "Specific compound override for App Process",
                "2026-04-10T11:13:00.000+09:00",
                "2026-04-10T11:13:00.000+09:00",
            ),
        )
        db_conn.commit()

    warning_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_threshold_compound_runtime",
        "seq_start": 85,
        "seq_end": 85,
        "sent_at": "2026-04-10T11:13:00.150+09:00",
        "items": [
            {
                "seq": 85,
                "payload_type": "process_snapshot",
                "occurred_at": "2026-04-10T11:13:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 97.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }
    recover_batch = {
        **warning_batch,
        "seq_start": 86,
        "seq_end": 86,
        "items": [
            {
                **warning_batch["items"][0],
                "seq": 86,
                "occurred_at": "2026-04-10T11:13:05.100+09:00",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 50.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=warning_batch).status_code == 202
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=recover_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        compound_alert = db_conn.execute(
            """
            SELECT alert_code, source_rule_id, severity, status, latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1902
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        general_open_count = db_conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1501
              AND status = 'open'
            """
        ).fetchone()["count"]
        compound_metadata = json.loads(compound_alert["metadata_json"])

    with seeded_app.app_context():
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        resolved_compound = db_conn.execute(
            """
            SELECT status, resolved_at
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1902
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        archive_row = db_conn.execute(
            """
            SELECT source_rule_id, source_rule_key, source_rule_display_name_snapshot,
                   resolution_source, resolution_reason
            FROM alert_history_archive
            WHERE source_rule_id = 1902
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert first_result["processed_items"] == 1
    assert compound_alert["alert_code"] == "rule.1902"
    assert compound_alert["severity"] == "critical"
    assert compound_alert["status"] == "open"
    assert "matched critical condition" in compound_alert["latest_message"]
    assert general_open_count == 0
    assert compound_metadata["cond_mode"] == "compound"
    assert compound_metadata["winning_condition_trace"] == {
        "severity": "critical",
        "condition_mode": "compound",
        "logical_operator": "or",
        "matched_clause_indexes": [1],
    }
    assert compound_metadata["explanation"] == {
        "rule_key": "threshold.process.cpu_usage.app-process-cpu-band",
        "display_name": "App Process CPU Band",
        "signal_type": "latest_state_metric",
        "value_key": "cpu_usage",
        "threshold_level": "critical",
        "reason": "cpu_usage=97.000 matched critical condition (or, clause 2)",
        "winning_condition_trace": {
            "severity": "critical",
            "condition_mode": "compound",
            "logical_operator": "or",
            "matched_clause_indexes": [1],
        },
        "family_key": ["threshold", "process", "cpu_usage", "gte"],
        "winner_rule_key": "threshold.process.cpu_usage.app-process-cpu-band",
        "winner_display_name": "App Process CPU Band",
        "suppressed_rule_keys": ["threshold.process.cpu_usage.process-cpu-high"],
        "suppressed_rule_display_names": ["Process CPU High"],
        "resolution_reason": None,
    }
    assert second_result["processed_items"] == 1
    assert resolved_compound["status"] == "resolved"
    assert resolved_compound["resolved_at"] is not None
    assert archive_row["source_rule_id"] == 1902
    assert archive_row["source_rule_key"] == "threshold.process.cpu_usage.app-process-cpu-band"
    assert archive_row["source_rule_display_name_snapshot"] == "App Process CPU Band"
    assert archive_row["resolution_source"] == "auto_recovery"
    assert archive_row["resolution_reason"] == "threshold_cleared"


def test_grouped_event_rule_opens_from_repeat_count_and_resolves_after_window(seeded_app, seeded_client) -> None:
    seeded_app.config["GROUPED_EVENT_WINDOW_SECONDS"] = 60
    base_time = datetime.now().astimezone().replace(microsecond=0)
    first_time = base_time
    second_time = base_time + timedelta(seconds=5)
    third_time = base_time + timedelta(seconds=10)
    recover_time = base_time + timedelta(seconds=20)
    expired_time = base_time - timedelta(seconds=120)

    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO alert_rules (
                id, rule_key, display_name, status, scope_type, object_type, monitored_object_id,
                state_type, signal_type, signal_key, metric_key, comparison, warning_threshold, critical_threshold,
                cond_mode, is_enabled, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1903,
                "event.process.process_restarted.process-restart-burst",
                "Process Restart Burst",
                "published",
                "monitored_object",
                None,
                1302,
                "process",
                "grouped_event_repeat",
                "process_restarted",
                "process_restarted",
                "gte",
                2.0,
                3.0,
                "scalar",
                1,
                "Restart storm alert",
                "2026-04-10T11:14:00.000+09:00",
                "2026-04-10T11:14:00.000+09:00",
            ),
        )
        db_conn.commit()

    def event_batch(seq: int, when: datetime) -> dict:
        return {
            "agent_id": "agent_local",
            "boot_id": "boot_event_repeat_runtime",
            "seq_start": seq,
            "seq_end": seq,
            "sent_at": when.isoformat(),
            "items": [
                {
                    "seq": seq,
                    "payload_type": "process_event",
                    "occurred_at": when.isoformat(),
                    "target_id": "app_main",
                    "payload": {
                        "event_type": "process_restarted",
                        "severity": "warning",
                        "message": "process restarted",
                    },
                }
            ],
        }

    recover_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_event_repeat_runtime",
        "seq_start": 90,
        "seq_end": 90,
        "sent_at": recover_time.isoformat(),
        "items": [
            {
                "seq": 90,
                "payload_type": "process_snapshot",
                "occurred_at": recover_time.isoformat(),
                "target_id": "app_main",
                "payload": {
                    "pid": 1234,
                    "state": "running",
                    "cpu_usage": 10.0,
                    "memory_rss": 4096,
                },
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=event_batch(87, first_time)).status_code == 202
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=event_batch(88, second_time)).status_code == 202
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=event_batch(89, third_time)).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        warning_alert = db_conn.execute(
            """
            SELECT alert_code, source_rule_id, severity, status, latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1903
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        warning_metadata = json.loads(warning_alert["metadata_json"])

    with seeded_app.app_context():
        third_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        critical_alert = db_conn.execute(
            """
            SELECT severity, status, repeat_count, latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1903
              AND status = 'open'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        critical_metadata = json.loads(critical_alert["metadata_json"])
        db_conn.execute(
            """
            UPDATE grouped_events
            SET last_occurred_at = ?, updated_at = ?
            WHERE monitored_object_id = ? AND event_type = ?
            """,
            (expired_time.isoformat(), expired_time.isoformat(), 1302, "process_restarted"),
        )
        db_conn.commit()

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=recover_batch).status_code == 202

    with seeded_app.app_context():
        fourth_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        resolved_alert = db_conn.execute(
            """
            SELECT status, resolved_at
            FROM alert_instances
            WHERE monitored_object_id = 1302
              AND source_rule_id = 1903
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        archive_row = db_conn.execute(
            """
            SELECT source_rule_id, source_rule_key, source_rule_display_name_snapshot,
                   resolution_source, resolution_reason
            FROM alert_history_archive
            WHERE source_rule_id = 1903
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    assert first_result["processed_items"] == 1
    assert second_result["processed_items"] == 1
    assert warning_alert["alert_code"] == "rule.1903"
    assert warning_alert["source_rule_id"] == 1903
    assert warning_alert["severity"] == "warning"
    assert warning_alert["status"] == "open"
    assert warning_alert["latest_message"] == "process_restarted repeat_count=2 >= 2"
    assert warning_metadata["signal_type"] == "grouped_event_repeat"
    assert warning_metadata["signal_key"] == "process_restarted"
    assert warning_metadata["family_key"] == ["event", "process", "process_restarted", "gte"]
    assert warning_metadata["explanation"]["reason"] == "process_restarted repeat_count=2 >= 2"
    assert warning_metadata["explanation"]["winner_rule_key"] == "event.process.process_restarted.process-restart-burst"
    assert third_result["processed_items"] == 1
    assert critical_alert["severity"] == "critical"
    assert critical_alert["status"] == "open"
    assert critical_alert["repeat_count"] == 2
    assert critical_alert["latest_message"] == "process_restarted repeat_count=3 >= 3"
    assert critical_metadata["signal_type"] == "grouped_event_repeat"
    assert critical_metadata["winning_condition_trace"]["severity"] == "critical"
    assert critical_metadata["explanation"]["threshold_level"] == "critical"
    assert critical_metadata["explanation"]["reason"] == "process_restarted repeat_count=3 >= 3"
    assert fourth_result["processed_items"] == 1
    assert resolved_alert["status"] == "resolved"
    assert resolved_alert["resolved_at"] is not None
    assert archive_row["source_rule_id"] == 1903
    assert archive_row["source_rule_key"] == "event.process.process_restarted.process-restart-burst"
    assert archive_row["source_rule_display_name_snapshot"] == "Process Restart Burst"
    assert archive_row["resolution_source"] == "auto_recovery"
    assert archive_row["resolution_reason"] == "event_window_elapsed"


def test_grouped_events_merge_at_exact_window_boundary(seeded_app, seeded_client) -> None:
    seeded_app.config["GROUPED_EVENT_WINDOW_SECONDS"] = 60
    first_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_group_exact",
        "seq_start": 91,
        "seq_end": 91,
        "sent_at": "2026-04-10T11:20:00.150+09:00",
        "items": [
            {
                "seq": 91,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T11:20:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_stopped",
                    "severity": "warning",
                    "message": "storm stop",
                },
            }
        ],
    }
    second_batch = {
        **first_batch,
        "seq_start": 92,
        "seq_end": 92,
        "items": [
            {
                **first_batch["items"][0],
                "seq": 92,
                "occurred_at": "2026-04-10T11:21:00.100+09:00",
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=first_batch).status_code == 202
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=second_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        group_rows = db_conn.execute(
            """
            SELECT event_type, repeat_count
            FROM grouped_events
            WHERE monitored_object_id = 1302
            ORDER BY id
            """
        ).fetchall()

    assert first_result["processed_items"] == 1
    assert second_result["processed_items"] == 1
    assert len(group_rows) == 1
    assert group_rows[0]["event_type"] == "process_stopped"
    assert group_rows[0]["repeat_count"] == 2


def test_grouped_events_split_beyond_window_boundary(seeded_app, seeded_client) -> None:
    seeded_app.config["GROUPED_EVENT_WINDOW_SECONDS"] = 60
    first_batch = {
        "agent_id": "agent_local",
        "boot_id": "boot_group_split",
        "seq_start": 93,
        "seq_end": 93,
        "sent_at": "2026-04-10T11:22:00.150+09:00",
        "items": [
            {
                "seq": 93,
                "payload_type": "process_event",
                "occurred_at": "2026-04-10T11:22:00.100+09:00",
                "target_id": "app_main",
                "payload": {
                    "event_type": "process_stopped",
                    "severity": "warning",
                    "message": "storm stop",
                },
            }
        ],
    }
    second_batch = {
        **first_batch,
        "seq_start": 94,
        "seq_end": 94,
        "items": [
            {
                **first_batch["items"][0],
                "seq": 94,
                "occurred_at": "2026-04-10T11:23:01.100+09:00",
            }
        ],
    }

    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=first_batch).status_code == 202
    assert seeded_client.post("/api/agents/ingest", headers=agent_headers(), json=second_batch).status_code == 202

    with seeded_app.app_context():
        first_result = process_pending_ingest(limit=1)
        second_result = process_pending_ingest(limit=1)
        db_conn = get_db()
        group_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM grouped_events WHERE monitored_object_id = 1302 AND event_type = 'process_stopped'"
        ).fetchone()["count"]

    assert first_result["processed_items"] == 1
    assert second_result["processed_items"] == 1
    assert group_count == 2


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
