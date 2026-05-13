from __future__ import annotations

import json
from datetime import datetime

from app.alert_archive import insert_alert_history_archive
from app.db import get_db
from app.views_api import build_view_runtime_watch_state, detect_view_runtime_changes


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
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                102,
                1302,
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
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                103,
                1303,
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
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity,
                state_json, occurred_at, received_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                3,
                None,
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
                id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                101,
                "agent_local",
                1302,
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
                id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                102,
                "agent_local",
                1303,
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
                id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                103,
                "agent_local",
                None,
                "outside_view",
                "process_stopped",
                "warning",
                "outside",
                json.dumps({"pid": 5555}),
                "2026-04-10T10:30:10.100+09:00",
                "2026-04-10T10:30:10.230+09:00",
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
                1302,
                "process.down",
                "critical",
                "open",
                "2026-04-10T10:21:10.100+09:00",
                "2026-04-10T10:21:10.100+09:00",
                1,
                "process not found",
                json.dumps({"event_type": "process_stopped"}),
                "2026-04-10T10:21:10.230+09:00",
                "2026-04-10T10:21:10.230+09:00",
            ),
        )
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
                "2026-04-10T10:21:10.100+09:00",
                "2026-04-10T10:21:10.100+09:00",
                1,
                "process not found",
                json.dumps({"pid": 1234}),
                "2026-04-10T10:21:10.230+09:00",
                "2026-04-10T10:21:10.230+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO grouped_events (
                monitored_object_id, target_id, event_type, severity, first_occurred_at, last_occurred_at,
                repeat_count, latest_message, latest_event_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1303,
                "agent_local",
                "agent_heartbeat_lost",
                "warning",
                "2026-04-10T10:20:10.100+09:00",
                "2026-04-10T10:20:10.100+09:00",
                1,
                "heartbeat delayed",
                json.dumps({"delay_ms": 5000}),
                "2026-04-10T10:20:10.230+09:00",
                "2026-04-10T10:20:10.230+09:00",
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
    assert [item["monitored_object_id"] for item in payload["items"]] == [1302, 1303]
    assert payload["items"][0]["state"]["pid"] == 1234
    assert payload["items"][1]["state"]["outbox_queue_depth"] == 0
    assert payload["items"][1]["status"] == "up"
    assert payload["items"][1]["state"]["heartbeat_timeout_level"] == "normal"


