from __future__ import annotations

from flask import g

from app.db import get_db
from app.metamodel_audit import json_or_none, serialize_metamodel_audit_log, write_metamodel_audit_log


def test_json_or_none_returns_none_for_empty_values_and_json_for_payload() -> None:
    assert json_or_none(None) is None
    assert json_or_none("") is None
    assert json_or_none({}) is None
    assert json_or_none({"code": "WorkerPool"}) == '{"code":"WorkerPool"}'


def test_write_metamodel_audit_log_rejects_invalid_entity_or_action(seeded_app) -> None:
    with seeded_app.app_context():
        db_conn = get_db()

        try:
            write_metamodel_audit_log(
                db_conn,
                entity_type="bad_type",
                entity_id=1,
                action_type="create",
                summary="bad entity",
            )
            entity_error = None
        except ValueError as exc:
            entity_error = str(exc)

        try:
            write_metamodel_audit_log(
                db_conn,
                entity_type="semantic_type",
                entity_id=1,
                action_type="bad_action",
                summary="bad action",
            )
            action_error = None
        except ValueError as exc:
            action_error = str(exc)

        assert entity_error == "entity_type is invalid"
        assert action_error == "action_type is invalid"


def test_write_metamodel_audit_log_uses_flask_user_when_actor_is_missing(seeded_app) -> None:
    with seeded_app.app_context():
        db_conn = get_db()
        g.user = {"id": 1, "username": "admin"}

        write_metamodel_audit_log(
            db_conn,
            entity_type="semantic_type",
            entity_id=103,
            action_type="update",
            summary="updated semantic type",
            metamodel_version_id=1,
            semantic_type_id=103,
            details={"field": "display_name"},
        )
        db_conn.commit()

        row = db_conn.execute(
            """
            SELECT actor_user_id, summary, details_json
            FROM metamodel_audit_logs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        assert row["actor_user_id"] == 1
        assert row["summary"] == "updated semantic type"
        assert row["details_json"] == '{"field":"display_name"}'


def test_serialize_metamodel_audit_log_handles_missing_and_present_details() -> None:
    without_details = serialize_metamodel_audit_log(
        {
            "id": 1,
            "metamodel_version_id": 1,
            "metamodel_version_code": "seed-v1",
            "metamodel_version_status": "published",
            "semantic_type_id": 103,
            "semantic_type_code": "SoftwareProcess",
            "entity_type": "semantic_type",
            "entity_id": 103,
            "action_type": "update",
            "actor_user_id": 1,
            "actor_username": "admin",
            "summary": "updated semantic type",
            "details_json": None,
            "created_at": "2026-05-06T09:00:00.000+09:00",
        }
    )
    with_details = serialize_metamodel_audit_log(
        {
            "id": 2,
            "metamodel_version_id": 1,
            "metamodel_version_code": "seed-v1",
            "metamodel_version_status": "published",
            "semantic_type_id": 103,
            "semantic_type_code": "SoftwareProcess",
            "entity_type": "semantic_type",
            "entity_id": 103,
            "action_type": "update",
            "actor_user_id": 1,
            "actor_username": "admin",
            "summary": "updated semantic type",
            "details_json": '{"field":"display_name"}',
            "created_at": "2026-05-06T09:00:01.000+09:00",
        }
    )

    assert without_details["details"] is None
    assert with_details["details"] == {"field": "display_name"}
