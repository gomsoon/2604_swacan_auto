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
                "operator ack note",
                "2026-04-12T11:04:30.000+09:00",
                1303,
            ),
        )
        db_conn.execute(
            """
            UPDATE alert_instances
            SET opening_rule_id = ?, opening_rule_key = ?, opening_rule_display_name_snapshot = ?,
                winner_transition_count = ?, last_winner_transition_at = ?
            WHERE monitored_object_id = ?
            """,
            (
                1502,
                "threshold.agent.outbox_queue_depth.agent-queue-high",
                "Agent Queue High",
                2,
                "2026-04-12T11:04:15.000+09:00",
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
    assert payload["items"][0]["source_rule_key"] == "threshold.agent.outbox_queue_depth.agent-queue-high"
    assert payload["items"][0]["source_rule_display_name_snapshot"] == "Agent Queue High"
    assert payload["items"][0]["opening_rule_id"] == 1502
    assert payload["items"][0]["opening_rule_key"] == "threshold.agent.outbox_queue_depth.agent-queue-high"
    assert payload["items"][0]["opening_rule_display_name_snapshot"] == "Agent Queue High"
    assert payload["items"][0]["winner_transition_count"] == 2
    assert payload["items"][0]["last_winner_transition_at"] == "2026-04-12T11:04:15.000+09:00"
    assert payload["items"][0]["source_rule_metric_key"] == "outbox_queue_depth"
    assert payload["items"][0]["source_rule_target_label"] == "MonitoringAgent"
    assert payload["items"][0]["is_acknowledged"] is True
    assert payload["items"][0]["ack_note"] == "operator ack note"
    assert payload["items"][0]["winner_transition_summary"] == {
        "opening_rule": {
            "id": 1502,
            "rule_key": "threshold.agent.outbox_queue_depth.agent-queue-high",
            "display_name": "Agent Queue High",
        },
        "winner_rule": {
            "id": 1502,
            "rule_key": "threshold.agent.outbox_queue_depth.agent-queue-high",
            "display_name": "Agent Queue High",
        },
        "transition_count": 2,
        "last_transition_at": "2026-04-12T11:04:15.000+09:00",
    }
    assert payload["items"][0]["explanation"]["reason"] == "heartbeat delayed"
    assert payload["items"][0]["explanation"]["suppressed_rule_display_names"] == []


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
                "planned maintenance",
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
        json={"acknowledged": True, "ack_note": "late acknowledgement"},
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
                "existing note",
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
        json={"acknowledged": True, "ack_note": "operator ack note"},
    )
    status_response = seeded_client.patch(
        "/api/admin/alerts/1/status",
        json={"status": "in_progress", "status_note": "investigating"},
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
    assert payload["items"][0]["note"] == "investigating"
    assert payload["items"][1]["action_type"] == "acknowledged"
    assert payload["items"][1]["previous_acknowledged"] is False
    assert payload["items"][1]["new_acknowledged"] is True
    assert payload["items"][1]["note"] == "operator ack note"
    assert payload["items"][1]["payload"]["source"] == "admin"


def test_admin_alert_history_accepts_boundary_limits_and_rejects_invalid_values(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)
    seeded_client.patch(
        "/api/admin/alerts/1",
        json={"acknowledged": True, "ack_note": "operator ack note"},
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
        json={"resolution_reason": "operator manual resolve"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["alert"]["status"] == "resolved"
    assert payload["alert"]["resolved_by_username"] == "admin"
    assert payload["archive"]["alert_code"] == "agent.warning"
    assert payload["archive"]["resolution_source"] == "manual_operator"
    assert payload["archive"]["resolution_reason"] == "manual_resolved"
    assert payload["archive"]["resolution_note"]
    assert payload["archive"]["source_rule_key"] is None
    assert payload["archive"]["source_rule_display_name_snapshot"] is None
    assert payload["archive"]["was_acknowledged"] is False

    with seeded_app.app_context():
        db_conn = get_db()
        archive_rows = db_conn.execute(
            """
            SELECT resolution_source, resolution_reason, final_status,
                   source_rule_key, source_rule_display_name_snapshot
            FROM alert_history_archive
            ORDER BY id DESC
            """
        ).fetchall()
        assert len(archive_rows) == 1
        assert archive_rows[0]["resolution_source"] == "manual_operator"
        assert archive_rows[0]["resolution_reason"] == "manual_resolved"
        assert archive_rows[0]["final_status"] == "resolved"
        assert archive_rows[0]["source_rule_key"] is None
        assert archive_rows[0]["source_rule_display_name_snapshot"] is None


def test_admin_manual_resolve_accepts_and_rejects_boundary_reason_lengths(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)

    ok_response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_note": "a" * 500},
    )
    too_long_response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_note": "a" * 501},
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
        json={"resolution_reason": "first manual resolve"},
    )
    second_resolve_response = seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": "second manual resolve"},
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
        json={"resolution_reason": "operator manual resolve"},
    )

    low_response = seeded_client.get("/api/admin/alert-history?limit=1")
    high_response = seeded_client.get("/api/admin/alert-history?limit=100")
    zero_response = seeded_client.get("/api/admin/alert-history?limit=0")
    over_response = seeded_client.get("/api/admin/alert-history?limit=101")
    invalid_response = seeded_client.get("/api/admin/alert-history?limit=abc")
    filtered_response = seeded_client.get("/api/admin/alert-archive?limit=10&resolution_source=manual_operator")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 1
    assert zero_response.status_code == 400
    assert over_response.status_code == 400
    assert invalid_response.status_code == 400
    assert filtered_response.status_code == 200
    assert filtered_response.get_json()["items"][0]["resolution_source"] == "manual_operator"


def test_admin_alert_archive_alias_supports_legacy_history_route(seeded_app, seeded_client) -> None:
    seed_admin_dashboard_rows(seeded_app)
    login(seeded_client)
    seeded_client.post(
        "/api/admin/alerts/1/resolve",
        json={"resolution_reason": "operator manual resolve"},
    )

    response = seeded_client.get("/api/admin/alert-history?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["resolution_reason"] == "manual_resolved"


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
    resolve_archive = resolve_response.get_json()["archive"]
    resolved_payload = resolve_response.get_json()["alert"]
    assert resolved_payload["status"] == "resolved"
    assert resolved_payload["resolved_by_username"] == "admin"
    assert resolved_payload["resolved_at"] is not None
    assert resolve_archive["resolution_reason"] == "resolved_from_status_api"
    assert resolve_archive["resolution_note"] == "done"

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
    assert payload["rule"]["condition_mode"] == "scalar"
    assert payload["rule"]["warning_condition"] == {
        "logical_operator": None,
        "clauses": [{"comparison": "gte", "value": 80.0}],
    }
    assert payload["rule"]["critical_condition"] == {
        "logical_operator": None,
        "clauses": [{"comparison": "gte", "value": 95.0}],
    }
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
    assert payload["decision_summary"] == {
        "candidate_rule_count": 1,
        "published_competing_rule_count": 0,
        "items_with_suppression_count": 0,
    }
    assert len(payload["items"]) == 1
    assert payload["items"][0]["display_name"] == "App Process"
    assert payload["items"][0]["object_type"] == "SoftwareProcess"
    assert payload["items"][0]["active_view_count"] == 1
    assert payload["items"][0]["active_node_count"] == 1
    assert payload["items"][0]["current_metric_value"] is None
    assert payload["items"][0]["threshold_level"] == "unknown"
    assert payload["items"][0]["winning_condition_trace"] is None
    assert payload["items"][0]["candidate_rule_count"] == 1
    assert payload["items"][0]["winner_display_name"] is None
    assert payload["items"][0]["winner_rule_origin"] is None
    assert payload["items"][0]["suppressed_rule_count"] == 0
    assert payload["items"][0]["suppressed_rule_display_names"] == []


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
    assert payload["items"][0]["winning_condition_trace"] == {
        "severity": "warning",
        "condition_mode": "scalar",
        "logical_operator": None,
        "matched_clause_indexes": [0],
    }
    assert payload["items"][0]["winner_display_name"] == "Process CPU High"
    assert payload["items"][0]["winner_rule_origin"] == "current_preview"
    assert payload["items"][0]["winner_threshold_level"] == "warning"
    assert payload["items"][0]["suppressed_rule_count"] == 0
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
    assert payload["rule"]["condition_mode"] == "scalar"
    assert payload["rule"]["warning_condition"] == {
        "logical_operator": None,
        "clauses": [{"comparison": "gte", "value": 80.0}],
    }
    assert payload["rule"]["critical_condition"] == {
        "logical_operator": None,
        "clauses": [{"comparison": "gte", "value": 95.0}],
    }
    assert payload["validation"] == {"errors": [], "warnings": []}
    assert payload["summary"]["matched_object_count"] == 1
    assert payload["items"][0]["display_name"] == "App Process"


def test_admin_alert_rule_preview_normalizes_compound_condition_shape(seeded_client) -> None:
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
            "display_name": "Preview CPU Band",
            "rule_key": "threshold.process.cpu_usage.preview-cpu-band",
            "is_enabled": True,
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 20},
                    {"comparison": "gte", "value": 80},
                ],
            },
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 10},
                    {"comparison": "gte", "value": 90},
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["rule"]["condition_mode"] == "compound"
    assert payload["rule"]["warning_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 20.0},
            {"comparison": "gte", "value": 80.0},
        ],
    }
    assert payload["rule"]["critical_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 10.0},
            {"comparison": "gte", "value": 90.0},
        ],
    }
    assert payload["summary"]["matched_object_count"] == 1


