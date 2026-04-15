from __future__ import annotations

import json
from datetime import datetime

from werkzeug.security import generate_password_hash

from app.db import get_db


def login(client, username: str = "admin", password: str = "admin123!"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def seed_regular_user(app) -> None:
    with app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO users (id, username, password_hash, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 'user', 1, ?, ?)
            """,
            (
                2,
                "viewer",
                generate_password_hash("viewer123!"),
                "2026-04-12T10:00:00.000+09:00",
                "2026-04-12T10:00:00.000+09:00",
            ),
        )
        db_conn.commit()


def seed_admin_dashboard_rows(app) -> None:
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
                10,
                102,
                "app_main",
                "process",
                "up",
                "normal",
                json.dumps({"pid": 1234, "cpu_usage": 1.5}),
                "2026-04-12T11:00:00.100+09:00",
                "2026-04-12T11:00:00.200+09:00",
                "2026-04-12T11:00:00.200+09:00",
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
                11,
                103,
                "agent_local",
                "agent",
                "up",
                "normal",
                json.dumps(
                    {
                        "heartbeat_time": "2026-04-12T11:00:20.000+09:00",
                        "backend_connection_status": "connected",
                        "outbox_queue_depth": 3,
                        "last_ack_seq": 7,
                    }
                ),
                "2026-04-12T11:00:20.000+09:00",
                "2026-04-12T11:00:20.100+09:00",
                "2026-04-12T11:00:20.100+09:00",
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
                12,
                101,
                "agent_local:host",
                "host",
                "up",
                "normal",
                json.dumps(
                    {
                        "hostname": "host-alpha",
                        "cpu_usage": 18.4,
                        "loadavg_1": 0.24,
                        "loadavg_5": 0.31,
                        "memory_total": 16777216,
                        "memory_used": 10485760,
                    }
                ),
                "2026-04-12T11:00:25.000+09:00",
                "2026-04-12T11:00:25.100+09:00",
                "2026-04-12T11:00:25.100+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO ingest_inbox (
                agent_id, boot_id, seq_start, seq_end, received_at, payload_json, status, processed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                "boot_pending",
                1,
                2,
                "2026-04-12T11:01:00.100+09:00",
                json.dumps({"items": [{"seq": 1}, {"seq": 2}]}),
                "pending",
                None,
                None,
            ),
        )
        db_conn.execute(
            """
            INSERT INTO ingest_inbox (
                agent_id, boot_id, seq_start, seq_end, received_at, payload_json, status, processed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                "boot_processed",
                3,
                3,
                "2026-04-12T11:02:00.100+09:00",
                json.dumps({"items": [{"seq": 3}]}),
                "processed",
                "2026-04-12T11:02:01.100+09:00",
                None,
            ),
        )
        db_conn.execute(
            """
            INSERT INTO ingest_inbox (
                agent_id, boot_id, seq_start, seq_end, received_at, payload_json, status, processed_at, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                "boot_failed",
                4,
                4,
                "2026-04-12T11:03:00.100+09:00",
                json.dumps({"items": [{"seq": 4}]}),
                "failed",
                "2026-04-12T11:03:01.100+09:00",
                "json parse error",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO raw_events (
                agent_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                "app_main",
                "process_stopped",
                "warning",
                "process not found",
                json.dumps({"pid": 1234}),
                "2026-04-12T11:05:00.100+09:00",
                "2026-04-12T11:05:00.200+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO raw_events (
                agent_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                "agent_local",
                "agent_heartbeat_lost",
                "warning",
                "heartbeat delayed",
                json.dumps({"delay_ms": 5000}),
                "2026-04-12T11:04:00.100+09:00",
                "2026-04-12T11:04:00.200+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO debug_payload_logs (
                channel, direction, endpoint_or_topic, agent_id, user_id, session_id,
                trace_id, status_code, payload_json, payload_size, is_redacted, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_backend",
                "request",
                "/api/agents/ingest",
                "agent_local",
                1,
                "sess-admin",
                "trace-001",
                202,
                json.dumps({"items": 2}),
                len(json.dumps({"items": 2}).encode("utf-8")),
                1,
                "2026-04-12T11:03:10.100+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO debug_payload_logs (
                channel, direction, endpoint_or_topic, agent_id, user_id, session_id,
                trace_id, status_code, payload_json, payload_size, is_redacted, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_backend",
                "response",
                "/api/agents/ingest",
                "agent_local",
                1,
                "sess-admin",
                "trace-001",
                202,
                json.dumps({"ack_seq": 4, "accepted_count": 1}),
                len(json.dumps({"ack_seq": 4, "accepted_count": 1}).encode("utf-8")),
                1,
                "2026-04-12T11:03:10.200+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO cleanup_runs (
                started_at, finished_at, raw_events_deleted, debug_payload_logs_deleted, ingest_inbox_deleted
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "2026-04-12T10:50:00.000+09:00",
                "2026-04-12T10:50:05.000+09:00",
                2,
                1,
                1,
            ),
        )
        db_conn.commit()


def test_admin_summary_requires_admin_role(seeded_app, seeded_client) -> None:
    response = seeded_client.get("/api/admin/summary")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"

    seed_regular_user(seeded_app)
    login_response = login(seeded_client, username="viewer", password="viewer123!")
    assert login_response.status_code == 200

    response = seeded_client.get("/api/admin/summary")
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


def test_admin_summary_returns_counts_and_recent_failures(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-12T11:01:10.000+09:00")
    login(seeded_client)

    response = seeded_client.get("/api/admin/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["service_status"] == "ok"
    assert payload["debug_payload_logging_enabled"] is False
    assert payload["counts"] == {
        "users": 1,
        "views": 1,
        "view_nodes": 3,
        "view_edges": 1,
        "latest_states": 3,
        "raw_events": 2,
        "debug_payload_logs": 2,
        "cleanup_runs": 1,
    }
    assert payload["ingest_inbox"]["status_counts"] == {
        "failed": 1,
        "pending": 1,
        "processed": 1,
        "processing": 0,
    }
    assert len(payload["ingest_inbox"]["recent_failed"]) == 1
    assert payload["ingest_inbox"]["recent_failed"][0]["error_message"] == "json parse error"
    assert payload["runtime"]["state_type_counts"] == {"agent": 1, "host": 1, "process": 1}
    assert payload["runtime"]["status_counts"]["down"] == 1
    assert payload["runtime"]["stale_agent_count"] == 1
    assert payload["stale_agents"][0]["target_id"] == "agent_local"
    assert payload["retention_policy"] == {
        "raw_events_days": 7,
        "debug_payload_hours": 24,
        "ingest_inbox_days": 7,
    }
    assert payload["last_cleanup"]["raw_events_deleted"] == 2
    assert payload["last_cleanup"]["debug_payload_logs_deleted"] == 1


def test_admin_ingest_inbox_filters_status_and_limit(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/admin/ingest-inbox?status=failed&limit=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["status"] == "failed"
    assert payload["items"][0]["item_count"] == 1


def test_admin_raw_events_rejects_invalid_limit(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/raw-events?limit=abc")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_admin_raw_events_accept_boundary_limits(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    low_response = seeded_client.get("/api/admin/raw-events?limit=1")
    high_response = seeded_client.get("/api/admin/raw-events?limit=100")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 2


def test_admin_raw_events_reject_out_of_range_limits(seeded_client) -> None:
    login(seeded_client)

    zero_response = seeded_client.get("/api/admin/raw-events?limit=0")
    over_response = seeded_client.get("/api/admin/raw-events?limit=101")

    assert zero_response.status_code == 400
    assert zero_response.get_json()["error"]["code"] == "validation_error"
    assert over_response.status_code == 400
    assert over_response.get_json()["error"]["code"] == "validation_error"


def test_admin_debug_payloads_support_filters(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get(
        "/api/admin/debug-payloads?channel=agent_backend&direction=response&trace_id=trace-001"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["debug_payload_logging_enabled"] is False
    assert len(payload["items"]) == 1
    assert payload["items"][0]["direction"] == "response"
    assert payload["items"][0]["username"] == "admin"
    assert payload["items"][0]["payload"]["ack_seq"] == 4


def test_admin_latest_states_support_filters_and_derived_status(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-12T11:01:10.000+09:00")
    login(seeded_client)

    response = seeded_client.get("/api/admin/latest-states?state_type=agent&status=down")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["target_id"] == "agent_local"
    assert payload["items"][0]["state"]["heartbeat_timeout_level"] == "down"


def test_admin_cleanup_runs_returns_recent_history(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/admin/cleanup-runs?limit=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["raw_events_deleted"] == 2
    assert payload["items"][0]["debug_payload_logs_deleted"] == 1
