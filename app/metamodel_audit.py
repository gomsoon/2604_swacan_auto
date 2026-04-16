from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import g


ALLOWED_METAMODEL_AUDIT_ENTITY_TYPES = {
    "metamodel_version",
    "semantic_type",
    "property_definition",
    "notation_definition",
    "containment_rule",
    "association_definition",
}

ALLOWED_METAMODEL_AUDIT_ACTION_TYPES = {
    "create",
    "update",
    "clone",
    "delete",
    "publish",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def json_or_none(value: Any) -> str | None:
    if value in (None, "", {}):
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def write_metamodel_audit_log(
    db_conn,
    *,
    entity_type: str,
    entity_id: int | None,
    action_type: str,
    summary: str,
    metamodel_version_id: int | None = None,
    semantic_type_id: int | None = None,
    details: dict[str, Any] | None = None,
    actor_user_id: int | None = None,
) -> None:
    if entity_type not in ALLOWED_METAMODEL_AUDIT_ENTITY_TYPES:
        raise ValueError("entity_type is invalid")
    if action_type not in ALLOWED_METAMODEL_AUDIT_ACTION_TYPES:
        raise ValueError("action_type is invalid")

    resolved_actor_user_id = actor_user_id
    if resolved_actor_user_id is None and g.get("user") is not None:
        resolved_actor_user_id = g.user["id"]

    timestamp = now_iso()
    db_conn.execute(
        """
        INSERT INTO metamodel_audit_logs (
            metamodel_version_id,
            semantic_type_id,
            entity_type,
            entity_id,
            action_type,
            actor_user_id,
            summary,
            details_json,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            metamodel_version_id,
            semantic_type_id,
            entity_type,
            entity_id,
            action_type,
            resolved_actor_user_id,
            summary,
            json_or_none(details),
            timestamp,
        ),
    )


def serialize_metamodel_audit_log(row) -> dict[str, Any]:
    details_json = row["details_json"]
    return {
        "id": row["id"],
        "metamodel_version_id": row["metamodel_version_id"],
        "metamodel_version_code": row["metamodel_version_code"],
        "semantic_type_id": row["semantic_type_id"],
        "semantic_type_code": row["semantic_type_code"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "action_type": row["action_type"],
        "actor_user_id": row["actor_user_id"],
        "actor_username": row["actor_username"],
        "summary": row["summary"],
        "details_json": details_json,
        "details": json.loads(details_json) if details_json else None,
        "created_at": row["created_at"],
    }