def test_admin_alert_rule_preview_returns_compound_or_winning_trace(seeded_app, seeded_client) -> None:
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
                "critical",
                "critical",
                json.dumps({"cpu_usage": 97.0}),
                "2026-04-12T11:15:00.000+09:00",
                "2026-04-12T11:15:00.100+09:00",
                "2026-04-12T11:15:00.100+09:00",
            ),
        )
        db_conn.commit()
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
            "display_name": "Preview CPU Band",
            "rule_key": "threshold.process.cpu_usage.preview-cpu-band",
            "is_enabled": True,
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 20},
                    {"comparison": "gte", "value": 80},
                ],
            },
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 10},
                    {"comparison": "gte", "value": 90},
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["validation"]["errors"] == []
    assert payload["summary"]["warning_match_count"] == 1
    assert payload["summary"]["critical_match_count"] == 1
    assert payload["decision_summary"] == {
        "candidate_rule_count": 2,
        "published_competing_rule_count": 1,
        "items_with_suppression_count": 1,
    }
    assert payload["items"][0]["current_metric_value"] == 97.0
    assert payload["items"][0]["threshold_level"] == "critical"
    assert payload["items"][0]["winning_condition_trace"] == {
        "severity": "critical",
        "condition_mode": "compound",
        "logical_operator": "or",
        "matched_clause_indexes": [1],
    }
    assert payload["items"][0]["winner_display_name"] == "Preview CPU Band"
    assert payload["items"][0]["winner_rule_origin"] == "current_preview"
    assert payload["items"][0]["winner_threshold_level"] == "critical"
    assert payload["items"][0]["suppressed_rule_count"] == 1
    assert payload["items"][0]["suppressed_rule_keys"] == ["threshold.process.cpu_usage.process-cpu-high"]
    assert payload["items"][0]["suppressed_rule_display_names"] == ["Process CPU High"]
    assert payload["items"][0]["explanation"] == {
        "rule_key": "threshold.process.cpu_usage.preview-cpu-band",
        "display_name": "Preview CPU Band",
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
        "winner_rule_key": "threshold.process.cpu_usage.preview-cpu-band",
        "winner_display_name": "Preview CPU Band",
        "suppressed_rule_keys": ["threshold.process.cpu_usage.process-cpu-high"],
        "suppressed_rule_display_names": ["Process CPU High"],
        "resolution_reason": None,
    }


