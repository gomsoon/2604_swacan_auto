from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import Blueprint, request

from .auth import admin_required, error_response
from .db import get_db

bp = Blueprint("admin_metamodel_api", __name__, url_prefix="/api/admin/metamodel")

ALLOWED_VERSION_STATUSES = {"draft", "published", "deprecated"}
ALLOWED_SEMANTIC_TYPE_KINDS = {"node", "edge", "container", "runtime-only"}
ALLOWED_PROPERTY_VALUE_TYPES = {"string", "integer", "number", "boolean", "enum", "json"}


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


def parse_optional_string(value: Any, *, field_name: str, max_length: int | None = None) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        return None
    if max_length is not None and len(normalized) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return normalized


def require_draft_version(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return None, error_response("metamodel_not_found", "metamodel version not found", 404)
    if version["status"] != "draft":
        return None, error_response("invalid_state", "only draft metamodel versions can be edited", 409)
    return version, None


def fetch_semantic_type_row(type_id: int):
    return get_db().execute(
        """
        SELECT st.id, st.metamodel_version_id, st.code, st.display_name, st.description, st.kind, st.runtime_kind,
               st.is_groupable, st.allows_runtime_binding, st.default_notation_id, st.is_active,
               st.created_at, st.updated_at,
               nd.code AS default_notation_code,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM semantic_types AS st
        JOIN metamodel_versions AS mv ON mv.id = st.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        LEFT JOIN notation_definitions AS nd ON nd.id = st.default_notation_id
        WHERE st.id = ?
        """,
        (type_id,),
    ).fetchone()


def serialize_semantic_type(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "metamodel_version_id": row["metamodel_version_id"],
        "metamodel_version_code": row["metamodel_version_code"],
        "namespace_code": row["namespace_code"],
        "code": row["code"],
        "display_name": row["display_name"],
        "description": row["description"],
        "kind": row["kind"],
        "runtime_kind": row["runtime_kind"],
        "is_groupable": bool(row["is_groupable"]),
        "allows_runtime_binding": bool(row["allows_runtime_binding"]),
        "default_notation_id": row["default_notation_id"],
        "default_notation_code": row["default_notation_code"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def fetch_property_row(property_id: int):
    return get_db().execute(
        """
        SELECT pd.id, pd.semantic_type_id, pd.code, pd.display_name, pd.description, pd.value_type, pd.unit,
               pd.default_value_json, pd.is_required, pd.is_runtime, pd.is_user_editable, pd.sort_order,
               pd.created_at, pd.updated_at,
               st.code AS semantic_type_code,
               st.display_name AS semantic_type_display_name,
               st.metamodel_version_id,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM property_definitions AS pd
        JOIN semantic_types AS st ON st.id = pd.semantic_type_id
        JOIN metamodel_versions AS mv ON mv.id = st.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE pd.id = ?
        """,
        (property_id,),
    ).fetchone()


def normalize_default_value_json(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            parsed = json.loads(normalized)
        else:
            parsed = value
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("default_value_json must be valid JSON") from exc


def serialize_property_definition(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "semantic_type_id": row["semantic_type_id"],
        "semantic_type_code": row["semantic_type_code"],
        "semantic_type_display_name": row["semantic_type_display_name"],
        "metamodel_version_id": row["metamodel_version_id"],
        "metamodel_version_code": row["metamodel_version_code"],
        "namespace_code": row["namespace_code"],
        "code": row["code"],
        "display_name": row["display_name"],
        "description": row["description"],
        "value_type": row["value_type"],
        "unit": row["unit"],
        "default_value_json": row["default_value_json"],
        "default_value": parse_json_or_none(row["default_value_json"]),
        "is_required": bool(row["is_required"]),
        "is_runtime": bool(row["is_runtime"]),
        "is_user_editable": bool(row["is_user_editable"]),
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def validate_semantic_type_payload(data: dict[str, Any], *, partial: bool = False) -> tuple[dict[str, Any] | None, Any | None]:
    payload = dict(data)
    try:
        if not partial or "code" in payload:
            code = parse_optional_string(payload.get("code"), field_name="code", max_length=100)
            if not code:
                return None, error_response("validation_error", "code is required", 400)
            payload["code"] = code

        if not partial or "display_name" in payload:
            display_name = parse_optional_string(payload.get("display_name"), field_name="display_name", max_length=120)
            if not display_name:
                return None, error_response("validation_error", "display_name is required", 400)
            payload["display_name"] = display_name

        if not partial or "kind" in payload:
            kind = payload.get("kind")
            if kind not in ALLOWED_SEMANTIC_TYPE_KINDS:
                return None, error_response("validation_error", "kind is invalid", 400)

        if "description" in payload:
            payload["description"] = parse_optional_string(payload.get("description"), field_name="description", max_length=500)
        if "runtime_kind" in payload:
            payload["runtime_kind"] = parse_optional_string(payload.get("runtime_kind"), field_name="runtime_kind", max_length=100)
    except ValueError as exc:
        return None, error_response("validation_error", str(exc), 400)

    for bool_field in ("is_groupable", "allows_runtime_binding", "is_active"):
        if not partial or bool_field in payload:
            value = payload.get(bool_field)
            if not isinstance(value, bool):
                return None, error_response("validation_error", f"{bool_field} must be a boolean", 400)
            payload[bool_field] = value

    return payload, None


def validate_property_payload(data: dict[str, Any], *, partial: bool = False) -> tuple[dict[str, Any] | None, Any | None]:
    payload = dict(data)
    try:
        if not partial or "code" in payload:
            code = parse_optional_string(payload.get("code"), field_name="code", max_length=100)
            if not code:
                return None, error_response("validation_error", "code is required", 400)
            payload["code"] = code

        if not partial or "display_name" in payload:
            display_name = parse_optional_string(payload.get("display_name"), field_name="display_name", max_length=120)
            if not display_name:
                return None, error_response("validation_error", "display_name is required", 400)
            payload["display_name"] = display_name

        if not partial or "value_type" in payload:
            value_type = payload.get("value_type")
            if value_type not in ALLOWED_PROPERTY_VALUE_TYPES:
                return None, error_response("validation_error", "value_type is invalid", 400)
            payload["value_type"] = value_type

        if "description" in payload:
            payload["description"] = parse_optional_string(payload.get("description"), field_name="description", max_length=500)
        if "unit" in payload:
            payload["unit"] = parse_optional_string(payload.get("unit"), field_name="unit", max_length=50)
        if "default_value_json" in payload:
            payload["default_value_json"] = normalize_default_value_json(payload.get("default_value_json"))
    except ValueError as exc:
        return None, error_response("validation_error", str(exc), 400)

    for bool_field in ("is_required", "is_runtime", "is_user_editable"):
        if not partial or bool_field in payload:
            value = payload.get(bool_field)
            if not isinstance(value, bool):
                return None, error_response("validation_error", f"{bool_field} must be a boolean", 400)
            payload[bool_field] = value

    if not partial or "sort_order" in payload:
        sort_order = payload.get("sort_order")
        if isinstance(sort_order, bool) or not isinstance(sort_order, int):
            return None, error_response("validation_error", "sort_order must be an integer", 400)
        if sort_order < 0 or sort_order > 9999:
            return None, error_response("validation_error", "sort_order must be between 0 and 9999", 400)
        payload["sort_order"] = sort_order

    return payload, None


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


@bp.get("/versions/<int:version_id>/semantic-types")
@admin_required
def list_semantic_types(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return error_response("metamodel_not_found", "metamodel version not found", 404)

    rows = get_db().execute(
        """
        SELECT st.id, st.metamodel_version_id, st.code, st.display_name, st.description, st.kind, st.runtime_kind,
               st.is_groupable, st.allows_runtime_binding, st.default_notation_id, st.is_active,
               st.created_at, st.updated_at,
               nd.code AS default_notation_code,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM semantic_types AS st
        JOIN metamodel_versions AS mv ON mv.id = st.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        LEFT JOIN notation_definitions AS nd ON nd.id = st.default_notation_id
        WHERE st.metamodel_version_id = ?
        ORDER BY st.kind ASC, st.code ASC, st.id ASC
        """,
        (version_id,),
    ).fetchall()

    return {
        "version": serialize_version(version),
        "items": [serialize_semantic_type(row) for row in rows],
    }


@bp.post("/versions/<int:version_id>/semantic-types")
@admin_required
def create_semantic_type(version_id: int):
    version, error = require_draft_version(version_id)
    if error:
        return error

    payload, error = validate_semantic_type_payload(request.get_json(silent=True) or {}, partial=False)
    if error:
        return error

    existing = get_db().execute(
        """
        SELECT 1
        FROM semantic_types
        WHERE metamodel_version_id = ? AND code = ?
        """,
        (version_id, payload["code"]),
    ).fetchone()
    if existing is not None:
        return error_response("semantic_type_conflict", "semantic type code already exists in version", 409)

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO semantic_types (
            metamodel_version_id, code, display_name, description, kind, runtime_kind,
            is_groupable, allows_runtime_binding, default_notation_id, is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        """,
        (
            version_id,
            payload["code"],
            payload["display_name"],
            payload.get("description"),
            payload["kind"],
            payload.get("runtime_kind"),
            int(payload["is_groupable"]),
            int(payload["allows_runtime_binding"]),
            int(payload["is_active"]),
            timestamp,
            timestamp,
        ),
    )
    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET updated_at = ?
        WHERE id = ?
        """,
        (timestamp, version_id),
    )
    db_conn.commit()

    created = fetch_semantic_type_row(int(cursor.lastrowid))
    return {"version": serialize_version(version), "semantic_type": serialize_semantic_type(created)}, 201


@bp.patch("/semantic-types/<int:type_id>")
@admin_required
def update_semantic_type(type_id: int):
    existing = fetch_semantic_type_row(type_id)
    if existing is None:
        return error_response("semantic_type_not_found", "semantic type not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft semantic types can be edited", 409)

    current_payload = {
        "code": existing["code"],
        "display_name": existing["display_name"],
        "description": existing["description"],
        "kind": existing["kind"],
        "runtime_kind": existing["runtime_kind"],
        "is_groupable": bool(existing["is_groupable"]),
        "allows_runtime_binding": bool(existing["allows_runtime_binding"]),
        "is_active": bool(existing["is_active"]),
    }
    current_payload.update(request.get_json(silent=True) or {})
    payload, error = validate_semantic_type_payload(current_payload, partial=False)
    if error:
        return error

    conflict = get_db().execute(
        """
        SELECT 1
        FROM semantic_types
        WHERE metamodel_version_id = ? AND code = ? AND id != ?
        """,
        (existing["metamodel_version_id"], payload["code"], type_id),
    ).fetchone()
    if conflict is not None:
        return error_response("semantic_type_conflict", "semantic type code already exists in version", 409)

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE semantic_types
        SET code = ?,
            display_name = ?,
            description = ?,
            kind = ?,
            runtime_kind = ?,
            is_groupable = ?,
            allows_runtime_binding = ?,
            is_active = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload["code"],
            payload["display_name"],
            payload.get("description"),
            payload["kind"],
            payload.get("runtime_kind"),
            int(payload["is_groupable"]),
            int(payload["allows_runtime_binding"]),
            int(payload["is_active"]),
            timestamp,
            type_id,
        ),
    )
    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET updated_at = ?
        WHERE id = ?
        """,
        (timestamp, existing["metamodel_version_id"]),
    )
    db_conn.commit()

    updated = fetch_semantic_type_row(type_id)
    return {"semantic_type": serialize_semantic_type(updated)}


@bp.get("/semantic-types/<int:type_id>/properties")
@admin_required
def list_property_definitions(type_id: int):
    semantic_type = fetch_semantic_type_row(type_id)
    if semantic_type is None:
        return error_response("semantic_type_not_found", "semantic type not found", 404)

    rows = get_db().execute(
        """
        SELECT pd.id, pd.semantic_type_id, pd.code, pd.display_name, pd.description, pd.value_type, pd.unit,
               pd.default_value_json, pd.is_required, pd.is_runtime, pd.is_user_editable, pd.sort_order,
               pd.created_at, pd.updated_at,
               st.code AS semantic_type_code,
               st.display_name AS semantic_type_display_name,
               st.metamodel_version_id,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM property_definitions AS pd
        JOIN semantic_types AS st ON st.id = pd.semantic_type_id
        JOIN metamodel_versions AS mv ON mv.id = st.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE pd.semantic_type_id = ?
        ORDER BY pd.sort_order ASC, pd.code ASC, pd.id ASC
        """,
        (type_id,),
    ).fetchall()

    return {
        "semantic_type": serialize_semantic_type(semantic_type),
        "items": [serialize_property_definition(row) for row in rows],
    }


@bp.post("/semantic-types/<int:type_id>/properties")
@admin_required
def create_property_definition(type_id: int):
    semantic_type = fetch_semantic_type_row(type_id)
    if semantic_type is None:
        return error_response("semantic_type_not_found", "semantic type not found", 404)
    if semantic_type["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft semantic types can be edited", 409)

    payload, error = validate_property_payload(request.get_json(silent=True) or {}, partial=False)
    if error:
        return error

    conflict = get_db().execute(
        """
        SELECT 1
        FROM property_definitions
        WHERE semantic_type_id = ? AND code = ?
        """,
        (type_id, payload["code"]),
    ).fetchone()
    if conflict is not None:
        return error_response("property_conflict", "property code already exists in semantic type", 409)

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO property_definitions (
            semantic_type_id, code, display_name, description, value_type, unit, default_value_json,
            is_required, is_runtime, is_user_editable, sort_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            type_id,
            payload["code"],
            payload["display_name"],
            payload.get("description"),
            payload["value_type"],
            payload.get("unit"),
            payload.get("default_value_json"),
            int(payload["is_required"]),
            int(payload["is_runtime"]),
            int(payload["is_user_editable"]),
            payload["sort_order"],
            timestamp,
            timestamp,
        ),
    )
    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET updated_at = ?
        WHERE id = ?
        """,
        (timestamp, semantic_type["metamodel_version_id"]),
    )
    db_conn.commit()

    created = fetch_property_row(int(cursor.lastrowid))
    return {
        "semantic_type": serialize_semantic_type(semantic_type),
        "property_definition": serialize_property_definition(created),
    }, 201


@bp.patch("/properties/<int:property_id>")
@admin_required
def update_property_definition(property_id: int):
    existing = fetch_property_row(property_id)
    if existing is None:
        return error_response("property_not_found", "property definition not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft property definitions can be edited", 409)

    current_payload = {
        "code": existing["code"],
        "display_name": existing["display_name"],
        "description": existing["description"],
        "value_type": existing["value_type"],
        "unit": existing["unit"],
        "default_value_json": existing["default_value_json"],
        "is_required": bool(existing["is_required"]),
        "is_runtime": bool(existing["is_runtime"]),
        "is_user_editable": bool(existing["is_user_editable"]),
        "sort_order": existing["sort_order"],
    }
    current_payload.update(request.get_json(silent=True) or {})
    payload, error = validate_property_payload(current_payload, partial=False)
    if error:
        return error

    conflict = get_db().execute(
        """
        SELECT 1
        FROM property_definitions
        WHERE semantic_type_id = ? AND code = ? AND id != ?
        """,
        (existing["semantic_type_id"], payload["code"], property_id),
    ).fetchone()
    if conflict is not None:
        return error_response("property_conflict", "property code already exists in semantic type", 409)

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE property_definitions
        SET code = ?,
            display_name = ?,
            description = ?,
            value_type = ?,
            unit = ?,
            default_value_json = ?,
            is_required = ?,
            is_runtime = ?,
            is_user_editable = ?,
            sort_order = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload["code"],
            payload["display_name"],
            payload.get("description"),
            payload["value_type"],
            payload.get("unit"),
            payload.get("default_value_json"),
            int(payload["is_required"]),
            int(payload["is_runtime"]),
            int(payload["is_user_editable"]),
            payload["sort_order"],
            timestamp,
            property_id,
        ),
    )
    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET updated_at = ?
        WHERE id = ?
        """,
        (timestamp, existing["metamodel_version_id"]),
    )
    db_conn.commit()

    updated = fetch_property_row(property_id)
    return {"property_definition": serialize_property_definition(updated)}
