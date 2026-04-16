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
ALLOWED_CARDINALITY_SCOPES = {"group_total", "per_member"}
ALLOWED_ASSOCIATION_DIRECTIONS = {"directed", "undirected"}
ALLOWED_NOTATION_KINDS = {"node", "edge"}
ALLOWED_RENDER_PRIMITIVES = {"rect", "rounded_rect", "line", "badge", "label"}


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


def build_unique_clone_text(
    base: str,
    *,
    max_length: int,
    exists_fn,
    suffix_builder,
) -> str:
    index = 1
    while index < 1000:
        suffix = suffix_builder(index)
        candidate = f"{base[: max_length - len(suffix)]}{suffix}"
        if not exists_fn(candidate):
            return candidate
        index += 1
    raise ValueError("failed to generate unique clone value")


def semantic_type_code_exists(version_id: int, code: str) -> bool:
    row = get_db().execute(
        """
        SELECT 1
        FROM semantic_types
        WHERE metamodel_version_id = ? AND code = ?
        """,
        (version_id, code),
    ).fetchone()
    return row is not None


def notation_code_exists(version_id: int, code: str) -> bool:
    row = get_db().execute(
        """
        SELECT 1
        FROM notation_definitions
        WHERE metamodel_version_id = ? AND code = ?
        """,
        (version_id, code),
    ).fetchone()
    return row is not None


