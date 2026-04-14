from __future__ import annotations

import json
from typing import Any

from flask import Blueprint, request

from .auth import error_response, login_required
from .db import get_db

bp = Blueprint("metamodel_api", __name__, url_prefix="/api/metamodel")


def parse_json_or_none(raw_value: str | None) -> Any:
    if not raw_value:
        return None
    return json.loads(raw_value)


def get_published_version_row(version_id: int):
    row = get_db().execute(
        """
        SELECT mv.id, mv.namespace_id, mv.version_code, mv.status, mv.description, mv.published_at,
               ns.code AS namespace_code, ns.name AS namespace_name
        FROM metamodel_versions AS mv
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE mv.id = ? AND mv.status = 'published'
        """,
        (version_id,),
    ).fetchone()
    if row is None:
        return None
    return row


def serialize_version(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "namespace_id": row["namespace_id"],
        "namespace_code": row["namespace_code"],
        "namespace_name": row["namespace_name"],
        "version_code": row["version_code"],
        "status": row["status"],
        "description": row["description"],
        "published_at": row["published_at"],
    }


@bp.get("/versions/published")
@login_required
def list_published_versions():
    rows = get_db().execute(
        """
        SELECT mv.id, mv.namespace_id, mv.version_code, mv.status, mv.description, mv.published_at,
               ns.code AS namespace_code, ns.name AS namespace_name
        FROM metamodel_versions AS mv
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE mv.status = 'published'
        ORDER BY ns.code ASC, mv.version_code ASC
        """
    ).fetchall()
    return {"items": [serialize_version(row) for row in rows]}


@bp.get("/versions/<int:version_id>")
@login_required
def get_version(version_id: int):
    row = get_published_version_row(version_id)
    if row is None:
        return error_response("metamodel_not_found", "published metamodel version not found", 404)
    return {"version": serialize_version(row)}


@bp.get("/versions/<int:version_id>/palette")
@login_required
def get_palette(version_id: int):
    version_row = get_published_version_row(version_id)
    if version_row is None:
        return error_response("metamodel_not_found", "published metamodel version not found", 404)

    rows = get_db().execute(
        """
        SELECT pg.id AS palette_group_id, pg.code AS palette_group_code, pg.label AS palette_group_label, pg.sort_order AS palette_group_sort_order,
               nd.id AS notation_id, nd.code AS notation_code, nd.display_name AS notation_display_name,
               nd.render_primitive, nd.render_schema_json, nd.style_tokens_json, nd.sort_order AS notation_sort_order,
               st.id AS semantic_type_id, st.code AS semantic_type_code, st.display_name AS semantic_type_display_name
        FROM palette_groups AS pg
        JOIN notation_definitions AS nd
            ON nd.palette_group_id = pg.id AND nd.is_visible_in_palette = 1
        JOIN semantic_types AS st
            ON st.id = nd.semantic_type_id
        WHERE pg.metamodel_version_id = ? AND nd.metamodel_version_id = ?
        ORDER BY pg.sort_order ASC, pg.id ASC, nd.sort_order ASC, nd.id ASC
        """,
        (version_id, version_id),
    ).fetchall()

    groups_by_id: dict[int, dict[str, Any]] = {}
    ordered_groups: list[dict[str, Any]] = []
    for row in rows:
        group = groups_by_id.get(row["palette_group_id"])
        if group is None:
            group = {
                "id": row["palette_group_id"],
                "code": row["palette_group_code"],
                "label": row["palette_group_label"],
                "sort_order": row["palette_group_sort_order"],
                "items": [],
            }
            groups_by_id[row["palette_group_id"]] = group
            ordered_groups.append(group)

        group["items"].append(
            {
                "notation_id": row["notation_id"],
                "notation_code": row["notation_code"],
                "display_name": row["notation_display_name"],
                "semantic_type_id": row["semantic_type_id"],
                "semantic_type_code": row["semantic_type_code"],
                "semantic_type_display_name": row["semantic_type_display_name"],
                "render_primitive": row["render_primitive"],
                "render_schema": parse_json_or_none(row["render_schema_json"]),
                "style_tokens": parse_json_or_none(row["style_tokens_json"]),
            }
        )

    return {"palette_groups": ordered_groups}


