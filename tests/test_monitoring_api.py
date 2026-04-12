from __future__ import annotations

import json

from app.db import get_db


def login(client, username: str = "admin", password: str = "admin123!"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def seed_monitoring_rows(app) -> None:
    with app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO latest_states (
                id, view_node_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                102,
                "app_main",
                "process",
                "up",
                "normal",
                json.dumps({"pid": 1234, "cpu_usage": 3.2, "memory_rss": 10485760}),
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.220+09:00",
                "2026-04-10T10:20:00.220+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO latest_states (
                id, view_node_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                103,
                "agent_local",
                "agent",
                "up",
                "normal",
                json.dumps({"heartbeat_time": "2026-04-10T10:20:00.100+09:00", "outbox_queue_depth": 0}),
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.220+09:00",
                "2026-04-10T10:20:00.220+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO latest_states (
                id, view_node_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,
                None,
                "unrelated_target",
                "process",
                "down",
                "warning",
                json.dumps({"pid": 9999}),
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.220+09:00",
                "2026-04-10T10:20:00.220+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO raw_events (
                id, agent_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                101,
                "agent_local",
                "app_main",
                "process_stopped",
                "warning",
                "process not found",
                json.dumps({"pid": 1234}),
                "2026-04-10T10:21:10.100+09:00",
                "2026-04-10T10:21:10.230+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO raw_events (
                id, agent_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                102,
                "agent_local",
                "agent_local",
                "agent_heartbeat_lost",
                "warning",
                "heartbeat delayed",
                json.dumps({"delay_ms": 5000}),
                "2026-04-10T10:20:10.100+09:00",
                "2026-04-10T10:20:10.230+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO raw_events (
                id, agent_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                103,
                "agent_local",
                "outside_view",
                "process_stopped",
                "warning",
                "outside",
                json.dumps({"pid": 5555}),
                "2026-04-10T10:30:10.100+09:00",
                "2026-04-10T10:30:10.230+09:00",
            ),
        )
        db_conn.commit()


def test_latest_state_requires_login(seeded_client) -> None:
    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_latest_state_returns_only_view_targets_in_view_order(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert [item["target_id"] for item in payload["items"]] == ["app_main", "agent_local"]
    assert payload["items"][0]["state"]["pid"] == 1234
    assert payload["items"][1]["state"]["outbox_queue_depth"] == 0


def test_events_returns_recent_items_filtered_by_view_targets(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/events?limit=2")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 2
    assert [item["id"] for item in payload["items"]] == [101, 102]
    assert all(item["target_id"] in {"app_main", "agent_local"} for item in payload["items"])


def test_events_reject_invalid_limit(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/views/1/events?limit=abc")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"
