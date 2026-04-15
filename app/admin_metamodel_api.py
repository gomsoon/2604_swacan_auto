from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import Blueprint, request

from .auth import admin_required, error_response
from .db import get_db

bp = Blueprint("admin_metamodel_api", __name__, url_prefix="/api/admin/metamodel")

ALLOWED_VERSION_STATUSES = {"draft", "published", "deprecated"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def parse_json_or_none(raw_value: str | None) -> Any:
    if not raw_value:
        return None
    return json.loads(raw_value)


def fetch_version(version_id: int):
    return get_db().execute(
        """
        SELECT mv.id, mv.namespace_id, mv.version_code, mv.status, mv.description, mv.based_on_version_id,
               mv.published_at, mv.created_at, mv.updated_at,
               ns.code AS namespace_code, ns.name AS namespace_name
        FROM metamodel_versions AS mv
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE mv.id = ?
        """,
        (version_id,),
    ).fetchone()


def serialize_version(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "namespace_id": row["namespace_id"],
        "namespace_code": row["namespace_code"],
        "namespace_name": row["namespace_name"],
        "version_code": row["version_code"],
        "status": row["status"],
        "description": row["description"],
        "based_on_version_id": row["based_on_version_id"],
        "published_at": row["published_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_version_summary(row) -> dict[str, Any]:
    return {
        **serialize_version(row),
        "semantic_type_count": row["semantic_type_count"],
        "notation_count": row["notation_count"],
        "palette_group_count": row["palette_group_count"],
    }


def require_namespace_id(namespace_code: str):
    row = get_db().execute(
        "SELECT id FROM metamodel_namespaces WHERE code = ?",
        (namespace_code,),
    ).fetchone()
    if row is None:
        return None, error_response("validation_error", "namespace_code is invalid", 400)
    return row["id"], None


def clone_metamodel_version(*, source_version_id: int, namespace_id: int, version_code: str, description: str | None):
    db_conn = get_db()
    timestamp = now_iso()
    cursor = db_conn.execute(
        """
        INSERT INTO metamodel_versions (
            namespace_id, version_code, status, description, based_on_version_id, published_at, created_at, updated_at
        ) VALUES (?, ?, 'draft', ?, ?, NULL, ?, ?)
        """,
        (namespace_id, version_code, description, source_version_id, timestamp, timestamp),
    )
    new_version_id = cursor.lastrowid

    old_to_new_semantic_type: dict[int, int] = {}
    old_to_new_palette_group: dict[int, int] = {}
    old_to_new_notation: dict[int, int] = {}

    source_palette_groups = db_conn.execute(
        """
        SELECT id, code, label, sort_order
        FROM palette_groups
        WHERE metamodel_version_id = ?
        ORDER BY sort_order ASC, id ASC
        """,
        (source_version_id,),
    ).fetchall()
    for row in source_palette_groups:
        new_row = db_conn.execute(
            """
            INSERT INTO palette_groups (
                metamodel_version_id, code, label, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (new_version_id, row["code"], row["label"], row["sort_order"], timestamp, timestamp),
        )
        old_to_new_palette_group[row["id"]] = new_row.lastrowid

    source_semantic_types = db_conn.execute(
        """
        SELECT id, code, display_name, description, kind, runtime_kind,
               is_groupable, allows_runtime_binding, default_notation_id, is_active
        FROM semantic_types
        WHERE metamodel_version_id = ?
        ORDER BY id ASC
        """,
        (source_version_id,),
    ).fetchall()
    for row in source_semantic_types:
        new_row = db_conn.execute(
            """
            INSERT INTO semantic_types (
                metamodel_version_id, code, display_name, description, kind, runtime_kind,
                is_groupable, allows_runtime_binding, default_notation_id, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                new_version_id,
                row["code"],
                row["display_name"],
                row["description"],
                row["kind"],
                row["runtime_kind"],
                row["is_groupable"],
                row["allows_runtime_binding"],
                row["is_active"],
                timestamp,
                timestamp,
            ),
        )
        old_to_new_semantic_type[row["id"]] = new_row.lastrowid

    source_notations = db_conn.execute(
        """
        SELECT id, semantic_type_id, palette_group_id, code, display_name, kind,
               render_primitive, render_schema_json, style_tokens_json,
               is_default, is_visible_in_palette, sort_order
        FROM notation_definitions
        WHERE metamodel_version_id = ?
        ORDER BY sort_order ASC, id ASC
        """,
        (source_version_id,),
    ).fetchall()
    for row in source_notations:
        new_row = db_conn.execute(
            """
            INSERT INTO notation_definitions (
                metamodel_version_id, semantic_type_id, palette_group_id, code, display_name, kind,
                render_primitive, render_schema_json, style_tokens_json,
                is_default, is_visible_in_palette, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_version_id,
                old_to_new_semantic_type[row["semantic_type_id"]],
                old_to_new_palette_group.get(row["palette_group_id"]) if row["palette_group_id"] else None,
                row["code"],
                row["display_name"],
                row["kind"],
                row["render_primitive"],
                row["render_schema_json"],
                row["style_tokens_json"],
                row["is_default"],
                row["is_visible_in_palette"],
                row["sort_order"],
                timestamp,
                timestamp,
            ),
        )
        old_to_new_notation[row["id"]] = new_row.lastrowid

    for row in source_semantic_types:
        if row["default_notation_id"] is None:
            continue
        db_conn.execute(
            """
            UPDATE semantic_types
            SET default_notation_id = ?
            WHERE id = ?
            """,
            (old_to_new_notation[row["default_notation_id"]], old_to_new_semantic_type[row["id"]]),
        )

    source_properties = db_conn.execute(
        """
        SELECT semantic_type_id, code, display_name, description, value_type, unit, default_value_json,
               is_required, is_runtime, is_user_editable, sort_order
        FROM property_definitions
        WHERE semantic_type_id IN (
            SELECT id FROM semantic_types WHERE metamodel_version_id = ?
        )
        ORDER BY sort_order ASC, id ASC
        """,
        (source_version_id,),
    ).fetchall()
    for row in source_properties:
        db_conn.execute(
            """
            INSERT INTO property_definitions (
                semantic_type_id, code, display_name, description, value_type, unit, default_value_json,
                is_required, is_runtime, is_user_editable, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                old_to_new_semantic_type[row["semantic_type_id"]],
                row["code"],
                row["display_name"],
                row["description"],
                row["value_type"],
                row["unit"],
                row["default_value_json"],
                row["is_required"],
                row["is_runtime"],
                row["is_user_editable"],
                row["sort_order"],
                timestamp,
                timestamp,
            ),
        )

    source_associations = db_conn.execute(
        """
        SELECT code, display_name, description, source_type_id, target_type_id, direction,
               multiplicity_source, multiplicity_target, semantics_json
        FROM association_definitions
        WHERE metamodel_version_id = ?
        ORDER BY id ASC
        """,
        (source_version_id,),
    ).fetchall()
    for row in source_associations:
        db_conn.execute(
            """
            INSERT INTO association_definitions (
                metamodel_version_id, code, display_name, description, source_type_id, target_type_id,
                direction, multiplicity_source, multiplicity_target, semantics_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_version_id,
                row["code"],
                row["display_name"],
                row["description"],
                old_to_new_semantic_type[row["source_type_id"]],
                old_to_new_semantic_type[row["target_type_id"]],
                row["direction"],
                row["multiplicity_source"],
                row["multiplicity_target"],
                row["semantics_json"],
                timestamp,
                timestamp,
            ),
        )

    source_containment_rules = db_conn.execute(
        """
        SELECT parent_type_id, child_type_id, min_count, max_count, cardinality_scope, is_required
        FROM containment_rules
        WHERE metamodel_version_id = ?
        ORDER BY id ASC
        """,
        (source_version_id,),
    ).fetchall()
    for row in source_containment_rules:
        db_conn.execute(
            """
            INSERT INTO containment_rules (
                metamodel_version_id, parent_type_id, child_type_id, min_count, max_count,
                cardinality_scope, is_required, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_version_id,
                old_to_new_semantic_type[row["parent_type_id"]],
                old_to_new_semantic_type[row["child_type_id"]],
                row["min_count"],
                row["max_count"],
                row["cardinality_scope"],
                row["is_required"],
                timestamp,
                timestamp,
            ),
        )

    db_conn.commit()
    return new_version_id


@bp.get("/versions")
@admin_required
def list_versions():
    rows = get_db().execute(
        """
        SELECT mv.id, mv.namespace_id, mv.version_code, mv.status, mv.description, mv.based_on_version_id,
               mv.published_at, mv.created_at, mv.updated_at,
               ns.code AS namespace_code, ns.name AS namespace_name,
               (SELECT COUNT(*) FROM semantic_types AS st WHERE st.metamodel_version_id = mv.id) AS semantic_type_count,
               (SELECT COUNT(*) FROM notation_definitions AS nd WHERE nd.metamodel_version_id = mv.id) AS notation_count,
               (SELECT COUNT(*) FROM palette_groups AS pg WHERE pg.metamodel_version_id = mv.id) AS palette_group_count
        FROM metamodel_versions AS mv
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        ORDER BY ns.code ASC, mv.id ASC
        """
    ).fetchall()
    return {"items": [serialize_version_summary(row) for row in rows]}


@bp.post("/versions")
@admin_required
def create_version():
    payload = request.get_json(silent=True) or {}
    namespace_code = payload.get("namespace_code")
    version_code = payload.get("version_code")
    based_on_version_id = payload.get("based_on_version_id")
    description = payload.get("description")

    if not namespace_code or not version_code:
        return error_response("validation_error", "namespace_code and version_code are required", 400)
    if not isinstance(based_on_version_id, int):
        return error_response("validation_error", "based_on_version_id must be an integer", 400)

    namespace_id, namespace_error = require_namespace_id(namespace_code)
    if namespace_error:
        return namespace_error

    source_version = fetch_version(based_on_version_id)
    if source_version is None:
        return error_response("validation_error", "based_on_version_id is invalid", 400)
    if source_version["namespace_id"] != namespace_id:
        return error_response("validation_error", "namespace_code must match based_on_version_id namespace", 400)

    existing = get_db().execute(
        """
        SELECT 1
        FROM metamodel_versions
        WHERE namespace_id = ? AND version_code = ?
        """,
        (namespace_id, version_code),
    ).fetchone()
    if existing is not None:
        return error_response("version_conflict", "version_code already exists in namespace", 409)

    new_version_id = clone_metamodel_version(
        source_version_id=based_on_version_id,
        namespace_id=namespace_id,
        version_code=version_code,
        description=description,
    )
    return {"version": serialize_version(fetch_version(new_version_id))}, 201


@bp.post("/versions/<int:version_id>/publish")
@admin_required
def publish_version(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return error_response("metamodel_not_found", "metamodel version not found", 404)
    if version["status"] != "draft":
        return error_response("publish_conflict", "only draft versions can be published", 409)

    db_conn = get_db()
    timestamp = now_iso()
    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET status = 'deprecated', updated_at = ?
        WHERE namespace_id = ? AND status = 'published' AND id != ?
        """,
        (timestamp, version["namespace_id"], version_id),
    )
    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET status = 'published', published_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (timestamp, timestamp, version_id),
    )
    db_conn.commit()

    return {"version": serialize_version(fetch_version(version_id))}
