from __future__ import annotations

import json
from datetime import datetime

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
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:05.000+09:00")
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert [item["target_id"] for item in payload["items"]] == ["app_main", "agent_local"]
    assert payload["items"][0]["state"]["pid"] == 1234
    assert payload["items"][1]["state"]["outbox_queue_depth"] == 0
    assert payload["items"][1]["status"] == "up"
    assert payload["items"][1]["state"]["heartbeat_timeout_level"] == "normal"


def test_latest_state_marks_agent_warning_when_heartbeat_is_delayed(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:20.000+09:00")
    seeded_app.config["AGENT_HEARTBEAT_WARNING_SECONDS"] = 10
    seeded_app.config["AGENT_HEARTBEAT_DOWN_SECONDS"] = 30
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    agent_state = payload["items"][1]
    assert agent_state["target_id"] == "agent_local"
    assert agent_state["status"] == "warning"
    assert agent_state["severity"] == "warning"
    assert agent_state["state"]["heartbeat_timeout_level"] == "warning"
    assert agent_state["state"]["heartbeat_timeout_message"] == "heartbeat delayed"


def test_latest_state_marks_agent_down_when_heartbeat_times_out(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:21:00.000+09:00")
    seeded_app.config["AGENT_HEARTBEAT_WARNING_SECONDS"] = 10
    seeded_app.config["AGENT_HEARTBEAT_DOWN_SECONDS"] = 30
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    agent_state = payload["items"][1]
    assert agent_state["target_id"] == "agent_local"
    assert agent_state["status"] == "down"
    assert agent_state["severity"] == "critical"
    assert agent_state["state"]["heartbeat_timeout_level"] == "down"
    assert agent_state["state"]["heartbeat_timeout_message"] == "heartbeat timeout"


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


def test_events_accept_boundary_limits(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    low_response = seeded_client.get("/api/views/1/events?limit=1")
    high_response = seeded_client.get("/api/views/1/events?limit=100")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 2


def test_events_reject_out_of_range_limits(seeded_client) -> None:
    login(seeded_client)

    zero_response = seeded_client.get("/api/views/1/events?limit=0")
    over_response = seeded_client.get("/api/views/1/events?limit=101")

    assert zero_response.status_code == 400
    assert zero_response.get_json()["error"]["code"] == "validation_error"
    assert over_response.status_code == 400
    assert over_response.get_json()["error"]["code"] == "validation_error"


def test_latest_state_marks_agent_warning_at_exact_warning_threshold(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:10.100+09:00")
    seeded_app.config["AGENT_HEARTBEAT_WARNING_SECONDS"] = 10
    seeded_app.config["AGENT_HEARTBEAT_DOWN_SECONDS"] = 30
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    agent_state = payload["items"][1]
    assert agent_state["status"] == "warning"
    assert agent_state["severity"] == "warning"
    assert agent_state["state"]["heartbeat_age_seconds"] == 10.0
    assert agent_state["state"]["heartbeat_timeout_level"] == "warning"


def test_latest_state_marks_agent_down_at_exact_down_threshold(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:30.100+09:00")
    seeded_app.config["AGENT_HEARTBEAT_WARNING_SECONDS"] = 10
    seeded_app.config["AGENT_HEARTBEAT_DOWN_SECONDS"] = 30
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    agent_state = payload["items"][1]
    assert agent_state["status"] == "down"
    assert agent_state["severity"] == "critical"
    assert agent_state["state"]["heartbeat_age_seconds"] == 30.0
    assert agent_state["state"]["heartbeat_timeout_level"] == "down"
