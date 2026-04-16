from __future__ import annotations

import json
from typing import Any

from .db import get_db


def parse_json_or_none(raw_value: str | None) -> Any:
    if not raw_value:
        return None
    return json.loads(raw_value)


def fetch_metamodel_version_snapshot(metamodel_version_id: int) -> dict[str, Any] | None:
    db_conn = get_db()
    version_row = db_conn.execute(
        """
        SELECT mv.id, mv.namespace_id, mv.version_code, mv.status, mv.description, mv.published_at,
               ns.code AS namespace_code, ns.name AS namespace_name
        FROM metamodel_versions AS mv
        JOIN metamodel_namespaces AS ns ON ns.id = mv.namespace_id
        WHERE mv.id = ?
        """,
        (metamodel_version_id,),
    ).fetchone()
    if version_row is None:
        return None

    semantic_rows = db_conn.execute(
        """
        SELECT st.id, st.metamodel_version_id, st.code, st.display_name, st.description, st.kind, st.runtime_kind,
               st.is_groupable, st.allows_runtime_binding, st.default_notation_id, st.is_active,
               nd.code AS default_notation_code
        FROM semantic_types AS st
        LEFT JOIN notation_definitions AS nd ON nd.id = st.default_notation_id
        WHERE st.metamodel_version_id = ?
        ORDER BY st.kind ASC, st.code ASC
        """,
        (metamodel_version_id,),
    ).fetchall()

    property_rows = db_conn.execute(
        """
        SELECT pd.id, pd.semantic_type_id, st.code AS semantic_type_code,
               pd.code, pd.display_name, pd.description, pd.value_type, pd.unit,
               pd.default_value_json, pd.is_required, pd.is_runtime, pd.is_user_editable, pd.sort_order
        FROM property_definitions AS pd
        JOIN semantic_types AS st ON st.id = pd.semantic_type_id
        WHERE st.metamodel_version_id = ?
        ORDER BY st.code ASC, pd.sort_order ASC, pd.id ASC
        """,
        (metamodel_version_id,),
    ).fetchall()

    containment_rows = db_conn.execute(
        """
        SELECT cr.id, parent.id AS parent_type_id, parent.code AS parent_type_code, parent.display_name AS parent_type_display_name,
               child.id AS child_type_id, child.code AS child_type_code, child.display_name AS child_type_display_name,
               cr.min_count, cr.max_count, cr.cardinality_scope, cr.is_required
        FROM containment_rules AS cr
        JOIN semantic_types AS parent ON parent.id = cr.parent_type_id
        JOIN semantic_types AS child ON child.id = cr.child_type_id
        WHERE cr.metamodel_version_id = ?
        ORDER BY parent.code ASC, child.code ASC
        """,
        (metamodel_version_id,),
    ).fetchall()

    association_rows = db_conn.execute(
        """
        SELECT ad.id, ad.code, ad.display_name, ad.description, ad.direction,
               ad.multiplicity_source, ad.multiplicity_target, ad.semantics_json,
               source.id AS source_type_id, source.code AS source_type_code, source.display_name AS source_type_display_name,
               target.id AS target_type_id, target.code AS target_type_code, target.display_name AS target_type_display_name
        FROM association_definitions AS ad
        JOIN semantic_types AS source ON source.id = ad.source_type_id
        JOIN semantic_types AS target ON target.id = ad.target_type_id
        WHERE ad.metamodel_version_id = ?
        ORDER BY ad.code ASC
        """,
        (metamodel_version_id,),
    ).fetchall()

    notation_rows = db_conn.execute(
        """
        SELECT nd.id, nd.code, nd.display_name, nd.kind, nd.render_primitive, nd.render_schema_json,
               nd.style_tokens_json, nd.is_default, nd.is_visible_in_palette, nd.sort_order,
               st.id AS semantic_type_id, st.code AS semantic_type_code, st.display_name AS semantic_type_display_name,
               pg.id AS palette_group_id, pg.code AS palette_group_code, pg.label AS palette_group_label, pg.sort_order AS palette_group_sort_order
        FROM notation_definitions AS nd
        JOIN semantic_types AS st ON st.id = nd.semantic_type_id
        LEFT JOIN palette_groups AS pg ON pg.id = nd.palette_group_id
        WHERE nd.metamodel_version_id = ?
        ORDER BY nd.sort_order ASC, nd.id ASC
        """,
        (metamodel_version_id,),
    ).fetchall()

    palette_groups: dict[int, dict[str, Any]] = {}
    ordered_palette_groups: list[dict[str, Any]] = []
    notation_items: list[dict[str, Any]] = []
    for row in notation_rows:
        notation_item = {
            "id": row["id"],
            "code": row["code"],
            "display_name": row["display_name"],
            "kind": row["kind"],
            "semantic_type_id": row["semantic_type_id"],
            "semantic_type_code": row["semantic_type_code"],
            "semantic_type_display_name": row["semantic_type_display_name"],
            "palette_group_id": row["palette_group_id"],
            "palette_group_code": row["palette_group_code"],
            "render_primitive": row["render_primitive"],
            "render_schema": parse_json_or_none(row["render_schema_json"]),
            "style_tokens": parse_json_or_none(row["style_tokens_json"]),
            "is_default": bool(row["is_default"]),
            "is_visible_in_palette": bool(row["is_visible_in_palette"]),
            "sort_order": row["sort_order"],
        }
        notation_items.append(notation_item)
        if not notation_item["is_visible_in_palette"] or row["palette_group_id"] is None:
            continue
        group = palette_groups.get(row["palette_group_id"])
        if group is None:
            group = {
                "id": row["palette_group_id"],
                "code": row["palette_group_code"],
                "label": row["palette_group_label"],
                "sort_order": row["palette_group_sort_order"],
                "items": [],
            }
            palette_groups[row["palette_group_id"]] = group
            ordered_palette_groups.append(group)
        group["items"].append(
            {
                "notation_id": notation_item["id"],
                "notation_code": notation_item["code"],
                "display_name": notation_item["display_name"],
                "semantic_type_id": notation_item["semantic_type_id"],
                "semantic_type_code": notation_item["semantic_type_code"],
                "semantic_type_display_name": notation_item["semantic_type_display_name"],
                "render_primitive": notation_item["render_primitive"],
                "render_schema": notation_item["render_schema"],
                "style_tokens": notation_item["style_tokens"],
            }
        )

    return {
        "version": {
            "id": version_row["id"],
            "namespace_id": version_row["namespace_id"],
            "namespace_code": version_row["namespace_code"],
            "namespace_name": version_row["namespace_name"],
            "version_code": version_row["version_code"],
            "status": version_row["status"],
            "description": version_row["description"],
            "published_at": version_row["published_at"],
        },
        "semantic_types": [
            {
                "id": row["id"],
                "metamodel_version_id": row["metamodel_version_id"],
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
            }
            for row in semantic_rows
        ],
        "property_definitions": [
            {
                "id": row["id"],
                "semantic_type_id": row["semantic_type_id"],
                "semantic_type_code": row["semantic_type_code"],
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
            for row in property_rows
        ],
        "containment_rules": [
            {
                "id": row["id"],
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
            }
            for row in containment_rows
        ],
        "associations": [
            {
                "id": row["id"],
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
                "semantics": parse_json_or_none(row["semantics_json"]),
            }
            for row in association_rows
        ],
        "notations": notation_items,
        "palette_groups": ordered_palette_groups,
    }
