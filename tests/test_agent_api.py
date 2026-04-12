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
        "seq_end": 12,
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
                "seq": 12,
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
    assert payload["ack_seq"] == 12
    assert payload["accepted_count"] == 3

    with seeded_app.app_context():
        db_conn = get_db()
        row = db_conn.execute(
            "SELECT agent_id, boot_id, seq_start, seq_end, status FROM ingest_inbox ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert row["agent_id"] == "agent_local"
    assert row["boot_id"] == "boot_001"
    assert row["seq_start"] == 10
    assert row["seq_end"] == 12
    assert row["status"] == "pending"


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
            "SELECT target_id, state_type, status FROM latest_states ORDER BY id"
        ).fetchall()
        event_rows = db_conn.execute(
            "SELECT target_id, event_type, severity FROM raw_events ORDER BY id"
        ).fetchall()

    assert result == {
        "processed_batches": 1,
        "failed_batches": 0,
        "processed_items": 3,
    }
    assert inbox_row["status"] == "processed"
    assert inbox_row["processed_at"] is not None
    assert [(row["target_id"], row["state_type"], row["status"]) for row in state_rows] == [
        ("agent_local", "agent", "up"),
        ("app_main", "process", "down"),
    ]
    assert [(row["target_id"], row["event_type"], row["severity"]) for row in event_rows] == [
        ("app_main", "process_stopped", "warning"),
    ]


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
    assert "processed_items=3" in result.output
