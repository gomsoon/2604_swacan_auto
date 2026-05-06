from __future__ import annotations

from app.alert_archive import insert_alert_history_archive, serialize_alert_archive_row
from app.db import get_db


def test_insert_alert_history_archive_rejects_invalid_resolution_source(seeded_app) -> None:
    with seeded_app.app_context():
        db_conn = get_db()

        try:
            insert_alert_history_archive(
                db_conn,
                alert_row={
                    "monitored_object_id": 1302,
                    "alert_code": "rule.1501",
                    "source_rule_id": 1501,
                    "first_occurred_at": "2026-04-12T11:05:00.000+09:00",
                    "severity": "warning",
                    "repeat_count": 2,
                    "acknowledged_at": None,
                    "acknowledged_by_user_id": None,
                    "latest_message": "cpu warning",
                    "metadata_json": "{\"metric_key\":\"cpu_usage\"}",
                },
                resolved_at="2026-04-12T11:06:00.000+09:00",
                resolution_source="bad_source",
                resolution_reason="invalid",
                resolved_by_user_id=1,
            )
            raised = False
        except ValueError as exc:
            raised = True
            assert str(exc) == "invalid resolution_source"

        assert raised is True


def test_insert_alert_history_archive_persists_acknowledgement_and_resolution(seeded_app) -> None:
    with seeded_app.app_context():
        db_conn = get_db()

        archive_id = insert_alert_history_archive(
            db_conn,
            alert_row={
                "monitored_object_id": 1302,
                "alert_code": "rule.1501",
                "source_rule_id": 1501,
                "first_occurred_at": "2026-04-12T11:05:00.000+09:00",
                "severity": "critical",
                "repeat_count": 3,
                "acknowledged_at": "2026-04-12T11:05:10.000+09:00",
                "acknowledged_by_user_id": 1,
                "latest_message": "cpu critical",
                "metadata_json": "{\"metric_key\":\"cpu_usage\"}",
            },
            resolved_at="2026-04-12T11:06:00.000+09:00",
            resolution_source="manual_operator",
            resolution_reason="resolved by operator",
            resolved_by_user_id=1,
        )
        db_conn.commit()

        row = db_conn.execute(
            """
            SELECT *
            FROM alert_history_archive
            WHERE id = ?
            """,
            (archive_id,),
        ).fetchone()

        assert row["final_status"] == "resolved"
        assert row["was_acknowledged"] == 1
        assert row["last_acknowledged_by_user_id"] == 1
        assert row["resolution_source"] == "manual_operator"
        assert row["resolution_reason"] == "resolved by operator"


def test_serialize_alert_archive_row_handles_metadata_json_and_invalid_json() -> None:
    valid_payload = serialize_alert_archive_row(
        {
            "id": 1,
            "monitored_object_id": 1302,
            "runtime_binding_key": "process:1302",
            "display_name": "App Process",
            "semantic_type_code": "SoftwareProcess",
            "alert_code": "rule.1501",
            "source_rule_id": 1501,
            "source_rule_metric_key": "cpu_usage",
            "source_rule_scope_type": "object_type",
            "source_rule_target_label": "SoftwareProcess",
            "opened_at": "2026-04-12T11:05:00.000+09:00",
            "resolved_at": "2026-04-12T11:06:00.000+09:00",
            "first_severity": "warning",
            "highest_severity": "critical",
            "final_severity": "critical",
            "final_status": "resolved",
            "repeat_count": 3,
            "was_acknowledged": 1,
            "last_acknowledged_at": "2026-04-12T11:05:10.000+09:00",
            "last_acknowledged_by_user_id": 1,
            "last_acknowledged_by_username": "admin",
            "resolution_source": "manual_operator",
            "resolution_reason": "resolved",
            "resolved_by_user_id": 1,
            "resolved_by_username": "admin",
            "latest_message": "cpu critical",
            "metadata_json": "{\"metric_key\":\"cpu_usage\"}",
            "created_at": "2026-04-12T11:06:00.000+09:00",
            "updated_at": "2026-04-12T11:06:00.000+09:00",
        }
    )
    invalid_payload = serialize_alert_archive_row(
        {
            "id": 2,
            "monitored_object_id": 1303,
            "runtime_binding_key": "agent:1303",
            "display_name": "Local Agent",
            "semantic_type_code": "MonitoringAgent",
            "alert_code": "rule.1502",
            "source_rule_id": 1502,
            "source_rule_metric_key": "outbox_queue_depth",
            "source_rule_scope_type": "object_type",
            "source_rule_target_label": "MonitoringAgent",
            "opened_at": "2026-04-12T11:05:00.000+09:00",
            "resolved_at": "2026-04-12T11:06:00.000+09:00",
            "first_severity": "warning",
            "highest_severity": "warning",
            "final_severity": "warning",
            "final_status": "resolved",
            "repeat_count": 1,
            "was_acknowledged": 0,
            "last_acknowledged_at": None,
            "last_acknowledged_by_user_id": None,
            "last_acknowledged_by_username": None,
            "resolution_source": "auto_recovery",
            "resolution_reason": None,
            "resolved_by_user_id": None,
            "resolved_by_username": None,
            "latest_message": "recovered",
            "metadata_json": "{invalid-json}",
            "created_at": "2026-04-12T11:06:00.000+09:00",
            "updated_at": "2026-04-12T11:06:00.000+09:00",
        }
    )

    assert valid_payload["was_acknowledged"] is True
    assert valid_payload["metadata"] == {"metric_key": "cpu_usage"}
    assert invalid_payload["was_acknowledged"] is False
    assert invalid_payload["metadata"] == "{invalid-json}"