def test_latest_state_prefers_active_version_targets_over_legacy_view_nodes(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:05.000+09:00")
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE view_nodes
            SET target_id = CASE
                WHEN node_type = 'SoftwareProcess' THEN 'legacy_process_target'
                WHEN node_type = 'MonitoringAgent' THEN 'legacy_agent_target'
                ELSE target_id
            END
            WHERE view_id = 1
            """
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert [item["target_id"] for item in payload["items"]] == ["app_main", "agent_local"]


def test_latest_state_prefers_monitored_object_binding_over_changed_active_target_id(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:05.000+09:00")
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE view_version_nodes
            SET target_id = 'stale_process_target'
            WHERE id = 1102
            """
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert [item["target_id"] for item in payload["items"]] == ["app_main", "agent_local"]
    assert payload["items"][0]["monitored_object_id"] == 1302


def test_events_prefers_active_version_targets_over_legacy_view_nodes(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE view_nodes
            SET target_id = CASE
                WHEN node_type = 'SoftwareProcess' THEN 'legacy_process_target'
                WHEN node_type = 'MonitoringAgent' THEN 'legacy_agent_target'
                ELSE target_id
            END
            WHERE view_id = 1
            """
        )
        db_conn.execute(
            """
            INSERT INTO raw_events (
                id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                104,
                "agent_local",
                None,
                "legacy_process_target",
                "process_stopped",
                "warning",
                "legacy only",
                json.dumps({"pid": 8080}),
                "2026-04-10T10:40:10.100+09:00",
                "2026-04-10T10:40:10.230+09:00",
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/events?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert all(item["target_id"] in {"app_main", "agent_local"} for item in payload["items"])
    assert not any(item["target_id"] == "legacy_process_target" for item in payload["items"])


def test_events_prefers_monitored_object_binding_over_changed_active_target_id(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE view_version_nodes
            SET target_id = 'stale_process_target'
            WHERE id = 1102
            """
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/events?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert any(item["target_id"] == "app_main" for item in payload["items"])
    assert not any(item["target_id"] == "stale_process_target" for item in payload["items"])
    assert payload["items"][0]["monitored_object_id"] == 1302


def test_alerts_return_open_monitored_object_alerts_for_active_view(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE alert_instances
            SET source_rule_id = ?, acknowledged_at = ?, acknowledged_by_user_id = ?, ack_note = ?, updated_at = ?
            WHERE monitored_object_id = ?
            """,
            (
                1501,
                "2026-04-10T10:21:30.000+09:00",
                1,
                "운영자가 확인함",
                "2026-04-10T10:21:30.000+09:00",
                1302,
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/alerts?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["monitored_object_id"] == 1302
    assert payload["items"][0]["alert_code"] == "process.down"
    assert payload["items"][0]["repeat_count"] == 1
    assert payload["items"][0]["source_rule_id"] == 1501
    assert payload["items"][0]["source_rule_metric_key"] == "cpu_usage"
    assert payload["items"][0]["source_rule_target_label"] == "SoftwareProcess"
    assert payload["items"][0]["is_acknowledged"] is True
    assert payload["items"][0]["acknowledged_by_username"] == "admin"
    assert payload["items"][0]["ack_note"] == "운영자가 확인함"


def test_alerts_prefer_monitored_object_binding_over_changed_active_target_id(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE view_version_nodes
            SET target_id = 'stale_process_target'
            WHERE id = 1102
            """
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/alerts?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["monitored_object_id"] == 1302


def test_alerts_default_to_active_status_filter(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE alert_instances
            SET status = 'in_progress', status_updated_at = ?, status_updated_by_user_id = ?, status_note = ?, updated_at = ?
            WHERE monitored_object_id = ?
            """,
            (
                "2026-04-10T10:22:00.000+09:00",
                1,
                "triage",
                "2026-04-10T10:22:00.000+09:00",
                1302,
            ),
        )
        db_conn.execute(
            """
            INSERT INTO alert_instances (
                monitored_object_id, alert_code, severity, status, status_updated_at, status_updated_by_user_id, status_note,
                resolved_at, resolved_by_user_id, first_occurred_at, last_occurred_at, repeat_count, latest_message,
                metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1302,
                "process.warning",
                "warning",
                "resolved",
                "2026-04-10T10:25:00.000+09:00",
                1,
                "resolved note",
                "2026-04-10T10:25:00.000+09:00",
                1,
                "2026-04-10T10:24:00.000+09:00",
                "2026-04-10T10:24:30.000+09:00",
                1,
                "resolved message",
                json.dumps({"state": "up"}),
                "2026-04-10T10:24:00.000+09:00",
                "2026-04-10T10:25:00.000+09:00",
            ),
        )
        db_conn.commit()
    login(seeded_client)

    active_response = seeded_client.get("/api/views/1/alerts?limit=10")
    resolved_response = seeded_client.get("/api/views/1/alerts?limit=10&status=resolved")

    assert active_response.status_code == 200
    assert len(active_response.get_json()["items"]) == 1
    assert active_response.get_json()["items"][0]["status"] == "in_progress"
    assert active_response.get_json()["items"][0]["status_note"] == "triage"

    assert resolved_response.status_code == 200
    assert len(resolved_response.get_json()["items"]) == 1
    assert resolved_response.get_json()["items"][0]["status"] == "resolved"
    assert resolved_response.get_json()["items"][0]["resolved_by_username"] == "admin"


def test_alerts_reject_invalid_status_filter(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/views/1/alerts?status=invalid")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_alerts_reject_out_of_range_limits(seeded_client) -> None:
    login(seeded_client)

    low_response = seeded_client.get("/api/views/1/alerts?limit=0")
    high_response = seeded_client.get("/api/views/1/alerts?limit=101")

    assert low_response.status_code == 400
    assert low_response.get_json()["error"]["code"] == "validation_error"
    assert high_response.status_code == 400
    assert high_response.get_json()["error"]["code"] == "validation_error"


def test_runtime_object_slice_returns_current_view_runtime_summary(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/runtime-objects/1302/slice?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["monitored_object_id"] == 1302
    assert [item["display_name"] for item in payload["fanout_nodes"]] == ["App Process"]
    assert payload["fanout_nodes"][0]["node_type"] == "SoftwareProcess"
    assert [item["target_id"] for item in payload["latest_states"]] == ["app_main"]
    assert payload["latest_states"][0]["state"]["pid"] == 1234
    assert [item["alert_code"] for item in payload["alerts"]] == ["process.down"]
    assert [item["event_type"] for item in payload["events"]] == ["process_stopped"]
    assert payload["history"]["summary"]["resolved_alert_count"] == 0
    assert payload["history"]["summary"]["raw_event_count"] == 1
    assert payload["history"]["raw_events"][0]["event_type"] == "process_stopped"


def test_runtime_object_slice_returns_alert_history_archive_summary(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        alert_row = db_conn.execute(
            """
            SELECT monitored_object_id, alert_code, source_rule_id, severity,
                   acknowledged_at, acknowledged_by_user_id,
                   first_occurred_at, last_occurred_at, repeat_count,
                   latest_message, metadata_json
            FROM alert_instances
            WHERE monitored_object_id = ?
            """,
            (1302,),
        ).fetchone()
        insert_alert_history_archive(
            db_conn,
            alert_row=alert_row,
            resolved_at="2026-04-10T10:25:00.000+09:00",
            resolution_source="manual_operator",
            resolution_reason="manual_resolved",
            resolution_note="resolved from monitoring view test",
            resolved_by_user_id=1,
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/runtime-objects/1302/slice?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["history"]["summary"]["resolved_alert_count"] == 1
    assert payload["history"]["summary"]["latest_resolved_at"] == "2026-04-10T10:25:00.000+09:00"
    assert payload["history"]["alert_archive"][0]["resolution_source"] == "manual_operator"
    assert payload["history"]["alert_archive"][0]["resolution_reason"] == "manual_resolved"
    assert payload["history"]["alert_archive"][0]["resolution_note"] == "resolved from monitoring view test"
    assert payload["history"]["alert_archive"][0]["source_rule_key"] is None
    assert payload["history"]["alert_archive"][0]["source_rule_display_name_snapshot"] is None
    assert payload["history"]["alert_archive"][0]["explanation"]["reason"] == "process not found"
    assert payload["history"]["alert_archive"][0]["explanation"]["suppressed_rule_display_names"] == []
    assert payload["history"]["alert_archive"][0]["explanation"]["resolution_reason"] == "manual_resolved"
    assert payload["history"]["alert_history"][0]["resolution_reason"] == "manual_resolved"


def test_runtime_object_slice_prefers_binding_when_active_target_id_changes(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE view_version_nodes
            SET target_id = 'stale_process_target'
            WHERE id = 1102
            """
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/runtime-objects/1302/slice?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["monitored_object_id"] == 1302
    assert payload["fanout_nodes"][0]["monitored_object_id"] == 1302
    assert payload["latest_states"][0]["target_id"] == "app_main"


def test_runtime_object_slice_returns_not_found_for_object_outside_current_view(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/runtime-objects/9999/slice?limit=10")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_runtime_object_slice_accepts_boundary_limits(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    low_response = seeded_client.get("/api/views/1/runtime-objects/1302/slice?limit=1")
    high_response = seeded_client.get("/api/views/1/runtime-objects/1302/slice?limit=100")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["alerts"]) == 1
    assert len(high_response.get_json()["events"]) == 1


def test_runtime_object_slice_rejects_out_of_range_limits(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    zero_response = seeded_client.get("/api/views/1/runtime-objects/1302/slice?limit=0")
    over_response = seeded_client.get("/api/views/1/runtime-objects/1302/slice?limit=101")
    invalid_response = seeded_client.get("/api/views/1/runtime-objects/1302/slice?limit=abc")

    assert zero_response.status_code == 400
    assert over_response.status_code == 400
    assert invalid_response.status_code == 400
    assert zero_response.get_json()["error"]["code"] == "validation_error"
    assert over_response.get_json()["error"]["code"] == "validation_error"
    assert invalid_response.get_json()["error"]["code"] == "validation_error"


def test_view_runtime_watch_state_detects_monitored_object_updates(seeded_app) -> None:
    seed_monitoring_rows(seeded_app)

    with seeded_app.app_context():
        previous_state = build_view_runtime_watch_state(1)
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE latest_states
            SET updated_at = ?, state_json = ?
            WHERE monitored_object_id = ? AND state_type = 'process'
            """,
            (
                "2026-04-10T10:22:00.000+09:00",
                json.dumps({"pid": 1234, "cpu_usage": 77.7}),
                1302,
            ),
        )
        db_conn.commit()
        current_state = build_view_runtime_watch_state(1)

    payload = detect_view_runtime_changes(previous_state, current_state)

    assert payload == {
        "full_refresh": False,
        "reason": "runtime_objects_changed",
        "monitored_object_ids": [1302],
    }


def test_view_runtime_watch_state_detects_alert_count_change_on_resolve(seeded_app) -> None:
    seed_monitoring_rows(seeded_app)

    with seeded_app.app_context():
        previous_state = build_view_runtime_watch_state(1)
        db_conn = get_db()
        db_conn.execute("DELETE FROM alert_instances WHERE monitored_object_id = ?", (1302,))
        db_conn.commit()
        current_state = build_view_runtime_watch_state(1)

    payload = detect_view_runtime_changes(previous_state, current_state)

    assert payload == {
        "full_refresh": False,
        "reason": "runtime_objects_changed",
        "monitored_object_ids": [1302],
    }


def test_view_runtime_watch_state_requests_full_refresh_when_view_signature_changes(seeded_app) -> None:
    seed_monitoring_rows(seeded_app)

    with seeded_app.app_context():
        previous_state = build_view_runtime_watch_state(1)
        db_conn = get_db()
        db_conn.execute(
            """
            UPDATE view_version_nodes
            SET target_id = ?
            WHERE id = ?
            """,
            ("app_main_v2", 1102),
        )
        db_conn.commit()
        current_state = build_view_runtime_watch_state(1)

    payload = detect_view_runtime_changes(previous_state, current_state)

    assert payload["full_refresh"] is True
    assert payload["reason"] == "view_structure_changed"
    assert payload["monitored_object_ids"] == [1301, 1302, 1303]


def test_latest_state_prefers_draft_targets_when_active_version_is_missing(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:05.000+09:00")
    login(seeded_client)

    create_view_response = seeded_client.post(
        "/api/views",
        json={"name": "Draft Preview View", "description": "draft fallback"},
    )
    assert create_view_response.status_code == 201
    view_id = create_view_response.get_json()["view"]["id"]

    draft_response = seeded_client.post(
        f"/api/views/{view_id}/drafts",
        json={"description": "draft preview"},
    )
    assert draft_response.status_code == 201
    draft_id = draft_response.get_json()["version"]["id"]

    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO view_nodes (
                view_id, parent_node_id, node_type, semantic_type_code, notation_code, display_name, target_id,
                layer_order, x, y, width, height, is_deleted, style_json, created_at, updated_at
            ) VALUES (?, NULL, 'PhysicalServer', 'PhysicalServer', 'server.physical.rect', 'Legacy Host', 'legacy_host',
                      10, 10, 10, 100, 80, 0, NULL, ?, ?)
            """,
            (
                view_id,
                "2026-04-10T10:00:00.000+09:00",
                "2026-04-10T10:00:00.000+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO view_version_nodes (
                view_version_id, element_key, parent_node_id, node_type, semantic_type_code, notation_code,
                display_name, target_id, instance_mode, cardinality_scope, expected_min, expected_max,
                layer_order, x, y, width, height, collapsed_state, is_deleted, style_json, properties_json,
                created_at, updated_at
            ) VALUES (?, 'draft_process_main', NULL, 'SoftwareProcess', 'SoftwareProcess', 'process.rounded_rect',
                      'Draft Process', 'draft_process_target', 'single', 'group_total', 1, 1,
                      20, 40, 40, 160, 56, 0, 0, NULL, NULL, ?, ?)
            """,
            (
                draft_id,
                "2026-04-10T10:00:00.000+09:00",
                "2026-04-10T10:00:00.000+09:00",
            ),
        )
        db_conn.execute(
            """
            INSERT INTO latest_states (
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity, state_json, occurred_at, received_at, updated_at
            ) VALUES (?, NULL, NULL, ?, 'process', 'up', 'normal', ?, ?, ?, ?)
            """,
            (
                9991,
                "draft_process_target",
                json.dumps({"pid": 4567, "cpu_usage": 1.5}),
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.220+09:00",
                "2026-04-10T10:20:00.220+09:00",
            ),
        )
        db_conn.commit()

    response = seeded_client.get(f"/api/views/{view_id}/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert [item["target_id"] for item in payload["items"]] == ["draft_process_target"]


def test_latest_state_uses_newly_activated_version_targets(seeded_app, seeded_client) -> None:
    seeded_app.config["CURRENT_TIME_PROVIDER"] = lambda: datetime.fromisoformat("2026-04-10T10:20:05.000+09:00")
    login(seeded_client)

    created = seeded_client.post(
        "/api/views/1/drafts",
        json={"description": "activate monitoring target"},
    ).get_json()
    draft_id = created["version"]["id"]
    process_node = next(node for node in created["nodes"] if node["node_type"] == "SoftwareProcess")

    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            "UPDATE view_version_nodes SET target_id = ? WHERE id = ?",
            ("activated_process_target", process_node["id"]),
        )
        db_conn.execute(
            """
            INSERT INTO latest_states (
                id, view_node_id, monitored_object_id, target_id, state_type, status, severity, state_json, occurred_at, received_at, updated_at
            ) VALUES (?, NULL, NULL, ?, 'process', 'up', 'normal', ?, ?, ?, ?)
            """,
            (
                9992,
                "activated_process_target",
                json.dumps({"pid": 7777, "cpu_usage": 5.5}),
                "2026-04-10T10:20:00.100+09:00",
                "2026-04-10T10:20:00.220+09:00",
                "2026-04-10T10:20:00.220+09:00",
            ),
        )
        db_conn.commit()

    published = seeded_client.post(
        f"/api/view-versions/{draft_id}/publish",
        json={"revision": created["version"]["revision"]},
    ).get_json()
    activated = seeded_client.post(
        f"/api/view-versions/{draft_id}/activate",
        json={"revision": published["version"]["revision"]},
    )

    assert activated.status_code == 200

    response = seeded_client.get("/api/views/1/latest-state")

    assert response.status_code == 200
    payload = response.get_json()
    assert any(item["target_id"] == "activated_process_target" for item in payload["items"])
    assert not any(item["target_id"] == "app_main" for item in payload["items"])


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
    assert [item["event_type"] for item in payload["items"]] == ["process_stopped", "agent_heartbeat_lost"]
    assert payload["items"][0]["repeat_count"] == 1
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


def test_event_drill_down_returns_group_raw_events_for_active_view(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    with seeded_app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO raw_events (
                id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                104,
                "agent_local",
                1302,
                "app_main",
                "process_stopped",
                "warning",
                "process still missing",
                json.dumps({"pid": 1234, "retry": 2}),
                "2026-04-10T10:21:40.100+09:00",
                "2026-04-10T10:21:40.230+09:00",
            ),
        )
        db_conn.execute(
            """
            UPDATE grouped_events
            SET last_occurred_at = ?, repeat_count = ?, latest_message = ?, latest_event_json = ?, updated_at = ?
            WHERE monitored_object_id = ? AND event_type = 'process_stopped'
            """,
            (
                "2026-04-10T10:21:40.100+09:00",
                2,
                "process still missing",
                json.dumps({"pid": 1234, "retry": 2}),
                "2026-04-10T10:21:40.230+09:00",
                1302,
            ),
        )
        db_conn.commit()
    login(seeded_client)

    response = seeded_client.get("/api/views/1/events/1/raw-events?limit=10")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["grouped_event"]["id"] == 1
    assert payload["grouped_event"]["repeat_count"] == 2
    assert [item["id"] for item in payload["items"]] == [104, 101]
    assert payload["items"][0]["agent_id"] == "agent_local"
    assert payload["items"][0]["event"]["retry"] == 2
    assert all(item["event_type"] == "process_stopped" for item in payload["items"])


def test_event_drill_down_accepts_boundary_limits(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    low_response = seeded_client.get("/api/views/1/events/1/raw-events?limit=1")
    high_response = seeded_client.get("/api/views/1/events/1/raw-events?limit=100")

    assert low_response.status_code == 200
    assert high_response.status_code == 200
    assert len(low_response.get_json()["items"]) == 1
    assert len(high_response.get_json()["items"]) == 1


def test_event_drill_down_rejects_out_of_range_limits(seeded_client) -> None:
    login(seeded_client)

    zero_response = seeded_client.get("/api/views/1/events/1/raw-events?limit=0")
    over_response = seeded_client.get("/api/views/1/events/1/raw-events?limit=101")
    invalid_response = seeded_client.get("/api/views/1/events/1/raw-events?limit=abc")

    assert zero_response.status_code == 400
    assert over_response.status_code == 400
    assert invalid_response.status_code == 400
    assert zero_response.get_json()["error"]["code"] == "validation_error"
    assert over_response.get_json()["error"]["code"] == "validation_error"
    assert invalid_response.get_json()["error"]["code"] == "validation_error"


def test_event_drill_down_returns_not_found_for_unmatched_grouped_event(seeded_app, seeded_client) -> None:
    seed_monitoring_rows(seeded_app)
    login(seeded_client)

    response = seeded_client.get("/api/views/1/events/999/raw-events?limit=10")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


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