def test_admin_alert_rule_preview_returns_compound_and_winning_trace(seeded_app, seeded_client) -> None:
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
                json.dumps({"cpu_usage": 52.0}),
                "2026-04-12T11:16:00.000+09:00",
                "2026-04-12T11:16:00.100+09:00",
                "2026-04-12T11:16:00.100+09:00",
            ),
        )
        db_conn.commit()
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
            "warning_threshold": 40,
            "critical_threshold": None,
            "display_name": "Preview CPU Window",
            "rule_key": "threshold.process.cpu_usage.preview-cpu-window",
            "is_enabled": True,
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "and",
                "clauses": [
                    {"comparison": "gte", "value": 40},
                    {"comparison": "lte", "value": 60},
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["validation"]["errors"] == []
    assert {"message": "This rule only emits a single severity level."} in payload["validation"]["warnings"]
    assert payload["summary"]["warning_match_count"] == 1
    assert payload["summary"]["critical_match_count"] == 0
    assert payload["items"][0]["current_metric_value"] == 52.0
    assert payload["items"][0]["threshold_level"] == "warning"
    assert payload["items"][0]["winning_condition_trace"] == {
        "severity": "warning",
        "condition_mode": "compound",
        "logical_operator": "and",
        "matched_clause_indexes": [0, 1],
    }
    assert payload["items"][0]["winner_display_name"] == "Preview CPU Window"
    assert payload["items"][0]["winner_rule_origin"] == "current_preview"
    assert payload["items"][0]["winner_threshold_level"] == "warning"
    assert payload["items"][0]["suppressed_rule_count"] == 0
    assert payload["items"][0]["explanation"]["reason"] == "cpu_usage=52.000 matched warning condition (and, clauses 1, 2)"
    assert payload["items"][0]["explanation"]["winner_rule_key"] == "threshold.process.cpu_usage.preview-cpu-window"
    assert payload["items"][0]["explanation"]["suppressed_rule_keys"] == []


def test_admin_alert_rule_preview_rejects_invalid_compound_shape_without_failing_request(seeded_client) -> None:
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
            "display_name": "Broken Compound Preview",
            "rule_key": "threshold.process.cpu_usage.broken-compound-preview",
            "is_enabled": True,
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": None,
                "clauses": [{"comparison": "gte", "value": 80}],
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["validation"]["warnings"] == []
    assert payload["validation"]["errors"] == [
        {"message": "warning_condition logical_operator must be 'and' or 'or' in compound mode."},
        {"message": "warning_condition must define exactly 2 clauses in compound mode."},
    ]
    assert payload["summary"] == {
        "matched_object_count": 0,
        "active_view_count": 0,
        "active_node_count": 0,
        "open_alert_count": 0,
        "source_rule_open_alert_count": 0,
        "metric_available_count": 0,
        "warning_match_count": 0,
        "critical_match_count": 0,
    }
    assert payload["items"] == []


def test_admin_alert_rule_preview_rejects_compound_subset_violation(seeded_client) -> None:
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
            "display_name": "Subset Broken Preview",
            "rule_key": "threshold.process.cpu_usage.subset-broken-preview",
            "is_enabled": True,
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "gte", "value": 80},
                    {"comparison": "gte", "value": 90},
                ],
            },
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 10},
                    {"comparison": "lte", "value": 5},
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert {"message": "warning_condition contains a redundant clause."} in payload["validation"]["warnings"]
    assert {"message": "critical_condition contains a redundant clause."} in payload["validation"]["warnings"]
    assert payload["validation"]["errors"] == [{"message": "critical_condition must be a subset of warning_condition."}]
    assert payload["items"] == []