def fetch_semantic_type_delete_blockers(type_id: int) -> dict[str, int]:
    row = get_db().execute(
        """
        SELECT
            (SELECT COUNT(*) FROM containment_rules WHERE parent_type_id = ?) AS containment_out_count,
            (SELECT COUNT(*) FROM containment_rules WHERE child_type_id = ?) AS containment_in_count,
            (SELECT COUNT(*) FROM association_definitions WHERE source_type_id = ?) AS association_out_count,
            (SELECT COUNT(*) FROM association_definitions WHERE target_type_id = ?) AS association_in_count
        """,
        (type_id, type_id, type_id, type_id),
    ).fetchone()
    return {
        "containment_out_count": row["containment_out_count"],
        "containment_in_count": row["containment_in_count"],
        "association_out_count": row["association_out_count"],
        "association_in_count": row["association_in_count"],
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


def fetch_containment_rule_row(rule_id: int):
    return get_db().execute(
        """
        SELECT cr.id, cr.metamodel_version_id, cr.parent_type_id, cr.child_type_id, cr.min_count, cr.max_count,
               cr.cardinality_scope, cr.is_required, cr.created_at, cr.updated_at,
               parent_st.code AS parent_type_code,
               parent_st.display_name AS parent_type_display_name,
               child_st.code AS child_type_code,
               child_st.display_name AS child_type_display_name,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM containment_rules AS cr
        JOIN semantic_types AS parent_st ON parent_st.id = cr.parent_type_id
        JOIN semantic_types AS child_st ON child_st.id = cr.child_type_id
        JOIN metamodel_versions AS mv ON mv.id = cr.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE cr.id = ?
        """,
        (rule_id,),
    ).fetchone()


def serialize_containment_rule(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "metamodel_version_id": row["metamodel_version_id"],
        "metamodel_version_code": row["metamodel_version_code"],
        "namespace_code": row["namespace_code"],
        "parent_type_id": row["parent_type_id"],
        "parent_type_code": row["parent_type_code"],
        "parent_type_display_name": row["parent_type_display_name"],
        "child_type_id": row["child_type_id"],
        "child_type_code": row["child_type_code"],
        "child_type_display_name": row["child_type_display_name"],
        "min_count": row["min_count"],
        "max_count": row["max_count"],
        "cardinality_scope": row["cardinality_scope"],
        "is_required": bool(row["is_required"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def fetch_association_definition_row(association_id: int):
    return get_db().execute(
        """
        SELECT ad.id, ad.metamodel_version_id, ad.code, ad.display_name, ad.description,
               ad.source_type_id, ad.target_type_id, ad.direction,
               ad.multiplicity_source, ad.multiplicity_target, ad.semantics_json,
               ad.created_at, ad.updated_at,
               source_st.code AS source_type_code,
               source_st.display_name AS source_type_display_name,
               target_st.code AS target_type_code,
               target_st.display_name AS target_type_display_name,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM association_definitions AS ad
        JOIN semantic_types AS source_st ON source_st.id = ad.source_type_id
        JOIN semantic_types AS target_st ON target_st.id = ad.target_type_id
        JOIN metamodel_versions AS mv ON mv.id = ad.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE ad.id = ?
        """,
        (association_id,),
    ).fetchone()


def serialize_association_definition(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "metamodel_version_id": row["metamodel_version_id"],
        "metamodel_version_code": row["metamodel_version_code"],
        "namespace_code": row["namespace_code"],
        "code": row["code"],
        "display_name": row["display_name"],
        "description": row["description"],
        "source_type_id": row["source_type_id"],
        "source_type_code": row["source_type_code"],
        "source_type_display_name": row["source_type_display_name"],
        "target_type_id": row["target_type_id"],
        "target_type_code": row["target_type_code"],
        "target_type_display_name": row["target_type_display_name"],
        "direction": row["direction"],
        "multiplicity_source": row["multiplicity_source"],
        "multiplicity_target": row["multiplicity_target"],
        "semantics_json": row["semantics_json"],
        "semantics": parse_json_or_none(row["semantics_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def fetch_notation_row(notation_id: int):
    return get_db().execute(
        """
        SELECT nd.id, nd.metamodel_version_id, nd.semantic_type_id, nd.palette_group_id, nd.code, nd.display_name,
               nd.kind, nd.render_primitive, nd.render_schema_json, nd.style_tokens_json,
               nd.is_default, nd.is_visible_in_palette, nd.sort_order, nd.created_at, nd.updated_at,
               st.code AS semantic_type_code,
               st.display_name AS semantic_type_display_name,
               st.kind AS semantic_type_kind,
               pg.code AS palette_group_code,
               pg.label AS palette_group_label,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM notation_definitions AS nd
        JOIN semantic_types AS st ON st.id = nd.semantic_type_id
        JOIN metamodel_versions AS mv ON mv.id = nd.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        LEFT JOIN palette_groups AS pg ON pg.id = nd.palette_group_id
        WHERE nd.id = ?
        """,
        (notation_id,),
    ).fetchone()


def serialize_notation_definition(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "metamodel_version_id": row["metamodel_version_id"],
        "metamodel_version_code": row["metamodel_version_code"],
        "namespace_code": row["namespace_code"],
        "semantic_type_id": row["semantic_type_id"],
        "semantic_type_code": row["semantic_type_code"],
        "semantic_type_display_name": row["semantic_type_display_name"],
        "palette_group_id": row["palette_group_id"],
        "palette_group_code": row["palette_group_code"],
        "palette_group_label": row["palette_group_label"],
        "code": row["code"],
        "display_name": row["display_name"],
        "kind": row["kind"],
        "render_primitive": row["render_primitive"],
        "render_schema_json": row["render_schema_json"],
        "render_schema": parse_json_or_none(row["render_schema_json"]),
        "style_tokens_json": row["style_tokens_json"],
        "style_tokens": parse_json_or_none(row["style_tokens_json"]),
        "is_default": bool(row["is_default"]),
        "is_visible_in_palette": bool(row["is_visible_in_palette"]),
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def fetch_notation_delete_blockers(notation_id: int) -> dict[str, int]:
    row = get_db().execute(
        """
        SELECT COUNT(*) AS default_reference_count
        FROM semantic_types
        WHERE default_notation_id = ?
        """,
        (notation_id,),
    ).fetchone()
    return {
        "default_reference_count": row["default_reference_count"],
    }


def validate_json_text_field(value: Any, *, field_name: str, required: bool) -> str | None:
    if value in (None, ""):
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    try:
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                if required:
                    raise ValueError(f"{field_name} is required")
                return None
            parsed = json.loads(normalized)
        else:
            parsed = value
        return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"{field_name} must be valid JSON") from exc


def validate_notation_payload(data: dict[str, Any], *, partial: bool = False) -> tuple[dict[str, Any] | None, Any | None]:
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
            if kind not in ALLOWED_NOTATION_KINDS:
                return None, error_response("validation_error", "kind is invalid", 400)
            payload["kind"] = kind

        if not partial or "render_primitive" in payload:
            render_primitive = payload.get("render_primitive")
            if render_primitive not in ALLOWED_RENDER_PRIMITIVES:
                return None, error_response("validation_error", "render_primitive is invalid", 400)
            payload["render_primitive"] = render_primitive

        if not partial or "semantic_type_id" in payload:
            semantic_type_id = payload.get("semantic_type_id")
            if isinstance(semantic_type_id, bool) or not isinstance(semantic_type_id, int) or semantic_type_id <= 0:
                return None, error_response("validation_error", "semantic_type_id must be a positive integer", 400)
            payload["semantic_type_id"] = semantic_type_id

        if "palette_group_id" in payload and payload.get("palette_group_id") not in (None, ""):
            palette_group_id = payload.get("palette_group_id")
            if isinstance(palette_group_id, bool) or not isinstance(palette_group_id, int) or palette_group_id <= 0:
                return None, error_response("validation_error", "palette_group_id must be a positive integer or null", 400)
            payload["palette_group_id"] = palette_group_id
        elif "palette_group_id" in payload:
            payload["palette_group_id"] = None

        if "render_schema_json" in payload or not partial:
            payload["render_schema_json"] = validate_json_text_field(
                payload.get("render_schema_json"),
                field_name="render_schema_json",
                required=True,
            )
        if "style_tokens_json" in payload:
            payload["style_tokens_json"] = validate_json_text_field(
                payload.get("style_tokens_json"),
                field_name="style_tokens_json",
                required=False,
            )
        elif not partial:
            payload["style_tokens_json"] = validate_json_text_field(
                payload.get("style_tokens_json"),
                field_name="style_tokens_json",
                required=False,
            )
    except ValueError as exc:
        return None, error_response("validation_error", str(exc), 400)

    for bool_field in ("is_default", "is_visible_in_palette"):
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


def update_default_notation(*, semantic_type_id: int, notation_id: int | None, db_conn) -> None:
    db_conn.execute(
        """
        UPDATE notation_definitions
        SET is_default = CASE WHEN id = ? THEN 1 ELSE 0 END
        WHERE semantic_type_id = ?
        """,
        (notation_id, semantic_type_id),
    )
    db_conn.execute(
        """
        UPDATE semantic_types
        SET default_notation_id = ?
        WHERE id = ?
        """,
        (notation_id, semantic_type_id),
    )


def validate_metamodel_version(version_id: int) -> dict[str, Any]:
    db_conn = get_db()
    issues: list[dict[str, Any]] = []

    semantic_types = db_conn.execute(
        """
        SELECT st.id, st.code, st.display_name, st.kind, st.default_notation_id, st.is_active
        FROM semantic_types AS st
        WHERE st.metamodel_version_id = ?
        ORDER BY st.id ASC
        """,
        (version_id,),
    ).fetchall()
    semantic_type_ids = {row["id"] for row in semantic_types}

    if not semantic_types:
        issues.append(
            {
                "code": "missing_semantic_types",
                "severity": "error",
                "message": "semantic type이 하나 이상 필요합니다.",
            }
        )

    for row in semantic_types:
        if row["kind"] == "runtime-only" or not row["is_active"]:
            continue
        if row["default_notation_id"] is None:
            issues.append(
                {
                    "code": "missing_default_notation",
                    "severity": "error",
                    "message": f"{row['display_name']} ({row['code']})에 default notation이 필요합니다.",
                    "semantic_type_id": row["id"],
                    "semantic_type_code": row["code"],
                }
            )
            continue

        notation_row = db_conn.execute(
            """
            SELECT id
            FROM notation_definitions
            WHERE id = ? AND metamodel_version_id = ?
            """,
            (row["default_notation_id"], version_id),
        ).fetchone()
        if notation_row is None:
            issues.append(
                {
                    "code": "invalid_default_notation",
                    "severity": "error",
                    "message": f"{row['display_name']} ({row['code']})의 default notation이 같은 version에 존재하지 않습니다.",
                    "semantic_type_id": row["id"],
                    "semantic_type_code": row["code"],
                }
            )

    containment_rows = db_conn.execute(
        """
        SELECT parent_type_id, child_type_id
        FROM containment_rules
        WHERE metamodel_version_id = ?
        ORDER BY id ASC
        """,
        (version_id,),
    ).fetchall()

    adjacency: dict[int, list[int]] = {}
    for row in containment_rows:
        adjacency.setdefault(row["parent_type_id"], []).append(row["child_type_id"])

    visited: set[int] = set()
    stack: set[int] = set()

    def dfs(node_id: int, path: list[int]) -> None:
        visited.add(node_id)
        stack.add(node_id)
        for next_id in adjacency.get(node_id, []):
            if next_id not in semantic_type_ids:
                issues.append(
                    {
                        "code": "invalid_containment_reference",
                        "severity": "error",
                        "message": f"containment rule이 존재하지 않는 semantic type을 참조합니다. ({node_id} -> {next_id})",
                    }
                )
                continue
            if next_id not in visited:
                dfs(next_id, path + [next_id])
            elif next_id in stack:
                cycle_path = path + [next_id]
                issues.append(
                    {
                        "code": "containment_cycle",
                        "severity": "error",
                        "message": "containment hierarchy에 cycle이 있습니다.",
                        "cycle_type_ids": cycle_path,
                    }
                )
        stack.remove(node_id)

    for type_id in semantic_type_ids:
        if type_id not in visited:
            dfs(type_id, [type_id])

    association_rows = db_conn.execute(
        """
        SELECT ad.id, ad.code, ad.source_type_id, ad.target_type_id, ad.semantics_json
        FROM association_definitions AS ad
        WHERE ad.metamodel_version_id = ?
        ORDER BY ad.id ASC
        """,
        (version_id,),
    ).fetchall()

    edge_type_codes = {
        row["code"]
        for row in semantic_types
        if row["kind"] == "edge"
    }
    for row in association_rows:
        if row["source_type_id"] not in semantic_type_ids or row["target_type_id"] not in semantic_type_ids:
            issues.append(
                {
                    "code": "invalid_association_reference",
                    "severity": "error",
                    "message": f"association {row['code']}이 같은 version에 없는 semantic type을 참조합니다.",
                    "association_id": row["id"],
                    "association_code": row["code"],
                }
            )
        semantics = parse_json_or_none(row["semantics_json"])
        if isinstance(semantics, dict) and semantics.get("default_edge_type"):
            default_edge_type = semantics["default_edge_type"]
            if default_edge_type not in edge_type_codes:
                issues.append(
                    {
                        "code": "invalid_association_edge_type",
                        "severity": "error",
                        "message": f"association {row['code']}의 default_edge_type {default_edge_type}가 존재하지 않습니다.",
                        "association_id": row["id"],
                        "association_code": row["code"],
                    }
                )

    summary = {
        "semantic_type_count": len(semantic_types),
        "containment_rule_count": len(containment_rows),
        "association_count": len(association_rows),
        "error_count": sum(1 for issue in issues if issue["severity"] == "error"),
        "warning_count": sum(1 for issue in issues if issue["severity"] == "warning"),
    }
    return {
        "is_valid": summary["error_count"] == 0,
        "summary": summary,
        "issues": issues,
    }


def normalize_json_for_compare(raw_value: Any) -> Any:
    if raw_value in (None, ""):
        return None
    try:
        parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return str(raw_value).strip()


def fetch_metamodel_diff_baseline(version) -> tuple[Any | None, str]:
    if version["based_on_version_id"]:
        baseline = fetch_version(version["based_on_version_id"])
        if baseline is not None:
            return baseline, "based_on_version"

    baseline = get_db().execute(
        """
        SELECT mv.id, mv.namespace_id, mv.version_code, mv.status, mv.description, mv.based_on_version_id,
               mv.published_at, mv.created_at, mv.updated_at,
               ns.code AS namespace_code, ns.name AS namespace_name
        FROM metamodel_versions AS mv
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE mv.namespace_id = ? AND mv.status = 'published' AND mv.id != ?
        ORDER BY COALESCE(mv.published_at, mv.updated_at, mv.created_at) DESC, mv.id DESC
        LIMIT 1
        """,
        (version["namespace_id"], version["id"]),
    ).fetchone()
    if baseline is not None:
        return baseline, "latest_published"

    return None, "none"


def build_metamodel_diff_section(
    current_items: dict[str, dict[str, Any]],
    baseline_items: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    added_keys = sorted(set(current_items) - set(baseline_items))
    removed_keys = sorted(set(baseline_items) - set(current_items))
    shared_keys = sorted(set(current_items) & set(baseline_items))

    changed: list[dict[str, Any]] = []
    unchanged_count = 0

    for key in shared_keys:
        before = baseline_items[key]
        after = current_items[key]
        changed_fields = sorted(
            field_name
            for field_name in after.keys()
            if field_name not in {"key", "title", "meta"} and before.get(field_name) != after.get(field_name)
        )
        if changed_fields:
            changed.append(
                {
                    "key": key,
                    "title": after["title"],
                    "meta": after["meta"],
                    "changed_fields": changed_fields,
                    "before": before,
                    "after": after,
                }
            )
        else:
            unchanged_count += 1

    return {
        "added": [current_items[key] for key in added_keys],
        "removed": [baseline_items[key] for key in removed_keys],
        "changed": changed,
        "unchanged_count": unchanged_count,
    }


def fetch_semantic_type_diff_items(version_id: int) -> dict[str, dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT st.code, st.display_name, st.description, st.kind, st.runtime_kind, st.is_groupable,
               st.allows_runtime_binding, st.is_active, nd.code AS default_notation_code
        FROM semantic_types AS st
        LEFT JOIN notation_definitions AS nd ON nd.id = st.default_notation_id
        WHERE st.metamodel_version_id = ?
        ORDER BY st.code ASC
        """,
        (version_id,),
    ).fetchall()
    return {
        row["code"]: {
            "key": row["code"],
            "title": row["display_name"],
            "meta": f"{row['code']} | {row['kind']}",
            "display_name": row["display_name"],
            "description": row["description"],
            "kind": row["kind"],
            "runtime_kind": row["runtime_kind"],
            "is_groupable": bool(row["is_groupable"]),
            "allows_runtime_binding": bool(row["allows_runtime_binding"]),
            "is_active": bool(row["is_active"]),
            "default_notation_code": row["default_notation_code"],
        }
        for row in rows
    }


def fetch_property_diff_items(version_id: int) -> dict[str, dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT st.code AS semantic_type_code, pd.code, pd.display_name, pd.description, pd.value_type, pd.unit,
               pd.default_value_json, pd.is_required, pd.is_runtime, pd.is_user_editable, pd.sort_order
        FROM property_definitions AS pd
        JOIN semantic_types AS st ON st.id = pd.semantic_type_id
        WHERE st.metamodel_version_id = ?
        ORDER BY st.code ASC, pd.code ASC
        """,
        (version_id,),
    ).fetchall()
    return {
        f"{row['semantic_type_code']}:{row['code']}": {
            "key": f"{row['semantic_type_code']}:{row['code']}",
            "title": row["display_name"],
            "meta": f"{row['semantic_type_code']} | {row['code']}",
            "semantic_type_code": row["semantic_type_code"],
            "display_name": row["display_name"],
            "description": row["description"],
            "value_type": row["value_type"],
            "unit": row["unit"],
            "default_value_json": normalize_json_for_compare(row["default_value_json"]),
            "is_required": bool(row["is_required"]),
            "is_runtime": bool(row["is_runtime"]),
            "is_user_editable": bool(row["is_user_editable"]),
            "sort_order": row["sort_order"],
        }
        for row in rows
    }


def fetch_containment_diff_items(version_id: int) -> dict[str, dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT parent_st.code AS parent_type_code, child_st.code AS child_type_code,
               cr.min_count, cr.max_count, cr.cardinality_scope, cr.is_required
        FROM containment_rules AS cr
        JOIN semantic_types AS parent_st ON parent_st.id = cr.parent_type_id
        JOIN semantic_types AS child_st ON child_st.id = cr.child_type_id
        WHERE cr.metamodel_version_id = ?
        ORDER BY parent_st.code ASC, child_st.code ASC
        """,
        (version_id,),
    ).fetchall()
    return {
        f"{row['parent_type_code']}->{row['child_type_code']}": {
            "key": f"{row['parent_type_code']}->{row['child_type_code']}",
            "title": f"{row['parent_type_code']} -> {row['child_type_code']}",
            "meta": row["cardinality_scope"],
            "parent_type_code": row["parent_type_code"],
            "child_type_code": row["child_type_code"],
            "min_count": row["min_count"],
            "max_count": row["max_count"],
            "cardinality_scope": row["cardinality_scope"],
            "is_required": bool(row["is_required"]),
        }
        for row in rows
    }


def fetch_association_diff_items(version_id: int) -> dict[str, dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT ad.code, ad.display_name, ad.description, ad.direction, ad.multiplicity_source,
               ad.multiplicity_target, ad.semantics_json,
               source_st.code AS source_type_code,
               target_st.code AS target_type_code
        FROM association_definitions AS ad
        JOIN semantic_types AS source_st ON source_st.id = ad.source_type_id
        JOIN semantic_types AS target_st ON target_st.id = ad.target_type_id
        WHERE ad.metamodel_version_id = ?
        ORDER BY ad.code ASC
        """,
        (version_id,),
    ).fetchall()
    return {
        row["code"]: {
            "key": row["code"],
            "title": row["display_name"],
            "meta": f"{row['source_type_code']} -> {row['target_type_code']}",
            "display_name": row["display_name"],
            "description": row["description"],
            "source_type_code": row["source_type_code"],
            "target_type_code": row["target_type_code"],
            "direction": row["direction"],
            "multiplicity_source": row["multiplicity_source"],
            "multiplicity_target": row["multiplicity_target"],
            "semantics_json": normalize_json_for_compare(row["semantics_json"]),
        }
        for row in rows
    }


def fetch_notation_diff_items(version_id: int) -> dict[str, dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT nd.code, nd.display_name, nd.kind, nd.render_primitive, nd.render_schema_json,
               nd.style_tokens_json, nd.sort_order, nd.is_default, nd.is_visible_in_palette,
               st.code AS semantic_type_code,
               pg.code AS palette_group_code
        FROM notation_definitions AS nd
        JOIN semantic_types AS st ON st.id = nd.semantic_type_id
        LEFT JOIN palette_groups AS pg ON pg.id = nd.palette_group_id
        WHERE nd.metamodel_version_id = ?
        ORDER BY nd.code ASC
        """,
        (version_id,),
    ).fetchall()
    return {
        row["code"]: {
            "key": row["code"],
            "title": row["display_name"],
            "meta": f"{row['semantic_type_code']} | {row['kind']}",
            "display_name": row["display_name"],
            "semantic_type_code": row["semantic_type_code"],
            "palette_group_code": row["palette_group_code"],
            "kind": row["kind"],
            "render_primitive": row["render_primitive"],
            "render_schema_json": normalize_json_for_compare(row["render_schema_json"]),
            "style_tokens_json": normalize_json_for_compare(row["style_tokens_json"]),
            "sort_order": row["sort_order"],
            "is_default": bool(row["is_default"]),
            "is_visible_in_palette": bool(row["is_visible_in_palette"]),
        }
        for row in rows
    }


def calculate_metamodel_diff(version_id: int) -> dict[str, Any]:
    version = fetch_version(version_id)
    if version is None:
        raise LookupError("metamodel version not found")

    baseline_version, baseline_strategy = fetch_metamodel_diff_baseline(version)

    current_sections = {
        "semantic_types": fetch_semantic_type_diff_items(version_id),
        "properties": fetch_property_diff_items(version_id),
        "containment_rules": fetch_containment_diff_items(version_id),
        "associations": fetch_association_diff_items(version_id),
        "notations": fetch_notation_diff_items(version_id),
    }
    baseline_sections = {
        "semantic_types": fetch_semantic_type_diff_items(baseline_version["id"]) if baseline_version else {},
        "properties": fetch_property_diff_items(baseline_version["id"]) if baseline_version else {},
        "containment_rules": fetch_containment_diff_items(baseline_version["id"]) if baseline_version else {},
        "associations": fetch_association_diff_items(baseline_version["id"]) if baseline_version else {},
        "notations": fetch_notation_diff_items(baseline_version["id"]) if baseline_version else {},
    }

    section_results = {
        section_name: build_metamodel_diff_section(current_sections[section_name], baseline_sections[section_name])
        for section_name in current_sections
    }
    summary = {
        section_name: {
            "added": len(section["added"]),
            "removed": len(section["removed"]),
            "changed": len(section["changed"]),
            "unchanged": section["unchanged_count"],
        }
        for section_name, section in section_results.items()
    }

    referenced_version_id = baseline_version["id"] if baseline_version else version["id"]
    active_view_rows = get_db().execute(
        """
        SELECT vv.id, vv.view_id, vv.version_code, vv.version_no, v.name AS view_name
        FROM view_versions AS vv
        JOIN views AS v ON v.id = vv.view_id
        WHERE vv.status = 'active' AND vv.metamodel_version_id = ?
        ORDER BY vv.view_id ASC, vv.id ASC
        LIMIT 10
        """,
        (referenced_version_id,),
    ).fetchall()
    active_view_count = get_db().execute(
        """
        SELECT COUNT(*) AS count
        FROM view_versions
        WHERE status = 'active' AND metamodel_version_id = ?
        """,
        (referenced_version_id,),
    ).fetchone()["count"]
    active_logical_view_count = get_db().execute(
        """
        SELECT COUNT(DISTINCT view_id) AS count
        FROM view_versions
        WHERE status = 'active' AND metamodel_version_id = ?
        """,
        (referenced_version_id,),
    ).fetchone()["count"]

    return {
        "baseline_version": serialize_version(baseline_version) if baseline_version else None,
        "baseline_strategy": baseline_strategy,
        "summary": summary,
        "impacts": {
            "referenced_version_id": referenced_version_id,
            "active_view_count": active_view_count,
            "active_logical_view_count": active_logical_view_count,
            "active_views": [
                {
                    "id": row["id"],
                    "view_id": row["view_id"],
                    "view_name": row["view_name"],
                    "version_code": row["version_code"] or f"v{row['version_no']}",
                }
                for row in active_view_rows
            ],
        },
        "sections": section_results,
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


def validate_containment_rule_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, Any | None]:
    payload = dict(data)

    for field_name in ("parent_type_id", "child_type_id"):
        value = payload.get(field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return None, error_response("validation_error", f"{field_name} must be a positive integer", 400)

    if payload["parent_type_id"] == payload["child_type_id"]:
        return None, error_response("validation_error", "parent_type_id and child_type_id must be different", 400)

    cardinality_scope = payload.get("cardinality_scope")
    if cardinality_scope not in ALLOWED_CARDINALITY_SCOPES:
        return None, error_response("validation_error", "cardinality_scope is invalid", 400)

    is_required = payload.get("is_required")
    if not isinstance(is_required, bool):
        return None, error_response("validation_error", "is_required must be a boolean", 400)

    def normalize_count(field_name: str) -> tuple[int | None, Any | None]:
        value = payload.get(field_name)
        if value in (None, ""):
            return None, None
        if isinstance(value, bool) or not isinstance(value, int):
            return None, error_response("validation_error", f"{field_name} must be an integer or null", 400)
        if value < 0 or value > 9999:
            return None, error_response("validation_error", f"{field_name} must be between 0 and 9999", 400)
        return value, None

    min_count, error = normalize_count("min_count")
    if error:
        return None, error
    max_count, error = normalize_count("max_count")
    if error:
        return None, error

    if min_count is not None and max_count is not None and max_count < min_count:
        return None, error_response("validation_error", "max_count must be greater than or equal to min_count", 400)

    payload["min_count"] = min_count
    payload["max_count"] = max_count
    return payload, None


def validate_association_definition_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, Any | None]:
    payload = dict(data)

    try:
        payload["code"] = parse_optional_string(payload.get("code"), field_name="code", max_length=100)
        if not payload["code"]:
            return None, error_response("validation_error", "code is required", 400)

        payload["display_name"] = parse_optional_string(
            payload.get("display_name"),
            field_name="display_name",
            max_length=100,
        )
        if not payload["display_name"]:
            return None, error_response("validation_error", "display_name is required", 400)

        payload["description"] = parse_optional_string(
            payload.get("description"),
            field_name="description",
            max_length=500,
        )
        payload["multiplicity_source"] = parse_optional_string(
            payload.get("multiplicity_source"),
            field_name="multiplicity_source",
            max_length=20,
        )
        payload["multiplicity_target"] = parse_optional_string(
            payload.get("multiplicity_target"),
            field_name="multiplicity_target",
            max_length=20,
        )

        for field_name in ("source_type_id", "target_type_id"):
            value = payload.get(field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                return None, error_response("validation_error", f"{field_name} must be a positive integer", 400)

        if payload["source_type_id"] == payload["target_type_id"]:
            return None, error_response("validation_error", "source_type_id and target_type_id must be different", 400)

        if payload.get("direction") not in ALLOWED_ASSOCIATION_DIRECTIONS:
            return None, error_response("validation_error", "direction is invalid", 400)

        payload["semantics_json"] = validate_json_text_field(
            payload.get("semantics_json"),
            field_name="semantics_json",
            required=False,
        )
    except ValueError as exc:
        return None, error_response("validation_error", str(exc), 400)

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


@bp.get("/versions/<int:version_id>/validation")
@admin_required
def validate_version(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return error_response("metamodel_not_found", "metamodel version not found", 404)

    return {
        "version": serialize_version(version),
        "validation": validate_metamodel_version(version_id),
    }


@bp.get("/versions/<int:version_id>/diff")
@admin_required
def diff_version(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return error_response("metamodel_not_found", "metamodel version not found", 404)

    return {
        "version": serialize_version(version),
        "diff": calculate_metamodel_diff(version_id),
    }


@bp.post("/versions/<int:version_id>/publish")
@admin_required
def publish_version(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return error_response("metamodel_not_found", "metamodel version not found", 404)
    if version["status"] != "draft":
        return error_response("publish_conflict", "only draft versions can be published", 409)

    validation = validate_metamodel_version(version_id)
    if not validation["is_valid"]:
        return {
            "error": {
                "code": "validation_failed",
                "message": "metamodel version validation failed",
            },
            "version": serialize_version(version),
            "validation": validation,
        }, 409

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


@bp.post("/semantic-types/<int:type_id>/clone")
@admin_required
def clone_semantic_type(type_id: int):
    existing = fetch_semantic_type_row(type_id)
    if existing is None:
        return error_response("semantic_type_not_found", "semantic type not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft semantic types can be cloned", 409)

    raw_payload = request.get_json(silent=True) or {}
    try:
        requested_code = parse_optional_string(raw_payload.get("code"), field_name="code", max_length=100)
        requested_display_name = parse_optional_string(
            raw_payload.get("display_name"),
            field_name="display_name",
            max_length=120,
        )
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    version_id = existing["metamodel_version_id"]
    clone_code = requested_code or build_unique_clone_text(
        existing["code"],
        max_length=100,
        exists_fn=lambda candidate: semantic_type_code_exists(version_id, candidate),
        suffix_builder=lambda index: "_copy" if index == 1 else f"_copy{index}",
    )
    if semantic_type_code_exists(version_id, clone_code):
        return error_response("semantic_type_conflict", "semantic type code already exists in version", 409)

    clone_display_name = requested_display_name or build_unique_clone_text(
        existing["display_name"],
        max_length=120,
        exists_fn=lambda _candidate: False,
        suffix_builder=lambda index: " Copy" if index == 1 else f" Copy {index}",
    )

    property_rows = get_db().execute(
        """
        SELECT code, display_name, description, value_type, unit, default_value_json,
               is_required, is_runtime, is_user_editable, sort_order
        FROM property_definitions
        WHERE semantic_type_id = ?
        ORDER BY sort_order ASC, code ASC, id ASC
        """,
        (type_id,),
    ).fetchall()
    notation_rows = get_db().execute(
        """
        SELECT palette_group_id, code, display_name, kind, render_primitive, render_schema_json,
               style_tokens_json, is_default, is_visible_in_palette, sort_order
        FROM notation_definitions
        WHERE semantic_type_id = ?
        ORDER BY sort_order ASC, code ASC, id ASC
        """,
        (type_id,),
    ).fetchall()

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
            clone_code,
            clone_display_name,
            existing["description"],
            existing["kind"],
            existing["runtime_kind"],
            int(bool(existing["is_groupable"])),
            int(bool(existing["allows_runtime_binding"])),
            int(bool(existing["is_active"])),
            timestamp,
            timestamp,
        ),
    )
    cloned_type_id = int(cursor.lastrowid)

    for row in property_rows:
        db_conn.execute(
            """
            INSERT INTO property_definitions (
                semantic_type_id, code, display_name, description, value_type, unit, default_value_json,
                is_required, is_runtime, is_user_editable, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cloned_type_id,
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

    cloned_default_notation_id = None
    for row in notation_rows:
        notation_code = build_unique_clone_text(
            row["code"],
            max_length=100,
            exists_fn=lambda candidate: notation_code_exists(version_id, candidate),
            suffix_builder=lambda index: "_copy" if index == 1 else f"_copy{index}",
        )
        notation_display_name = build_unique_clone_text(
            row["display_name"],
            max_length=120,
            exists_fn=lambda _candidate: False,
            suffix_builder=lambda index: " Copy" if index == 1 else f" Copy {index}",
        )
        notation_cursor = db_conn.execute(
            """
            INSERT INTO notation_definitions (
                metamodel_version_id, semantic_type_id, palette_group_id, code, display_name, kind,
                render_primitive, render_schema_json, style_tokens_json,
                is_default, is_visible_in_palette, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version_id,
                cloned_type_id,
                row["palette_group_id"],
                notation_code,
                notation_display_name,
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
        if row["is_default"]:
            cloned_default_notation_id = int(notation_cursor.lastrowid)

    if cloned_default_notation_id is not None:
        db_conn.execute(
            """
            UPDATE semantic_types
            SET default_notation_id = ?
            WHERE id = ?
            """,
            (cloned_default_notation_id, cloned_type_id),
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

    cloned = fetch_semantic_type_row(cloned_type_id)
    return {
        "semantic_type": serialize_semantic_type(cloned),
        "clone_summary": {
            "property_count": len(property_rows),
            "notation_count": len(notation_rows),
            "default_notation_cloned": cloned_default_notation_id is not None,
        },
    }, 201


@bp.delete("/semantic-types/<int:type_id>")
@admin_required
def delete_semantic_type(type_id: int):
    existing = fetch_semantic_type_row(type_id)
    if existing is None:
        return error_response("semantic_type_not_found", "semantic type not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft semantic types can be deleted", 409)

    blockers = fetch_semantic_type_delete_blockers(type_id)
    has_blockers = any(blockers.values())
    if has_blockers:
        return {
            "error": {
                "code": "semantic_type_in_use",
                "message": "semantic type cannot be deleted while containment or association rules still reference it",
            },
            "dependency_counts": blockers,
        }, 409

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute("DELETE FROM semantic_types WHERE id = ?", (type_id,))
    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET updated_at = ?
        WHERE id = ?
        """,
        (timestamp, existing["metamodel_version_id"]),
    )
    db_conn.commit()

    return {
        "deleted": True,
        "semantic_type_id": type_id,
    }


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


@bp.get("/versions/<int:version_id>/containment-rules")
@admin_required
def list_containment_rules(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return error_response("metamodel_not_found", "metamodel version not found", 404)

    rows = get_db().execute(
        """
        SELECT cr.id, cr.metamodel_version_id, cr.parent_type_id, cr.child_type_id, cr.min_count, cr.max_count,
               cr.cardinality_scope, cr.is_required, cr.created_at, cr.updated_at,
               parent_st.code AS parent_type_code,
               parent_st.display_name AS parent_type_display_name,
               child_st.code AS child_type_code,
               child_st.display_name AS child_type_display_name,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM containment_rules AS cr
        JOIN semantic_types AS parent_st ON parent_st.id = cr.parent_type_id
        JOIN semantic_types AS child_st ON child_st.id = cr.child_type_id
        JOIN metamodel_versions AS mv ON mv.id = cr.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE cr.metamodel_version_id = ?
        ORDER BY parent_st.code ASC, child_st.code ASC, cr.id ASC
        """,
        (version_id,),
    ).fetchall()

    return {
        "version": serialize_version(version),
        "items": [serialize_containment_rule(row) for row in rows],
    }


@bp.post("/versions/<int:version_id>/containment-rules")
@admin_required
def create_containment_rule(version_id: int):
    version, error = require_draft_version(version_id)
    if error:
        return error

    payload, error = validate_containment_rule_payload(request.get_json(silent=True) or {})
    if error:
        return error

    type_rows = get_db().execute(
        """
        SELECT id
        FROM semantic_types
        WHERE metamodel_version_id = ? AND id IN (?, ?)
        """,
        (version_id, payload["parent_type_id"], payload["child_type_id"]),
    ).fetchall()
    if len(type_rows) != 2:
        return error_response("validation_error", "parent_type_id and child_type_id must belong to the selected version", 400)

    conflict = get_db().execute(
        """
        SELECT 1
        FROM containment_rules
        WHERE metamodel_version_id = ? AND parent_type_id = ? AND child_type_id = ?
        """,
        (version_id, payload["parent_type_id"], payload["child_type_id"]),
    ).fetchone()
    if conflict is not None:
        return error_response("containment_rule_conflict", "containment rule already exists in version", 409)

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO containment_rules (
            metamodel_version_id, parent_type_id, child_type_id, min_count, max_count,
            cardinality_scope, is_required, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            payload["parent_type_id"],
            payload["child_type_id"],
            payload["min_count"],
            payload["max_count"],
            payload["cardinality_scope"],
            int(payload["is_required"]),
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

    created = fetch_containment_rule_row(int(cursor.lastrowid))
    return {
        "version": serialize_version(version),
        "containment_rule": serialize_containment_rule(created),
    }, 201


@bp.patch("/containment-rules/<int:rule_id>")
@admin_required
def update_containment_rule(rule_id: int):
    existing = fetch_containment_rule_row(rule_id)
    if existing is None:
        return error_response("containment_rule_not_found", "containment rule not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft containment rules can be edited", 409)

    current_payload = {
        "parent_type_id": existing["parent_type_id"],
        "child_type_id": existing["child_type_id"],
        "min_count": existing["min_count"],
        "max_count": existing["max_count"],
        "cardinality_scope": existing["cardinality_scope"],
        "is_required": bool(existing["is_required"]),
    }
    current_payload.update(request.get_json(silent=True) or {})
    payload, error = validate_containment_rule_payload(current_payload)
    if error:
        return error

    type_rows = get_db().execute(
        """
        SELECT id
        FROM semantic_types
        WHERE metamodel_version_id = ? AND id IN (?, ?)
        """,
        (existing["metamodel_version_id"], payload["parent_type_id"], payload["child_type_id"]),
    ).fetchall()
    if len(type_rows) != 2:
        return error_response("validation_error", "parent_type_id and child_type_id must belong to the selected version", 400)

    conflict = get_db().execute(
        """
        SELECT 1
        FROM containment_rules
        WHERE metamodel_version_id = ? AND parent_type_id = ? AND child_type_id = ? AND id != ?
        """,
        (
            existing["metamodel_version_id"],
            payload["parent_type_id"],
            payload["child_type_id"],
            rule_id,
        ),
    ).fetchone()
    if conflict is not None:
        return error_response("containment_rule_conflict", "containment rule already exists in version", 409)

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE containment_rules
        SET parent_type_id = ?,
            child_type_id = ?,
            min_count = ?,
            max_count = ?,
            cardinality_scope = ?,
            is_required = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload["parent_type_id"],
            payload["child_type_id"],
            payload["min_count"],
            payload["max_count"],
            payload["cardinality_scope"],
            int(payload["is_required"]),
            timestamp,
            rule_id,
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

    updated = fetch_containment_rule_row(rule_id)
    return {"containment_rule": serialize_containment_rule(updated)}


@bp.get("/versions/<int:version_id>/associations")
@admin_required
def list_association_definitions(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return error_response("metamodel_not_found", "metamodel version not found", 404)

    rows = get_db().execute(
        """
        SELECT ad.id, ad.metamodel_version_id, ad.code, ad.display_name, ad.description,
               ad.source_type_id, ad.target_type_id, ad.direction,
               ad.multiplicity_source, ad.multiplicity_target, ad.semantics_json,
               ad.created_at, ad.updated_at,
               source_st.code AS source_type_code,
               source_st.display_name AS source_type_display_name,
               target_st.code AS target_type_code,
               target_st.display_name AS target_type_display_name,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM association_definitions AS ad
        JOIN semantic_types AS source_st ON source_st.id = ad.source_type_id
        JOIN semantic_types AS target_st ON target_st.id = ad.target_type_id
        JOIN metamodel_versions AS mv ON mv.id = ad.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE ad.metamodel_version_id = ?
        ORDER BY ad.code ASC, ad.id ASC
        """,
        (version_id,),
    ).fetchall()

    return {
        "version": serialize_version(version),
        "items": [serialize_association_definition(row) for row in rows],
    }


@bp.post("/versions/<int:version_id>/associations")
@admin_required
def create_association_definition(version_id: int):
    version, error = require_draft_version(version_id)
    if error:
        return error

    payload, error = validate_association_definition_payload(request.get_json(silent=True) or {})
    if error:
        return error

    type_rows = get_db().execute(
        """
        SELECT id
        FROM semantic_types
        WHERE metamodel_version_id = ? AND id IN (?, ?)
        """,
        (version_id, payload["source_type_id"], payload["target_type_id"]),
    ).fetchall()
    if len(type_rows) != 2:
        return error_response("validation_error", "source_type_id and target_type_id must belong to the selected version", 400)

    conflict = get_db().execute(
        """
        SELECT 1
        FROM association_definitions
        WHERE metamodel_version_id = ? AND code = ?
        """,
        (version_id, payload["code"]),
    ).fetchone()
    if conflict is not None:
        return error_response("association_conflict", "association code already exists in version", 409)

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO association_definitions (
            metamodel_version_id, code, display_name, description, source_type_id, target_type_id,
            direction, multiplicity_source, multiplicity_target, semantics_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            payload["code"],
            payload["display_name"],
            payload.get("description"),
            payload["source_type_id"],
            payload["target_type_id"],
            payload["direction"],
            payload.get("multiplicity_source"),
            payload.get("multiplicity_target"),
            payload.get("semantics_json"),
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

    created = fetch_association_definition_row(int(cursor.lastrowid))
    return {
        "version": serialize_version(version),
        "association_definition": serialize_association_definition(created),
    }, 201


@bp.patch("/associations/<int:association_id>")
@admin_required
def update_association_definition(association_id: int):
    existing = fetch_association_definition_row(association_id)
    if existing is None:
        return error_response("association_not_found", "association definition not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft association definitions can be edited", 409)

    current_payload = {
        "code": existing["code"],
        "display_name": existing["display_name"],
        "description": existing["description"],
        "source_type_id": existing["source_type_id"],
        "target_type_id": existing["target_type_id"],
        "direction": existing["direction"],
        "multiplicity_source": existing["multiplicity_source"],
        "multiplicity_target": existing["multiplicity_target"],
        "semantics_json": existing["semantics_json"],
    }
    current_payload.update(request.get_json(silent=True) or {})
    payload, error = validate_association_definition_payload(current_payload)
    if error:
        return error

    type_rows = get_db().execute(
        """
        SELECT id
        FROM semantic_types
        WHERE metamodel_version_id = ? AND id IN (?, ?)
        """,
        (existing["metamodel_version_id"], payload["source_type_id"], payload["target_type_id"]),
    ).fetchall()
    if len(type_rows) != 2:
        return error_response("validation_error", "source_type_id and target_type_id must belong to the selected version", 400)

    conflict = get_db().execute(
        """
        SELECT 1
        FROM association_definitions
        WHERE metamodel_version_id = ? AND code = ? AND id != ?
        """,
        (existing["metamodel_version_id"], payload["code"], association_id),
    ).fetchone()
    if conflict is not None:
        return error_response("association_conflict", "association code already exists in version", 409)

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE association_definitions
        SET code = ?,
            display_name = ?,
            description = ?,
            source_type_id = ?,
            target_type_id = ?,
            direction = ?,
            multiplicity_source = ?,
            multiplicity_target = ?,
            semantics_json = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload["code"],
            payload["display_name"],
            payload.get("description"),
            payload["source_type_id"],
            payload["target_type_id"],
            payload["direction"],
            payload.get("multiplicity_source"),
            payload.get("multiplicity_target"),
            payload.get("semantics_json"),
            timestamp,
            association_id,
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

    updated = fetch_association_definition_row(association_id)
    return {"association_definition": serialize_association_definition(updated)}


@bp.get("/versions/<int:version_id>/palette-groups")
@admin_required
def list_palette_groups(version_id: int):
    version = fetch_version(version_id)
    if version is None:
        return error_response("metamodel_not_found", "metamodel version not found", 404)

    rows = get_db().execute(
        """
        SELECT id, metamodel_version_id, code, label, sort_order, created_at, updated_at
        FROM palette_groups
        WHERE metamodel_version_id = ?
        ORDER BY sort_order ASC, code ASC, id ASC
        """,
        (version_id,),
    ).fetchall()
    return {
        "version": serialize_version(version),
        "items": [
            {
                "id": row["id"],
                "metamodel_version_id": row["metamodel_version_id"],
                "code": row["code"],
                "label": row["label"],
                "sort_order": row["sort_order"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ],
    }


@bp.get("/semantic-types/<int:type_id>/notations")
@admin_required
def list_notations(type_id: int):
    semantic_type = fetch_semantic_type_row(type_id)
    if semantic_type is None:
        return error_response("semantic_type_not_found", "semantic type not found", 404)

    rows = get_db().execute(
        """
        SELECT nd.id, nd.metamodel_version_id, nd.semantic_type_id, nd.palette_group_id, nd.code, nd.display_name,
               nd.kind, nd.render_primitive, nd.render_schema_json, nd.style_tokens_json,
               nd.is_default, nd.is_visible_in_palette, nd.sort_order, nd.created_at, nd.updated_at,
               st.code AS semantic_type_code,
               st.display_name AS semantic_type_display_name,
               st.kind AS semantic_type_kind,
               pg.code AS palette_group_code,
               pg.label AS palette_group_label,
               mv.status AS metamodel_version_status,
               mv.version_code AS metamodel_version_code,
               ns.code AS namespace_code
        FROM notation_definitions AS nd
        JOIN semantic_types AS st ON st.id = nd.semantic_type_id
        JOIN metamodel_versions AS mv ON mv.id = nd.metamodel_version_id
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        LEFT JOIN palette_groups AS pg ON pg.id = nd.palette_group_id
        WHERE nd.semantic_type_id = ?
        ORDER BY nd.sort_order ASC, nd.code ASC, nd.id ASC
        """,
        (type_id,),
    ).fetchall()

    return {
        "semantic_type": serialize_semantic_type(semantic_type),
        "items": [serialize_notation_definition(row) for row in rows],
    }


@bp.post("/semantic-types/<int:type_id>/notations")
@admin_required
def create_notation(type_id: int):
    semantic_type = fetch_semantic_type_row(type_id)
    if semantic_type is None:
        return error_response("semantic_type_not_found", "semantic type not found", 404)
    if semantic_type["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft semantic types can be edited", 409)

    payload, error = validate_notation_payload(request.get_json(silent=True) or {}, partial=False)
    if error:
        return error
    if payload["semantic_type_id"] != type_id:
        return error_response("validation_error", "semantic_type_id must match the selected semantic type", 400)
    if semantic_type["kind"] == "edge" and payload["kind"] != "edge":
        return error_response("validation_error", "edge semantic type requires edge notation kind", 400)
    if semantic_type["kind"] != "edge" and payload["kind"] != "node":
        return error_response("validation_error", "non-edge semantic type requires node notation kind", 400)

    if payload.get("palette_group_id") is not None:
        palette_group = get_db().execute(
            "SELECT 1 FROM palette_groups WHERE id = ? AND metamodel_version_id = ?",
            (payload["palette_group_id"], semantic_type["metamodel_version_id"]),
        ).fetchone()
        if palette_group is None:
            return error_response("validation_error", "palette_group_id must belong to the selected version", 400)

    conflict = get_db().execute(
        """
        SELECT 1
        FROM notation_definitions
        WHERE metamodel_version_id = ? AND code = ?
        """,
        (semantic_type["metamodel_version_id"], payload["code"]),
    ).fetchone()
    if conflict is not None:
        return error_response("notation_conflict", "notation code already exists in version", 409)

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO notation_definitions (
            metamodel_version_id, semantic_type_id, palette_group_id, code, display_name, kind,
            render_primitive, render_schema_json, style_tokens_json,
            is_default, is_visible_in_palette, sort_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            semantic_type["metamodel_version_id"],
            type_id,
            payload.get("palette_group_id"),
            payload["code"],
            payload["display_name"],
            payload["kind"],
            payload["render_primitive"],
            payload["render_schema_json"],
            payload.get("style_tokens_json"),
            int(payload["is_default"]),
            int(payload["is_visible_in_palette"]),
            payload["sort_order"],
            timestamp,
            timestamp,
        ),
    )
    notation_id = int(cursor.lastrowid)
    if payload["is_default"]:
        update_default_notation(semantic_type_id=type_id, notation_id=notation_id, db_conn=db_conn)

    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET updated_at = ?
        WHERE id = ?
        """,
        (timestamp, semantic_type["metamodel_version_id"]),
    )
    db_conn.commit()

    created = fetch_notation_row(notation_id)
    return {
        "semantic_type": serialize_semantic_type(semantic_type),
        "notation_definition": serialize_notation_definition(created),
    }, 201


@bp.patch("/notations/<int:notation_id>")
@admin_required
def update_notation(notation_id: int):
    existing = fetch_notation_row(notation_id)
    if existing is None:
        return error_response("notation_not_found", "notation definition not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft notation definitions can be edited", 409)

    current_payload = {
        "semantic_type_id": existing["semantic_type_id"],
        "palette_group_id": existing["palette_group_id"],
        "code": existing["code"],
        "display_name": existing["display_name"],
        "kind": existing["kind"],
        "render_primitive": existing["render_primitive"],
        "render_schema_json": existing["render_schema_json"],
        "style_tokens_json": existing["style_tokens_json"],
        "is_default": bool(existing["is_default"]),
        "is_visible_in_palette": bool(existing["is_visible_in_palette"]),
        "sort_order": existing["sort_order"],
    }
    current_payload.update(request.get_json(silent=True) or {})
    payload, error = validate_notation_payload(current_payload, partial=False)
    if error:
        return error

    semantic_type = fetch_semantic_type_row(payload["semantic_type_id"])
    if semantic_type is None or semantic_type["metamodel_version_id"] != existing["metamodel_version_id"]:
        return error_response("validation_error", "semantic_type_id must belong to the selected version", 400)
    if semantic_type["kind"] == "edge" and payload["kind"] != "edge":
        return error_response("validation_error", "edge semantic type requires edge notation kind", 400)
    if semantic_type["kind"] != "edge" and payload["kind"] != "node":
        return error_response("validation_error", "non-edge semantic type requires node notation kind", 400)

    if payload.get("palette_group_id") is not None:
        palette_group = get_db().execute(
            "SELECT 1 FROM palette_groups WHERE id = ? AND metamodel_version_id = ?",
            (payload["palette_group_id"], existing["metamodel_version_id"]),
        ).fetchone()
        if palette_group is None:
            return error_response("validation_error", "palette_group_id must belong to the selected version", 400)

    conflict = get_db().execute(
        """
        SELECT 1
        FROM notation_definitions
        WHERE metamodel_version_id = ? AND code = ? AND id != ?
        """,
        (existing["metamodel_version_id"], payload["code"], notation_id),
    ).fetchone()
    if conflict is not None:
        return error_response("notation_conflict", "notation code already exists in version", 409)

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE notation_definitions
        SET semantic_type_id = ?,
            palette_group_id = ?,
            code = ?,
            display_name = ?,
            kind = ?,
            render_primitive = ?,
            render_schema_json = ?,
            style_tokens_json = ?,
            is_default = ?,
            is_visible_in_palette = ?,
            sort_order = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            payload["semantic_type_id"],
            payload.get("palette_group_id"),
            payload["code"],
            payload["display_name"],
            payload["kind"],
            payload["render_primitive"],
            payload["render_schema_json"],
            payload.get("style_tokens_json"),
            int(payload["is_default"]),
            int(payload["is_visible_in_palette"]),
            payload["sort_order"],
            timestamp,
            notation_id,
        ),
    )

    if payload["is_default"]:
        update_default_notation(semantic_type_id=payload["semantic_type_id"], notation_id=notation_id, db_conn=db_conn)
    elif existing["is_default"] and existing["semantic_type_id"] == payload["semantic_type_id"]:
        update_default_notation(semantic_type_id=payload["semantic_type_id"], notation_id=None, db_conn=db_conn)

    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET updated_at = ?
        WHERE id = ?
        """,
        (timestamp, existing["metamodel_version_id"]),
    )
    db_conn.commit()

    updated = fetch_notation_row(notation_id)
    return {"notation_definition": serialize_notation_definition(updated)}


@bp.post("/notations/<int:notation_id>/clone")
@admin_required
def clone_notation(notation_id: int):
    existing = fetch_notation_row(notation_id)
    if existing is None:
        return error_response("notation_not_found", "notation definition not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft notation definitions can be cloned", 409)

    raw_payload = request.get_json(silent=True) or {}
    try:
        requested_code = parse_optional_string(raw_payload.get("code"), field_name="code", max_length=100)
        requested_display_name = parse_optional_string(
            raw_payload.get("display_name"),
            field_name="display_name",
            max_length=120,
        )
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    version_id = existing["metamodel_version_id"]
    clone_code = requested_code or build_unique_clone_text(
        existing["code"],
        max_length=100,
        exists_fn=lambda candidate: notation_code_exists(version_id, candidate),
        suffix_builder=lambda index: "_copy" if index == 1 else f"_copy{index}",
    )
    if notation_code_exists(version_id, clone_code):
        return error_response("notation_conflict", "notation code already exists in version", 409)

    clone_display_name = requested_display_name or build_unique_clone_text(
        existing["display_name"],
        max_length=120,
        exists_fn=lambda _candidate: False,
        suffix_builder=lambda index: " Copy" if index == 1 else f" Copy {index}",
    )

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO notation_definitions (
            metamodel_version_id, semantic_type_id, palette_group_id, code, display_name, kind,
            render_primitive, render_schema_json, style_tokens_json,
            is_default, is_visible_in_palette, sort_order, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
        """,
        (
            existing["metamodel_version_id"],
            existing["semantic_type_id"],
            existing["palette_group_id"],
            clone_code,
            clone_display_name,
            existing["kind"],
            existing["render_primitive"],
            existing["render_schema_json"],
            existing["style_tokens_json"],
            int(bool(existing["is_visible_in_palette"])),
            existing["sort_order"],
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
        (timestamp, existing["metamodel_version_id"]),
    )
    db_conn.commit()

    cloned = fetch_notation_row(int(cursor.lastrowid))
    return {
        "notation_definition": serialize_notation_definition(cloned),
        "clone_summary": {
            "default_copied_as_secondary": bool(existing["is_default"]),
        },
    }, 201


@bp.delete("/notations/<int:notation_id>")
@admin_required
def delete_notation(notation_id: int):
    existing = fetch_notation_row(notation_id)
    if existing is None:
        return error_response("notation_not_found", "notation definition not found", 404)
    if existing["metamodel_version_status"] != "draft":
        return error_response("invalid_state", "only draft notation definitions can be deleted", 409)

    blockers = fetch_notation_delete_blockers(notation_id)
    if any(blockers.values()):
        return {
            "error": {
                "code": "notation_in_use",
                "message": "notation definition cannot be deleted while it is used as a semantic type default notation",
            },
            "dependency_counts": blockers,
        }, 409

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute("DELETE FROM notation_definitions WHERE id = ?", (notation_id,))
    db_conn.execute(
        """
        UPDATE metamodel_versions
        SET updated_at = ?
        WHERE id = ?
        """,
        (timestamp, existing["metamodel_version_id"]),
    )
    db_conn.commit()

    return {
        "deleted": True,
        "notation_definition_id": notation_id,
    }
