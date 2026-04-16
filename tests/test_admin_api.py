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
    assert payload["items"][0]["debug_payload_logs_deleted"] == 1


def test_admin_alerts_returns_open_alerts(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/admin/alerts?limit=10&status=open")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["monitored_object_id"] == 1303
    assert payload["items"][0]["alert_code"] == "agent.warning"
    assert payload["items"][0]["runtime_binding_key"] == "agent_local"


def test_admin_alerts_reject_invalid_status_filter(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/alerts?status=bad")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


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
    assert payload["scope_type"] == "object_type"
    assert payload["warning_threshold"] == 1024
    assert payload["critical_threshold"] == 2048


def test_admin_update_alert_rule_accepts_existing_integer_enabled_value(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.patch(
        "/api/admin/alert-rules/1501",
        json={
            "description": "프로세스 CPU 경계값 수정",
            "critical_threshold": 96,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()["rule"]
    assert payload["id"] == 1501
    assert payload["critical_threshold"] == 96
    assert payload["is_enabled"] is True


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