def test_admin_alert_rule_preview_returns_compound_redundancy_warning(seeded_client) -> None:
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
            "display_name": "Redundant Compound Preview",
            "rule_key": "threshold.process.cpu_usage.redundant-compound-preview",
            "is_enabled": True,
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "gte", "value": 80},
                    {"comparison": "gte", "value": 90},
                ],
            },
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "gte", "value": 95},
                    {"comparison": "gte", "value": 98},
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["validation"]["errors"] == []
    assert {"message": "warning_condition contains a redundant clause."} in payload["validation"]["warnings"]
    assert {"message": "critical_condition contains a redundant clause."} in payload["validation"]["warnings"]
    assert payload["summary"]["matched_object_count"] == 1


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


def test_admin_alert_rule_preview_reports_published_rule_winner_and_suppressed_current_rule(
    seeded_app, seeded_client
) -> None:
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
                "2026-04-12T11:18:00.000+09:00",
                "2026-04-12T11:18:00.100+09:00",
                "2026-04-12T11:18:00.100+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO alert_rules (
                id, rule_key, display_name, status, scope_type, object_type, monitored_object_id,
                state_type, metric_key, comparison, warning_threshold, critical_threshold,
                is_enabled, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                70.0,
                92.0,
                1,
                "Specific override for App Process",
                "2026-04-12T11:18:00.000+09:00",
                "2026-04-12T11:18:00.000+09:00",
            ),
        )
        db_conn.commit()
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
    assert payload["decision_summary"] == {
        "candidate_rule_count": 3,
        "published_competing_rule_count": 2,
        "items_with_suppression_count": 1,
    }
    assert payload["items"][0]["threshold_level"] == "warning"
    assert payload["items"][0]["winner_display_name"] == "App Process CPU Override"
    assert payload["items"][0]["winner_scope_type"] == "monitored_object"
    assert payload["items"][0]["winner_rule_origin"] == "published_rule"
    assert payload["items"][0]["winner_threshold_level"] == "warning"
    assert payload["items"][0]["suppressed_rule_count"] == 2
    assert payload["items"][0]["suppressed_rule_display_names"] == [
        "Preview CPU High",
        "Process CPU High",
    ]


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
            "description": "RSS threshold",
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