@bp.get("/versions/<int:version_id>/semantic-types")
@login_required
def list_semantic_types(version_id: int):
    version_row = get_published_version_row(version_id)
    if version_row is None:
        return error_response("metamodel_not_found", "published metamodel version not found", 404)

    rows = get_db().execute(
        """
        SELECT st.id, st.code, st.display_name, st.description, st.kind, st.runtime_kind,
               st.is_groupable, st.allows_runtime_binding, st.is_active,
               nd.code AS default_notation_code
        FROM semantic_types AS st
        LEFT JOIN notation_definitions AS nd ON nd.id = st.default_notation_id
        WHERE st.metamodel_version_id = ?
        ORDER BY st.kind ASC, st.code ASC
        """,
        (version_id,),
    ).fetchall()

    return {
        "items": [
            {
                "id": row["id"],
                "code": row["code"],
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
        ]
    }


@bp.get("/versions/<int:version_id>/semantic-types/<string:type_code>/properties")
@login_required
def get_type_properties(version_id: int, type_code: str):
    version_row = get_published_version_row(version_id)
    if version_row is None:
        return error_response("metamodel_not_found", "published metamodel version not found", 404)

    type_row = get_db().execute(
        """
        SELECT id, code
        FROM semantic_types
        WHERE metamodel_version_id = ? AND code = ?
        """,
        (version_id, type_code),
    ).fetchone()
    if type_row is None:
        return error_response("semantic_type_not_found", "semantic type not found", 404)

    rows = get_db().execute(
        """
        SELECT code, display_name, description, value_type, unit, default_value_json,
               is_required, is_runtime, is_user_editable, sort_order
        FROM property_definitions
        WHERE semantic_type_id = ?
        ORDER BY sort_order ASC, id ASC
        """,
        (type_row["id"],),
    ).fetchall()

    return {
        "semantic_type_code": type_row["code"],
        "items": [
            {
                "code": row["code"],
                "display_name": row["display_name"],
                "description": row["description"],
                "value_type": row["value_type"],
                "unit": row["unit"],
                "default_value": parse_json_or_none(row["default_value_json"]),
                "is_required": bool(row["is_required"]),
                "is_runtime": bool(row["is_runtime"]),
                "is_user_editable": bool(row["is_user_editable"]),
                "sort_order": row["sort_order"],
            }
            for row in rows
        ],
    }


@bp.get("/versions/<int:version_id>/containment-rules")
@login_required
def list_containment_rules(version_id: int):
    version_row = get_published_version_row(version_id)
    if version_row is None:
        return error_response("metamodel_not_found", "published metamodel version not found", 404)

    rows = get_db().execute(
        """
        SELECT cr.id, parent.code AS parent_type_code, child.code AS child_type_code,
               cr.min_count, cr.max_count, cr.cardinality_scope, cr.is_required
        FROM containment_rules AS cr
        JOIN semantic_types AS parent ON parent.id = cr.parent_type_id
        JOIN semantic_types AS child ON child.id = cr.child_type_id
        WHERE cr.metamodel_version_id = ?
        ORDER BY parent.code ASC, child.code ASC
        """,
        (version_id,),
    ).fetchall()

    return {
        "items": [
            {
                "id": row["id"],
                "parent_type_code": row["parent_type_code"],
                "child_type_code": row["child_type_code"],
                "min_count": row["min_count"],
                "max_count": row["max_count"],
                "cardinality_scope": row["cardinality_scope"],
                "is_required": bool(row["is_required"]),
            }
            for row in rows
        ]
    }


@bp.get("/versions/<int:version_id>/associations")
@login_required
def list_associations(version_id: int):
    version_row = get_published_version_row(version_id)
    if version_row is None:
        return error_response("metamodel_not_found", "published metamodel version not found", 404)

    rows = get_db().execute(
        """
        SELECT ad.id, ad.code, ad.display_name, ad.description, ad.direction,
               ad.multiplicity_source, ad.multiplicity_target, ad.semantics_json,
               source.code AS source_type_code, target.code AS target_type_code
        FROM association_definitions AS ad
        JOIN semantic_types AS source ON source.id = ad.source_type_id
        JOIN semantic_types AS target ON target.id = ad.target_type_id
        WHERE ad.metamodel_version_id = ?
        ORDER BY ad.code ASC
        """,
        (version_id,),
    ).fetchall()

    return {
        "items": [
            {
                "id": row["id"],
                "code": row["code"],
                "display_name": row["display_name"],
                "description": row["description"],
                "source_type_code": row["source_type_code"],
                "target_type_code": row["target_type_code"],
                "direction": row["direction"],
                "multiplicity_source": row["multiplicity_source"],
                "multiplicity_target": row["multiplicity_target"],
                "semantics": parse_json_or_none(row["semantics_json"]),
            }
            for row in rows
        ]
    }


@bp.get("/versions/<int:version_id>/notations")
@login_required
def list_notations(version_id: int):
    version_row = get_published_version_row(version_id)
    if version_row is None:
        return error_response("metamodel_not_found", "published metamodel version not found", 404)

    semantic_type_code = request.args.get("semantic_type_code")
    palette_only = request.args.get("palette_only") == "1"

    sql = """
        SELECT nd.id, nd.code, nd.display_name, nd.kind, nd.render_primitive,
               nd.render_schema_json, nd.style_tokens_json, nd.is_default,
               nd.is_visible_in_palette, nd.sort_order,
               st.id AS semantic_type_id, st.code AS semantic_type_code, st.display_name AS semantic_type_display_name,
               pg.code AS palette_group_code
        FROM notation_definitions AS nd
        JOIN semantic_types AS st ON st.id = nd.semantic_type_id
        LEFT JOIN palette_groups AS pg ON pg.id = nd.palette_group_id
        WHERE nd.metamodel_version_id = ?
    """
    params: list[Any] = [version_id]
    if semantic_type_code:
        sql += " AND st.code = ?"
        params.append(semantic_type_code)
    if palette_only:
        sql += " AND nd.is_visible_in_palette = 1"

    sql += " ORDER BY nd.sort_order ASC, nd.id ASC"

    rows = get_db().execute(sql, tuple(params)).fetchall()
    return {
        "items": [
            {
                "id": row["id"],
                "code": row["code"],
                "display_name": row["display_name"],
                "kind": row["kind"],
                "semantic_type_id": row["semantic_type_id"],
                "semantic_type_code": row["semantic_type_code"],
                "semantic_type_display_name": row["semantic_type_display_name"],
                "palette_group_code": row["palette_group_code"],
                "render_primitive": row["render_primitive"],
                "render_schema": parse_json_or_none(row["render_schema_json"]),
                "style_tokens": parse_json_or_none(row["style_tokens_json"]),
                "is_default": bool(row["is_default"]),
                "is_visible_in_palette": bool(row["is_visible_in_palette"]),
                "sort_order": row["sort_order"],
            }
            for row in rows
        ]
    }
