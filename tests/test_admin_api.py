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
            INSERT INTO users (id, username, password_hash, role, metamodel_permission, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 'user', 'view', 1, ?, ?)
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
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                10,
                102,
                1302,
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
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                11,
                103,
                1303,
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
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                12,
                101,
                1304,
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
                agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                1302,
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
                agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                1303,
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
            INSERT INTO alert_instances (
                monitored_object_id, alert_code, severity, status, first_occurred_at, last_occurred_at,
                repeat_count, latest_message, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1303,
                "agent.warning",
                "warning",
                "open",
                "2026-04-12T11:04:00.100+09:00",
                "2026-04-12T11:04:00.100+09:00",
                1,
                "heartbeat delayed",
                json.dumps({"event_type": "agent_heartbeat_lost"}),
                "2026-04-12T11:04:00.200+09:00",
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
                started_at, finished_at, raw_events_deleted, grouped_events_deleted, debug_payload_logs_deleted, ingest_inbox_deleted
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "2026-04-12T10:50:00.000+09:00",
                "2026-04-12T10:50:05.000+09:00",
                2,
                1,
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
        "grouped_events": 0,
        "open_alerts": 1,
        "alert_rules": 3,
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
        "grouped_events_days": 7,
        "debug_payload_hours": 24,
        "ingest_inbox_days": 7,
    }
    assert payload["last_cleanup"]["raw_events_deleted"] == 2
    assert payload["last_cleanup"]["grouped_events_deleted"] == 1
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