def test_admin_create_alert_rule_accepts_valid_grouped_event_rule(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "signal_type": "grouped_event_repeat",
            "signal_key": "process_restarted",
            "comparison": "gte",
            "warning_threshold": 2,
            "critical_threshold": 4,
            "is_enabled": True,
            "display_name": "Process Restart Burst",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["rule"]
    assert payload["status"] == "draft"
    assert payload["signal_type"] == "grouped_event_repeat"
    assert payload["signal_key"] == "process_restarted"
    assert payload["metric_key"] == "process_restarted"
    assert payload["condition_mode"] == "scalar"
    assert payload["rule_key"].startswith("event.process.process_restarted.")


def test_admin_alert_rule_preview_supports_grouped_event_repeat(seeded_app, seeded_client) -> None:
    login(seeded_client)
    current_time = datetime.now().astimezone().isoformat()

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
                "process_restarted",
                "warning",
                current_time,
                current_time,
                4,
                "process restarted repeatedly",
                json.dumps({"event_type": "process_restarted", "repeat_count": 4}),
                current_time,
                current_time,
            ),
        )
        db_conn.commit()

    response = seeded_client.post(
        "/api/admin/alert-rules/preview?limit=20",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "signal_type": "grouped_event_repeat",
            "signal_key": "process_restarted",
            "comparison": "gte",
            "warning_threshold": 2,
            "critical_threshold": 4,
            "display_name": "Process Restart Burst",
            "rule_key": "event.process.process_restarted.process-restart-burst",
            "is_enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["rule"]["signal_type"] == "grouped_event_repeat"
    assert payload["rule"]["signal_key"] == "process_restarted"
    assert payload["rule"]["metric_key"] == "process_restarted"
    assert payload["summary"]["warning_match_count"] == 1
    assert payload["summary"]["critical_match_count"] == 1
    assert payload["items"][0]["signal_type"] == "grouped_event_repeat"
    assert payload["items"][0]["signal_key"] == "process_restarted"
    assert payload["items"][0]["grouped_event_repeat_count"] == 4
    assert payload["items"][0]["current_metric_value"] == 4.0
    assert payload["items"][0]["grouped_event_latest_message"] == "process restarted repeatedly"
    assert payload["items"][0]["explanation"] == {
        "rule_key": "event.process.process_restarted.process-restart-burst",
        "display_name": "Process Restart Burst",
        "signal_type": "grouped_event_repeat",
        "value_key": "process_restarted",
        "threshold_level": "critical",
        "reason": "process_restarted repeat_count=4 >= 4",
        "winning_condition_trace": {
            "severity": "critical",
            "condition_mode": "scalar",
            "logical_operator": None,
            "matched_clause_indexes": [0],
        },
        "family_key": ["event", "process", "process_restarted", "gte"],
        "winner_rule_key": "event.process.process_restarted.process-restart-burst",
        "winner_display_name": "Process Restart Burst",
        "suppressed_rule_keys": [],
        "suppressed_rule_display_names": [],
        "resolution_reason": None,
    }


def test_admin_alert_rule_preview_supports_stale_heartbeat_threshold(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:20.100+09:00")
    seeded_app.config["AGENT_HEARTBEAT_WARNING_SECONDS"] = 10
    seeded_app.config["AGENT_HEARTBEAT_DOWN_SECONDS"] = 30
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO latest_states (
                target_id, state_type, view_node_id, monitored_object_id, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "agent_local",
                "agent",
                None,
                1303,
                "up",
                "normal",
                json.dumps(
                    {
                        "heartbeat_time": "2026-04-10T10:20:00.100+09:00",
                        "backend_connection_status": "connected",
                        "outbox_queue_depth": 0,
                    }
                ),
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.100+09:00",
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules/preview?limit=20",
        json={
            "scope_type": "object_type",
            "object_type": "MonitoringAgent",
            "state_type": "agent",
            "metric_key": "heartbeat_age_seconds",
            "comparison": "gte",
            "warning_threshold": 10,
            "critical_threshold": 30,
            "display_name": "Agent Heartbeat Stale",
            "rule_key": "threshold.agent.heartbeat_age_seconds.agent-heartbeat-stale",
            "is_enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["rule"]["signal_type"] == "latest_state_metric"
    assert payload["rule"]["metric_key"] == "heartbeat_age_seconds"
    assert payload["summary"]["warning_match_count"] == 1
    assert payload["summary"]["critical_match_count"] == 0
    assert payload["items"][0]["signal_type"] == "latest_state_metric"
    assert payload["items"][0]["current_metric_value"] == 20.0
    assert payload["items"][0]["threshold_level"] == "warning"
    assert payload["items"][0]["reason"] == "heartbeat_age_seconds=20.000 >= 10.000"
    assert payload["items"][0]["winning_condition_trace"] == {
        "severity": "warning",
        "condition_mode": "scalar",
        "logical_operator": None,
        "matched_clause_indexes": [0],
    }
    assert payload["items"][0]["explanation"] == {
        "rule_key": "threshold.agent.heartbeat_age_seconds.agent-heartbeat-stale",
        "display_name": "Agent Heartbeat Stale",
        "signal_type": "latest_state_metric",
        "value_key": "heartbeat_age_seconds",
        "threshold_level": "warning",
        "reason": "heartbeat_age_seconds=20.000 >= 10.000",
        "winning_condition_trace": {
            "severity": "warning",
            "condition_mode": "scalar",
            "logical_operator": None,
            "matched_clause_indexes": [0],
        },
        "family_key": ["threshold", "agent", "heartbeat_age_seconds", "gte"],
        "winner_rule_key": "threshold.agent.heartbeat_age_seconds.agent-heartbeat-stale",
        "winner_display_name": "Agent Heartbeat Stale",
        "suppressed_rule_keys": [],
        "suppressed_rule_display_names": [],
        "resolution_reason": None,
    }


def test_admin_alert_rule_preview_supports_no_data_latest_state_age_threshold(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:20.100+09:00")
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute("DELETE FROM latest_states WHERE monitored_object_id = ? AND state_type = ?", (1302, "process"))
        db_conn.execute(
            """
            INSERT INTO latest_states (
                target_id, state_type, view_node_id, monitored_object_id, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "app_main",
                "process",
                None,
                1302,
                "up",
                "normal",
                json.dumps({"pid": 1234, "state": "running", "cpu_usage": 10.0, "memory_rss": 4096}),
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.100+09:00",
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules/preview?limit=20",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "latest_state_age_seconds",
            "comparison": "gte",
            "warning_threshold": 10,
            "critical_threshold": 30,
            "display_name": "Process No Data",
            "rule_key": "threshold.process.latest_state_age_seconds.process-no-data",
            "is_enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["rule"]["signal_type"] == "latest_state_metric"
    assert payload["rule"]["metric_key"] == "latest_state_age_seconds"
    assert payload["summary"]["warning_match_count"] == 1
    assert payload["summary"]["critical_match_count"] == 0
    assert payload["items"][0]["current_metric_value"] == 20.0
    assert payload["items"][0]["threshold_level"] == "warning"
    assert payload["items"][0]["reason"] == "latest_state_age_seconds=20.000 >= 10.000"
    assert payload["items"][0]["explanation"] == {
        "rule_key": "threshold.process.latest_state_age_seconds.process-no-data",
        "display_name": "Process No Data",
        "signal_type": "latest_state_metric",
        "value_key": "latest_state_age_seconds",
        "threshold_level": "warning",
        "reason": "latest_state_age_seconds=20.000 >= 10.000",
        "winning_condition_trace": {
            "severity": "warning",
            "condition_mode": "scalar",
            "logical_operator": None,
            "matched_clause_indexes": [0],
        },
        "family_key": ["threshold", "process", "latest_state_age_seconds", "gte"],
        "winner_rule_key": "threshold.process.latest_state_age_seconds.process-no-data",
        "winner_display_name": "Process No Data",
        "suppressed_rule_keys": [],
        "suppressed_rule_display_names": [],
        "resolution_reason": None,
    }


def test_admin_alert_rule_rejects_invalid_no_data_rule_shape(seeded_client) -> None:
    login(seeded_client)

    agent_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "MonitoringAgent",
            "state_type": "agent",
            "metric_key": "latest_state_age_seconds",
            "comparison": "gte",
            "warning_threshold": 10,
            "is_enabled": True,
        },
    )
    compound_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "latest_state_age_seconds",
            "comparison": "gte",
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "gte", "value": 10},
                    {"comparison": "gte", "value": 20},
                ],
            },
            "warning_threshold": 10,
            "is_enabled": True,
        },
    )

    assert agent_response.status_code == 400
    assert agent_response.get_json()["error"]["message"] == "agent no-data/stale should use heartbeat_age_seconds threshold rules"
    assert compound_response.status_code == 400
    assert compound_response.get_json()["error"]["message"] == "latest_state_age_seconds currently supports only scalar condition_mode"


def test_admin_alert_rule_rejects_invalid_grouped_event_rule_shape(seeded_client) -> None:
    login(seeded_client)

    comparison_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "signal_type": "grouped_event_repeat",
            "signal_key": "process_restarted",
            "comparison": "lte",
            "warning_threshold": 1,
            "is_enabled": True,
        },
    )
    compound_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "signal_type": "grouped_event_repeat",
            "signal_key": "process_restarted",
            "comparison": "gte",
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "gte", "value": 2},
                    {"comparison": "gte", "value": 3},
                ],
            },
            "warning_threshold": 2,
            "is_enabled": True,
        },
    )

    assert comparison_response.status_code == 400
    assert comparison_response.get_json()["error"]["message"] == "event rules currently require comparison=gte"
    assert compound_response.status_code == 400
    assert compound_response.get_json()["error"]["message"] == "event rules currently support only scalar condition_mode"


def test_admin_create_alert_rule_accepts_compound_draft_rule(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 20},
                    {"comparison": "gte", "value": 80},
                ],
            },
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 10},
                    {"comparison": "gte", "value": 90},
                ],
            },
            "is_enabled": True,
            "display_name": "CPU Band",
            "rule_key": "threshold.process.cpu_usage.cpu-band",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["rule"]
    assert payload["status"] == "draft"
    assert payload["condition_mode"] == "compound"
    assert payload["warning_threshold"] is None
    assert payload["critical_threshold"] is None
    assert payload["warning_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 20.0},
            {"comparison": "gte", "value": 80.0},
        ],
    }
    assert payload["critical_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 10.0},
            {"comparison": "gte", "value": 90.0},
        ],
    }
    assert payload["publish_warnings"] == []


def test_admin_alert_rule_targets_preview_supports_saved_compound_draft(seeded_client) -> None:
    login(seeded_client)

    create_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 20},
                    {"comparison": "gte", "value": 80},
                ],
            },
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 10},
                    {"comparison": "gte", "value": 90},
                ],
            },
            "display_name": "CPU Band Saved Preview",
            "rule_key": "threshold.process.cpu_usage.cpu-band-saved-preview",
            "is_enabled": True,
        },
    )
    assert create_response.status_code == 201
    rule_id = create_response.get_json()["rule"]["id"]

    preview_response = seeded_client.get(f"/api/admin/alert-rules/{rule_id}/targets-preview?limit=10")

    assert preview_response.status_code == 200
    payload = preview_response.get_json()
    assert payload["preview_source"] == "saved_rule"
    assert payload["rule"]["condition_mode"] == "compound"
    assert payload["validation"]["errors"] == []
    assert payload["rule"]["warning_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 20.0},
            {"comparison": "gte", "value": 80.0},
        ],
    }


def test_admin_update_alert_rule_rejects_semantic_edit_for_published_rule(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.patch(
        "/api/admin/alert-rules/1501",
        json={
            "description": "Process CPU threshold update",
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


def test_admin_update_alert_rule_accepts_compound_draft_changes(seeded_client) -> None:
    login(seeded_client)

    create_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "warning_threshold": 80,
            "critical_threshold": 95,
            "display_name": "CPU High Draft",
            "rule_key": "threshold.process.cpu_usage.cpu-high-draft",
            "is_enabled": True,
        },
    )
    assert create_response.status_code == 201
    rule_id = create_response.get_json()["rule"]["id"]

    update_response = seeded_client.patch(
        f"/api/admin/alert-rules/{rule_id}",
        json={
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 20},
                    {"comparison": "gte", "value": 80},
                ],
            },
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 10},
                    {"comparison": "gte", "value": 90},
                ],
            },
            "warning_threshold": None,
            "critical_threshold": None,
        },
    )

    assert update_response.status_code == 200
    payload = update_response.get_json()["rule"]
    assert payload["condition_mode"] == "compound"
    assert payload["warning_threshold"] is None
    assert payload["critical_threshold"] is None
    assert payload["warning_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 20.0},
            {"comparison": "gte", "value": 80.0},
        ],
    }
    assert payload["critical_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 10.0},
            {"comparison": "gte", "value": 90.0},
        ],
    }


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


def test_admin_clone_alert_rule_preserves_compound_conditions(seeded_client) -> None:
    login(seeded_client)

    create_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "condition_mode": "compound",
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 10},
                    {"comparison": "gte", "value": 90},
                ],
            },
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 20},
                    {"comparison": "gte", "value": 80},
                ],
            },
            "is_enabled": True,
            "display_name": "CPU Window",
            "rule_key": "threshold.process.cpu_usage.cpu-window",
        },
    )
    assert create_response.status_code == 201
    rule_id = create_response.get_json()["rule"]["id"]

    clone_response = seeded_client.post(f"/api/admin/alert-rules/{rule_id}/clone")

    assert clone_response.status_code == 201
    payload = clone_response.get_json()["rule"]
    assert payload["status"] == "draft"
    assert payload["is_enabled"] is False
    assert payload["condition_mode"] == "compound"
    assert payload["warning_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 20.0},
            {"comparison": "gte", "value": 80.0},
        ],
    }
    assert payload["critical_condition"] == {
        "logical_operator": "or",
        "clauses": [
            {"comparison": "lte", "value": 10.0},
            {"comparison": "gte", "value": 90.0},
        ],
    }


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


def test_admin_publish_alert_rule_allows_valid_grouped_event_draft(seeded_client) -> None:
    login(seeded_client)

    create_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "signal_type": "grouped_event_repeat",
            "signal_key": "process_restarted",
            "comparison": "gte",
            "warning_threshold": 2,
            "critical_threshold": 4,
            "display_name": "Process Restart Burst",
            "rule_key": "event.process.process_restarted.process-restart-burst",
            "is_enabled": True,
        },
    )
    assert create_response.status_code == 201
    rule_id = create_response.get_json()["rule"]["id"]

    publish_response = seeded_client.post(f"/api/admin/alert-rules/{rule_id}/publish")

    assert publish_response.status_code == 200
    payload = publish_response.get_json()
    assert payload["rule"]["status"] == "published"
    assert payload["rule"]["signal_type"] == "grouped_event_repeat"
    assert payload["rule"]["signal_key"] == "process_restarted"
    assert payload["validation"] == {"errors": [], "warnings": []}


def test_admin_publish_alert_rule_allows_valid_compound_draft(seeded_client) -> None:
    login(seeded_client)

    create_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 20},
                    {"comparison": "gte", "value": 80},
                ],
            },
            "critical_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 10},
                    {"comparison": "gte", "value": 90},
                ],
            },
            "display_name": "CPU Band",
            "rule_key": "threshold.process.cpu_usage.cpu-band-publish",
            "is_enabled": True,
        },
    )
    assert create_response.status_code == 201
    rule_id = create_response.get_json()["rule"]["id"]

    publish_response = seeded_client.post(f"/api/admin/alert-rules/{rule_id}/publish")

    assert publish_response.status_code == 200
    payload = publish_response.get_json()
    assert payload["rule"]["status"] == "published"
    assert payload["rule"]["condition_mode"] == "compound"
    assert payload["validation"] == {"errors": [], "warnings": []}


def test_admin_publish_alert_rule_accepts_compound_warnings(seeded_client) -> None:
    login(seeded_client)

    create_response = seeded_client.post(
        "/api/admin/alert-rules",
        json={
            "scope_type": "object_type",
            "object_type": "SoftwareProcess",
            "state_type": "process",
            "metric_key": "cpu_usage",
            "comparison": "gte",
            "condition_mode": "compound",
            "warning_condition": {
                "logical_operator": "or",
                "clauses": [
                    {"comparison": "lte", "value": 20},
                    {"comparison": "gte", "value": 80},
                ],
            },
            "critical_condition": None,
            "display_name": "CPU Band (Copy)",
            "rule_key": "threshold.process.cpu_usage.cpu-band-publish-copy",
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