def test_admin_grouped_events_returns_recent_groups(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO grouped_events (
                monitored_object_id, target_id, event_type, severity, first_occurred_at, last_occurred_at,
                repeat_count, latest_message, latest_event_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1302,
                "app_main",
                "process_stopped",
                "warning",
                "2026-04-12T11:05:00.100+09:00",
                "2026-04-12T11:05:10.100+09:00",
                3,
                "process not found",
                json.dumps({"pid": 1234}),
                "2026-04-12T11:05:00.200+09:00",
                "2026-04-12T11:05:10.200+09:00",
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/admin/grouped-events?limit=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["event_type"] == "process_stopped"
    assert payload["items"][0]["repeat_count"] == 3


def test_admin_grouped_event_drill_down_returns_matching_raw_events(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO grouped_events (
                monitored_object_id, target_id, event_type, severity, first_occurred_at, last_occurred_at,
                repeat_count, latest_message, latest_event_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1302,
                "app_main",
                "process_stopped",
                "warning",
                "2026-04-12T11:05:00.100+09:00",
                "2026-04-12T11:05:40.100+09:00",
                2,
                "process still missing",
                json.dumps({"pid": 1234, "retry": 2}),
                "2026-04-12T11:05:00.200+09:00",
                "2026-04-12T11:05:40.200+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO raw_events (
                agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                1302,
                "app_main",
                "process_stopped",
                "warning",
                "process still missing",
                json.dumps({"pid": 1234, "retry": 2}),
                "2026-04-12T11:05:40.100+09:00",
                "2026-04-12T11:05:40.200+09:00",
            ),
        )
        grouped_event_id = db_conn.execute("SELECT MAX(id) AS id FROM grouped_events").fetchone()["id"]
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get(f"/api/admin/grouped-events/{grouped_event_id}/raw-events?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["grouped_event"]["id"] == grouped_event_id
    assert payload["grouped_event"]["repeat_count"] == 2
    assert len(payload["items"]) == 2
    assert payload["items"][0]["agent_id"] == "agent_local"
    assert payload["items"][0]["event"]["retry"] == 2
    assert payload["items"][0]["message"] == "process still missing"


def test_admin_grouped_event_drill_down_accepts_boundary_limits(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO grouped_events (
                monitored_object_id, target_id, event_type, severity, first_occurred_at, last_occurred_at,
                repeat_count, latest_message, latest_event_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1302,
                "app_main",
                "process_stopped",
                "warning",
                "2026-04-12T11:05:00.100+09:00",
                "2026-04-12T11:05:00.100+09:00",
                1,
                "process not found",
                json.dumps({"pid": 1234}),
                "2026-04-12T11:05:00.200+09:00",
                "2026-04-12T11:05:00.200+09:00",
            ),
        )
        grouped_event_id = db_conn.execute("SELECT MAX(id) AS id FROM grouped_events").fetchone()["id"]
        db_conn.commit()
    login(seeded_client)

    low_response = seeded_client.get(f"/api/admin/grouped-events/{grouped_event_id}/raw-events?limit=1")
    high_response = seeded_client.get(f"/api/admin/grouped-events/{grouped_event_id}/raw-events?limit=100")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 1


def test_admin_grouped_event_drill_down_rejects_invalid_limits_and_missing_group(seeded_client) -> None:
    login(seeded_client)

    zero_response = seeded_client.get("/api/admin/grouped-events/1/raw-events?limit=0")
    over_response = seeded_client.get("/api/admin/grouped-events/1/raw-events?limit=101")
    invalid_response = seeded_client.get("/api/admin/grouped-events/1/raw-events?limit=abc")
    missing_response = seeded_client.get("/api/admin/grouped-events/999/raw-events?limit=10")

    assert zero_response.status_code == 400
    assert over_response.status_code == 400
    assert invalid_response.status_code == 400
    assert missing_response.status_code == 404
    assert missing_response.get_json()["error"]["code"] == "not_found"


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
    assert payload["items"][0]["monitored_object_id"] == 1303
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
    assert payload["items"][0]["grouped_events_deleted"] == 1
    assert payload["items"][0]["debug_payload_logs_deleted"] == 1


def test_admin_alerts_returns_open_alerts(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE alert_instances
            SET source_rule_id = ?, acknowledged_at = ?, acknowledged_by_user_id = ?, ack_note = ?, updated_at = ?
            WHERE monitored_object_id = ?
            """,
            (
                1502,
                "2026-04-12T11:04:30.000+09:00",
                1,
                "운영자가 확인함",
                "2026-04-12T11:04:30.000+09:00",
                1303,
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/admin/alerts?limit=10&status=open")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["monitored_object_id"] == 1303
    assert payload["items"][0]["alert_code"] == "agent.warning"
    assert payload["items"][0]["runtime_binding_key"] == "agent_local"
    assert payload["items"][0]["source_rule_id"] == 1502
    assert payload["items"][0]["source_rule_metric_key"] == "outbox_queue_depth"
    assert payload["items"][0]["source_rule_target_label"] == "MonitoringAgent"
    assert payload["items"][0]["is_acknowledged"] is True
    assert payload["items"][0]["ack_note"] == "운영자가 확인함"


def test_admin_alerts_reject_invalid_status_filter(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/alerts?status=bad")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_admin_alerts_support_acknowledged_filter(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE alert_instances
            SET acknowledged_at = ?, acknowledged_by_user_id = ?, ack_note = ?, updated_at = ?
            WHERE monitored_object_id = ?
            """,
            (
                "2026-04-12T11:04:30.000+09:00",
                1,
                "점검 예정",
                "2026-04-12T11:04:30.000+09:00",
                1303,
            ),
        )
        db_conn.commit()
    login(seeded_client)

    acknowledged_response = seeded_client.get("/api/admin/alerts?status=open&is_acknowledged=true")
    unacknowledged_response = seeded_client.get("/api/admin/alerts?status=open&is_acknowledged=false")

    assert acknowledged_response.status_code == 200
    assert len(acknowledged_response.get_json()["items"]) == 1
    assert acknowledged_response.get_json()["items"][0]["is_acknowledged"] is True

    assert unacknowledged_response.status_code == 200
    assert unacknowledged_response.get_json()["items"] == []


def test_admin_alerts_reject_invalid_acknowledged_filter(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/alerts?status=open&is_acknowledged=maybe")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_admin_acknowledge_alert_accepts_boundary_note_length(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)
    ack_note = "a" * 500

    response = seeded_client.patch(
        "/api/admin/alerts/1",
        json={"acknowledged": True, "ack_note": ack_note},
    )

    assert response.status_code == 200
    payload = response.get_json()["alert"]
    assert payload["is_acknowledged"] is True
    assert payload["ack_note"] == ack_note
    assert payload["acknowledged_by_username"] == "admin"


def test_admin_acknowledge_alert_rejects_too_long_note(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.patch(
        "/api/admin/alerts/1",
        json={"acknowledged": True, "ack_note": "a" * 501},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_admin_acknowledge_alert_rejects_invalid_acknowledged_type(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.patch(
        "/api/admin/alerts/1",
        json={"acknowledged": "true"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_admin_acknowledge_alert_rejects_resolved_alert(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE alert_instances
            SET status = 'resolved', updated_at = ?
            WHERE id = 1
            """,
            ("2026-04-12T11:05:00.000+09:00",),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.patch(
        "/api/admin/alerts/1",
        json={"acknowledged": True, "ack_note": "늦게 확인"},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_unacknowledge_alert_clears_ack_fields(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE alert_instances
            SET acknowledged_at = ?, acknowledged_by_user_id = ?, ack_note = ?, updated_at = ?
            WHERE id = 1
            """,
            (
                "2026-04-12T11:04:30.000+09:00",
                1,
                "기존 메모",
                "2026-04-12T11:04:30.000+09:00",
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.patch(
        "/api/admin/alerts/1",
        json={"acknowledged": False},
    )

    assert response.status_code == 200
    payload = response.get_json()["alert"]
    assert payload["is_acknowledged"] is False
    assert payload["acknowledged_at"] is None
    assert payload["acknowledged_by_user_id"] is None
    assert payload["ack_note"] is None


def test_admin_alert_history_tracks_ack_and_status_changes(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    ack_response = seeded_client.patch(
        "/api/admin/alerts/1",
        json={"acknowledged": True, "ack_note": "운영자가 확인함"},
    )
    status_response = seeded_client.patch(
        "/api/admin/alerts/1/status",
        json={"status": "in_progress", "status_note": "조사중"},
    )
    history_response = seeded_client.get("/api/admin/alerts/1/history?limit=10")

    assert ack_response.status_code == 200
    assert status_response.status_code == 200
    assert history_response.status_code == 200

    payload = history_response.get_json()
    assert len(payload["items"]) == 2
    assert payload["items"][0]["action_type"] == "status_changed"
    assert payload["items"][0]["previous_status"] == "open"
    assert payload["items"][0]["new_status"] == "in_progress"
    assert payload["items"][0]["performed_by_username"] == "admin"
    assert payload["items"][0]["note"] == "조사중"
    assert payload["items"][1]["action_type"] == "acknowledged"
    assert payload["items"][1]["previous_acknowledged"] is False
    assert payload["items"][1]["new_acknowledged"] is True
    assert payload["items"][1]["note"] == "운영자가 확인함"
    assert payload["items"][1]["payload"]["source"] == "admin"


def test_admin_alert_history_accepts_boundary_limits_and_rejects_invalid_values(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)
    seeded_client.patch(
        "/api/admin/alerts/1",
        json={"acknowledged": True, "ack_note": "운영자가 확인함"},
    )

    low_response = seeded_client.get("/api/admin/alerts/1/history?limit=1")
    high_response = seeded_client.get("/api/admin/alerts/1/history?limit=100")
    zero_response = seeded_client.get("/api/admin/alerts/1/history?limit=0")
    over_response = seeded_client.get("/api/admin/alerts/1/history?limit=101")
    invalid_response = seeded_client.get("/api/admin/alerts/1/history?limit=abc")
    missing_response = seeded_client.get("/api/admin/alerts/999/history?limit=10")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 1
    assert zero_response.status_code == 400
    assert over_response.status_code == 400
    assert invalid_response.status_code == 400
    assert missing_response.status_code == 404
    assert missing_response.get_json()["error"]["code"] == "not_found"


def test_admin_manual_resolve_archives_alert_and_returns_summary(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": "운영자가 수동 종료"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["alert"]["status"] == "resolved"
    assert payload["alert"]["resolved_by_username"] == "admin"
    assert payload["archive"]["alert_code"] == "agent.warning"
    assert payload["archive"]["resolution_source"] == "manual_operator"
    assert payload["archive"]["resolution_reason"] == "운영자가 수동 종료"
    assert payload["archive"]["was_acknowledged"] is False

    with seeded_app.app_context():
        db_conn = get_db()
        archive_rows = db_conn.execute(
            """
            SELECT resolution_source, resolution_reason, final_status
            FROM alert_history_archive
            ORDER BY id DESC
            """
        ).fetchall()
        assert len(archive_rows) == 1
        assert archive_rows[0]["resolution_source"] == "manual_operator"
        assert archive_rows[0]["resolution_reason"] == "운영자가 수동 종료"
        assert archive_rows[0]["final_status"] == "resolved"


def test_admin_manual_resolve_accepts_and_rejects_boundary_reason_lengths(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    ok_response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": "a" * 500},
    )
    too_long_response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": "a" * 501},
    )

    assert ok_response.status_code == 200
    assert too_long_response.status_code == 400
    assert too_long_response.get_json()["error"]["code"] == "validation_error"


def test_admin_manual_resolve_rejects_missing_reason_and_already_resolved(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    missing_reason_response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": ""},
    )
    first_resolve_response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": "1차 수동 종료"},
    )
    second_resolve_response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": "2차 수동 종료"},
    )

    assert missing_reason_response.status_code == 400
    assert missing_reason_response.get_json()["error"]["code"] == "validation_error"
    assert first_resolve_response.status_code == 200
    assert second_resolve_response.status_code == 409
    assert second_resolve_response.get_json()["error"]["code"] == "invalid_state"


def test_admin_alert_history_archive_accepts_boundary_limits_and_filters(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)
    seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": "운영자가 수동 종료"},
    )

    low_response = seeded_client.get("/api/admin/alert-history?limit=1")
    high_response = seeded_client.get("/api/admin/alert-history?limit=100")
    zero_response = seeded_client.get("/api/admin/alert-history?limit=0")
    over_response = seeded_client.get("/api/admin/alert-history?limit=101")
    invalid_response = seeded_client.get("/api/admin/alert-history?limit=abc")
    filtered_response = seeded_client.get("/api/admin/alert-history?limit=10&resolution_source=manual_operator")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 1
    assert zero_response.status_code == 400
    assert over_response.status_code == 400
    assert invalid_response.status_code == 400
    assert filtered_response.status_code == 200
    assert filtered_response.get_json()["items"][0]["resolution_source"] == "manual_operator"


def test_admin_alerts_support_active_and_resolved_status_filters(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE alert_instances
            SET status = 'in_progress', status_updated_at = ?, status_updated_by_user_id = ?, status_note = ?, updated_at = ?
            WHERE id = 1
            """,
            (
                "2026-04-12T11:04:30.000+09:00",
                1,
                "investigating",
                "2026-04-12T11:04:30.000+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO alert_instances (
                monitored_object_id, alert_code, severity, status, status_updated_at, status_updated_by_user_id,
                status_note, resolved_at, resolved_by_user_id,
                first_occurred_at, last_occurred_at, repeat_count, latest_message, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1302,
                "process.warning",
                "warning",
                "resolved",
                "2026-04-12T11:06:00.000+09:00",
                1,
                "resolved note",
                "2026-04-12T11:06:00.000+09:00",
                1,
                "2026-04-12T11:05:00.000+09:00",
                "2026-04-12T11:05:30.000+09:00",
                1,
                "resolved message",
                json.dumps({"state": "up"}),
                "2026-04-12T11:05:00.000+09:00",
                "2026-04-12T11:06:00.000+09:00",
            ),
        )
        db_conn.commit()
    login(seeded_client)

    active_response = seeded_client.get("/api/admin/alerts?status=active")
    resolved_response = seeded_client.get("/api/admin/alerts?status=resolved")

    assert active_response.status_code == 200
    assert len(active_response.get_json()["items"]) == 1
    assert active_response.get_json()["items"][0]["status"] == "in_progress"

    assert resolved_response.status_code == 200
    assert len(resolved_response.get_json()["items"]) == 1
    assert resolved_response.get_json()["items"][0]["status"] == "resolved"


def test_admin_update_alert_status_accepts_boundary_note_length(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.patch(
        "/api/admin/alerts/1/status",
        json={"status": "in_progress", "status_note": "a" * 500},
    )

    assert response.status_code == 200
    payload = response.get_json()["alert"]
    assert payload["status"] == "in_progress"
    assert payload["status_note"] == "a" * 500
    assert payload["status_updated_by_username"] == "admin"


def test_admin_update_alert_status_rejects_invalid_values(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    invalid_status_response = seeded_client.patch(
        "/api/admin/alerts/1/status",
        json={"status": "unknown"},
    )
    too_long_note_response = seeded_client.patch(
        "/api/admin/alerts/1/status",
        json={"status": "suppressed", "status_note": "a" * 501},
    )

    assert invalid_status_response.status_code == 400
    assert invalid_status_response.get_json()["error"]["code"] == "validation_error"
    assert too_long_note_response.status_code == 400
    assert too_long_note_response.get_json()["error"]["code"] == "validation_error"


def test_admin_update_alert_status_resolves_and_reopens_alert(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    resolve_response = seeded_client.patch(
        "/api/admin/alerts/1/status",
        json={"status": "resolved", "status_note": "done"},
    )
    reopen_response = seeded_client.patch(
        "/api/admin/alerts/1/status",
        json={"status": "open", "status_note": "reopened"},
    )

    assert resolve_response.status_code == 200
    resolved_payload = resolve_response.get_json()["alert"]
    assert resolved_payload["status"] == "resolved"
    assert resolved_payload["resolved_by_username"] == "admin"
    assert resolved_payload["resolved_at"] is not None

    assert reopen_response.status_code == 200
    reopened_payload = reopen_response.get_json()["alert"]
    assert reopened_payload["status"] == "open"
    assert reopened_payload["status_note"] == "reopened"
    assert reopened_payload["resolved_at"] is None


def test_admin_alert_rules_lists_seeded_rules(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/alert-rules")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 3
    assert {item["metric_key"] for item in payload["items"]} == {
        "cpu_usage",
        "outbox_queue_depth",
        "memory_used_ratio",
    }
    assert {item["status"] for item in payload["items"]} == {"published"}
    assert all(item["is_editable"] is False for item in payload["items"])
    assert all(item["publish_warnings"] == [] for item in payload["items"])


def test_admin_alert_rules_support_filters(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/alert-rules?scope_type=object_type&state_type=process&is_enabled=true")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["metric_key"] == "cpu_usage"


def test_admin_alert_rules_support_object_type_filter(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/alert-rules?object_type=MonitoringAgent")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["metric_key"] == "outbox_queue_depth"
    assert payload["items"][0]["target_display_name"] is None


def test_admin_alert_rules_reject_invalid_filter_boundary(seeded_client) -> None:
    login(seeded_client)

    scope_response = seeded_client.get("/api/admin/alert-rules?scope_type=bad")
    state_response = seeded_client.get("/api/admin/alert-rules?state_type=bad")
    enabled_response = seeded_client.get("/api/admin/alert-rules?is_enabled=maybe")

    assert scope_response.status_code == 400
    assert state_response.status_code == 400
    assert enabled_response.status_code == 400
    assert enabled_response.get_json()["error"]["code"] == "validation_error"


def test_admin_alert_rule_targets_preview_returns_matching_objects(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/alert-rules/1501/targets-preview?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["preview_source"] == "saved_rule"
    assert payload["rule"]["id"] == 1501
    assert payload["validation"] == {"errors": [], "warnings": []}
    assert payload["summary"] == {
        "matched_object_count": 1,
        "active_view_count": 1,
        "active_node_count": 1,
        "open_alert_count": 0,
        "source_rule_open_alert_count": 0,
        "metric_available_count": 0,
        "warning_match_count": 0,
        "critical_match_count": 0,
    }
    assert len(payload["items"]) == 1
    assert payload["items"][0]["display_name"] == "App Process"
    assert payload["items"][0]["object_type"] == "SoftwareProcess"
    assert payload["items"][0]["active_view_count"] == 1
    assert payload["items"][0]["active_node_count"] == 1
    assert payload["items"][0]["current_metric_value"] is None
    assert payload["items"][0]["threshold_level"] == "unknown"


def test_admin_alert_rule_targets_preview_includes_current_alert_impact(seeded_app, seeded_client) -> None:
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO latest_states (
                view_node_id, monitored_object_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                102,
                1302,
                "app_main",
                "process",
                "warning",
                "warning",
                json.dumps({"cpu_usage": 88.0}),
                "2026-04-12T11:10:00.000+09:00",
                "2026-04-12T11:10:00.100+09:00",
                "2026-04-12T11:10:00.100+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO alert_instances (
                monitored_object_id, alert_code, source_rule_id, severity, status, first_occurred_at, last_occurred_at,
                repeat_count, latest_message, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1302,
                "rule.1501",
                1501,
                "warning",
                "open",
                "2026-04-12T11:10:00.000+09:00",
                "2026-04-12T11:10:00.000+09:00",
                1,
                "cpu warning",
                json.dumps({"metric_key": "cpu_usage"}),
                "2026-04-12T11:10:00.100+09:00",
                "2026-04-12T11:10:00.100+09:00",
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/admin/alert-rules/1501/targets-preview?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["open_alert_count"] == 1
    assert payload["summary"]["source_rule_open_alert_count"] == 1
    assert payload["summary"]["warning_match_count"] == 1
    assert payload["summary"]["critical_match_count"] == 0
    assert payload["items"][0]["current_metric_value"] == 88.0
    assert payload["items"][0]["threshold_level"] == "warning"
    assert payload["items"][0]["source_rule_open_alert_count"] == 1


def test_admin_alert_rule_targets_preview_accepts_boundary_limits(seeded_client) -> None:
    login(seeded_client)

    low_response = seeded_client.get("/api/admin/alert-rules/1501/targets-preview?limit=1")
    high_response = seeded_client.get("/api/admin/alert-rules/1501/targets-preview?limit=100")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 1


def test_admin_alert_rule_targets_preview_rejects_invalid_limits_and_missing_rule(seeded_client) -> None:
    login(seeded_client)

    zero_response = seeded_client.get("/api/admin/alert-rules/1501/targets-preview?limit=0")
    over_response = seeded_client.get("/api/admin/alert-rules/1501/targets-preview?limit=101")
    invalid_response = seeded_client.get("/api/admin/alert-rules/1501/targets-preview?limit=abc")
    missing_response = seeded_client.get("/api/admin/alert-rules/9999/targets-preview?limit=10")

    assert zero_response.status_code == 400
    assert over_response.status_code == 400
    assert invalid_response.status_code == 400
    assert missing_response.status_code == 404


def test_admin_alert_rule_preview_accepts_unsaved_draft_payload(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules/preview?limit=20",
        json={
            "status": "draft",
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "warning_threshold": 80,
            "critical_threshold": 95,
            "display_name": "Preview CPU High",
            "rule_key": "threshold.process.cpu_usage.preview-cpu-high",
            "is_enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["preview_source"] == "draft_preview"
    assert payload["rule"]["display_name"] == "Preview CPU High"
    assert payload["rule"]["status"] == "draft"
    assert payload["validation"] == {"errors": [], "warnings": []}
    assert payload["summary"]["matched_object_count"] == 1
    assert payload["items"][0]["display_name"] == "App Process"


def test_admin_alert_rule_preview_returns_validation_errors_without_failing_request(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules/preview?limit=20",
        json={
            "status": "draft",
            "scope_type": "object_type",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "warning_threshold": 80,
            "critical_threshold": 95,
            "display_name": "Broken Preview",
            "rule_key": "threshold.process.cpu_usage.broken-preview",
            "is_enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["preview_source"] == "draft_preview"
    assert payload["validation"]["warnings"] == []
    assert payload["validation"]["errors"] == [{"message": "object_type is required for object_type scope"}]
    assert payload["summary"]["matched_object_count"] == 0
    assert payload["items"] == []


def test_admin_alert_rule_preview_returns_publish_warnings(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules/preview?limit=20",
        json={
            "status": "draft",
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "warning_threshold": 80,
            "critical_threshold": None,
            "display_name": "Preview CPU High (Copy)",
            "rule_key": "threshold.process.cpu_usage.preview-cpu-high-copy",
            "is_enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["validation"]["errors"] == []
    assert payload["validation"]["warnings"] == [
        {"message": "This rule only emits a single severity level."},
        {"message": "display_name still contains the '(Copy)' suffix."},
    ]
    assert payload["summary"]["matched_object_count"] == 1


def test_admin_monitored_objects_support_filters_and_counts(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/admin/monitored-objects?limit=10&object_type=MonitoringAgent&query=Local")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["display_name"] == "Local Agent"
    assert payload["items"][0]["active_view_count"] == 1
    assert payload["items"][0]["active_node_count"] == 1
    assert payload["items"][0]["open_alert_count"] == 1


def test_admin_monitored_objects_accept_boundary_limits(seeded_client) -> None:
    login(seeded_client)

    low_response = seeded_client.get("/api/admin/monitored-objects?limit=1")
    high_response = seeded_client.get("/api/admin/monitored-objects?limit=100")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 4


def test_admin_monitored_objects_reject_out_of_range_limits(seeded_client) -> None:
    login(seeded_client)

    zero_response = seeded_client.get("/api/admin/monitored-objects?limit=0")
    over_response = seeded_client.get("/api/admin/monitored-objects?limit=101")
    invalid_response = seeded_client.get("/api/admin/monitored-objects?limit=abc")

    assert zero_response.status_code == 400
    assert over_response.status_code == 400
    assert invalid_response.status_code == 400
    assert invalid_response.get_json()["error"]["code"] == "validation_error"


def test_admin_create_alert_rule_accepts_valid_object_type_rule(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "memory_rss",
            "comparison": "gte",
            "warning_threshold": 1024,
            "critical_threshold": 2048,
            "is_enabled": True,
            "description": "RSS 임계치",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["rule"]
    assert payload["status"] == "draft"
    assert payload["is_editable"] is True
    assert payload["rule_key"].startswith("threshold.process.memory_rss.")
    assert payload["scope_type"] == "object_type"
    assert payload["warning_threshold"] == 1024
    assert payload["critical_threshold"] == 2048
    assert payload["display_name"] is not None


def test_admin_update_alert_rule_rejects_semantic_edit_for_published_rule(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.patch(
        "/api/admin/alert-rules/1501",
        json={
            "description": "프로세스 CPU 경계값 수정",
            "critical_threshold": 96,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"] == "published rule conditions cannot be edited; clone the rule to create a new draft"


def test_admin_update_alert_rule_allows_enabled_toggle_for_published_rule(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.patch("/api/admin/alert-rules/1501", json={"is_enabled": False})

    assert response.status_code == 200
    payload = response.get_json()["rule"]
    assert payload["id"] == 1501
    assert payload["status"] == "published"
    assert payload["is_enabled"] is False
    assert payload["publish_warnings"] == []


def test_admin_clone_alert_rule_creates_disabled_draft_copy(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post("/api/admin/alert-rules/1501/clone")

    assert response.status_code == 201
    payload = response.get_json()["rule"]
    assert payload["status"] == "draft"
    assert payload["is_editable"] is True
    assert payload["is_enabled"] is False
    assert payload["rule_key"] == "threshold.process.cpu_usage.process-cpu-high-2"
    assert payload["display_name"] == "Process CPU High (Copy)"
    assert payload["publish_warnings"] == [{"message": "display_name still contains the '(Copy)' suffix."}]


def test_admin_publish_alert_rule_accepts_warnings_but_publishes_draft(seeded_client) -> None:
    login(seeded_client)

    create_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "rss_mb",
            "comparison": "gte",
            "warning_threshold": 1024,
            "critical_threshold": None,
            "display_name": "RSS High (Copy)",
            "rule_key": "threshold.process.rss_mb.rss-high-copy",
            "is_enabled": True,
        },
    )
    assert create_response.status_code == 201
    rule_id = create_response.get_json()["rule"]["id"]

    publish_response = seeded_client.post(f"/api/admin/alert-rules/{rule_id}/publish")

    assert publish_response.status_code == 200
    payload = publish_response.get_json()
    assert payload["rule"]["status"] == "published"
    assert payload["validation"]["errors"] == []
    assert len(payload["validation"]["warnings"]) == 2


def test_admin_alert_rule_rejects_duplicate_rule_key(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "rss_mb",
            "comparison": "gte",
            "warning_threshold": 1024,
            "critical_threshold": 2048,
            "display_name": "RSS High",
            "rule_key": "threshold.process.cpu_usage.process-cpu-high",
            "is_enabled": True,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["message"] == "rule_key must be unique across all alert rules"


def test_admin_alert_rule_rejects_missing_thresholds(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "warning_threshold": None,
            "critical_threshold": None,
            "is_enabled": True,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_admin_alert_rule_rejects_invalid_monitored_object_scope_boundary(seeded_client) -> None:
    login(seeded_client)

    wrong_type = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "monitored_object",
            "monitored_object_id": "1302",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "warning_threshold": 80,
            "critical_threshold": 95,
            "is_enabled": True,
        },
    )
    missing_row = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "monitored_object",
            "monitored_object_id": 999999,
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "warning_threshold": 80,
            "critical_threshold": 95,
            "is_enabled": True,
        },
    )

    assert wrong_type.status_code == 400
    assert missing_row.status_code == 400
    assert wrong_type.get_json()["error"]["code"] == "validation_error"
    assert missing_row.get_json()["error"]["code"] == "validation_error"


def test_admin_alert_rule_rejects_invalid_threshold_order_for_gte_and_lte(seeded_client) -> None:
    login(seeded_client)

    gte_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "warning_threshold": 90,
            "critical_threshold": 80,
            "is_enabled": True,
        },
    )
    lte_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "HostSnapshot",
            "state_type": "host",
            "metric_key": "memory_available",
            "comparison": "lte",
            "warning_threshold": 20,
            "critical_threshold": 30,
            "is_enabled": True,
        },
    )

    assert gte_response.status_code == 400
    assert lte_response.status_code == 400
    assert gte_response.get_json()["error"]["code"] == "validation_error"
    assert lte_response.get_json()["error"]["code"] == "validation_error"
