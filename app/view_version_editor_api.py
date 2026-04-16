from __future__ import annotations

import json
import re
from typing import Any

from flask import Blueprint, g, request

from .auth import error_response, login_required
from .editor_api import (
    EDGE_MUTABLE_FIELDS,
    NODE_MUTABLE_FIELDS,
    next_layer_order,
    resolve_layer_order,
)
from .view_versioning import (
    get_owned_view_version,
    now_iso,
    sync_primary_node_binding,
    serialize_view_version_edge,
    serialize_view_version_node,
    serialize_view_version,
)
from .view_metamodel import fetch_metamodel_version_snapshot
from .db import get_db

bp = Blueprint("view_version_editor_api", __name__, url_prefix="/api/view-versions")

NODE_SEMANTIC_KINDS = {"node", "container", "runtime-only"}
RESERVED_NODE_PROPERTY_CODES = {
    "display_name",
    "target_id",
    "instance_mode",
    "cardinality_scope",
    "expected_min",
    "expected_max",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") or "item"


def make_element_key(prefix: str, display_name: str, existing_keys: set[str]) -> str:
    base = f"{prefix}_{slugify(display_name)}"
    candidate = base
    counter = 2
    while candidate in existing_keys:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def require_draft_version(version_id: int):
    version_row = get_owned_view_version(version_id, g.user["id"])
    if version_row is None:
        return None, error_response("not_found", "view version not found", 404)
    if version_row["status"] != "draft":
        return None, error_response("version_state_conflict", "only draft versions can be edited", 409)
    return version_row, None


def fetch_version_metamodel(version_row) -> dict[str, Any] | None:
    metamodel_version_id = version_row["metamodel_version_id"]
    if metamodel_version_id is None:
        return None
    return fetch_metamodel_version_snapshot(metamodel_version_id)


def build_editor_metamodel(version_row) -> dict[str, Any]:
    snapshot = fetch_version_metamodel(version_row) or {
        "version": None,
        "semantic_types": [],
        "containment_rules": [],
        "associations": [],
        "notations": [],
        "palette_groups": [],
    }
    semantic_types_by_code = {item["code"]: item for item in snapshot["semantic_types"]}
    notation_by_code = {item["code"]: item for item in snapshot["notations"]}
    allowed_node_types = {
        item["code"]
        for item in snapshot["semantic_types"]
        if item["is_active"] and item["kind"] in NODE_SEMANTIC_KINDS
    }
    allowed_edge_types = {
        item["code"]
        for item in snapshot["semantic_types"]
        if item["is_active"] and item["kind"] == "edge"
    }
    containment_pairs = {
        (item["parent_type_code"], item["child_type_code"])
        for item in snapshot["containment_rules"]
    }
    property_definitions_by_type: dict[str, list[dict[str, Any]]] = {}
    for item in snapshot.get("property_definitions", []):
        property_definitions_by_type.setdefault(item["semantic_type_code"], []).append(item)
    allowed_parent_codes_by_child: dict[str, set[str]] = {}
    for item in snapshot["containment_rules"]:
        allowed_parent_codes_by_child.setdefault(item["child_type_code"], set()).add(item["parent_type_code"])
    return {
        "snapshot": snapshot,
        "semantic_types_by_code": semantic_types_by_code,
        "notation_by_code": notation_by_code,
        "allowed_node_types": allowed_node_types,
        "allowed_edge_types": allowed_edge_types,
        "containment_pairs": containment_pairs,
        "property_definitions_by_type": property_definitions_by_type,
        "allowed_parent_codes_by_child": allowed_parent_codes_by_child,
    }


def validate_property_value(value_type: str, value: Any) -> bool:
    if value_type == "string":
        return isinstance(value, str)
    if value_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "json":
        return True
    return True


def validate_node_properties(node: dict[str, Any], editor_metamodel: dict[str, Any]) -> str | None:
    semantic_type_code = node.get("semantic_type_code") or node["node_type"]
    raw_properties = node.get("properties") or {}
    if not isinstance(raw_properties, dict):
        return "properties must be an object"

    definitions = {
        item["code"]: item
        for item in editor_metamodel["property_definitions_by_type"].get(semantic_type_code, [])
        if item["is_user_editable"] and not item["is_runtime"] and item["code"] not in RESERVED_NODE_PROPERTY_CODES
    }
    unknown_codes = set(raw_properties) - set(definitions)
    if unknown_codes:
        return f"unknown property codes: {', '.join(sorted(unknown_codes))}"

    for code, definition in definitions.items():
        if definition["is_required"] and code not in raw_properties:
            return f"property '{code}' is required"
        if code in raw_properties and not validate_property_value(definition["value_type"], raw_properties[code]):
            return f"property '{code}' does not match value_type '{definition['value_type']}'"

    return None


def resolve_node_defaults(editor_metamodel: dict[str, Any], node_type: str) -> dict[str, Any] | None:
    semantic_type = editor_metamodel["semantic_types_by_code"].get(node_type)
    if semantic_type is None or semantic_type["code"] not in editor_metamodel["allowed_node_types"]:
        return None
    return {
        "semantic_type_code": semantic_type["code"],
        "notation_code": semantic_type.get("default_notation_code"),
    }


def resolve_edge_defaults(editor_metamodel: dict[str, Any], edge_type: str) -> dict[str, Any] | None:
    semantic_type = editor_metamodel["semantic_types_by_code"].get(edge_type)
    if semantic_type is None or semantic_type["code"] not in editor_metamodel["allowed_edge_types"]:
        return None
    return {
        "semantic_type_code": semantic_type["code"],
        "notation_code": semantic_type.get("default_notation_code"),
    }


def find_association_by_code(editor_metamodel: dict[str, Any], association_code: str) -> dict[str, Any] | None:
    return next(
        (item for item in editor_metamodel["snapshot"]["associations"] if item["code"] == association_code),
        None,
    )


def association_matches_nodes(
    association: dict[str, Any],
    source_type_code: str,
    target_type_code: str,
) -> bool:
    if association["direction"] == "undirected":
        return {
            association["source_type_code"],
            association["target_type_code"],
        } == {source_type_code, target_type_code}
    return (
        association["source_type_code"] == source_type_code
        and association["target_type_code"] == target_type_code
    )


def validate_nodes_against_metamodel(nodes: list[dict[str, Any]], editor_metamodel: dict[str, Any]) -> str | None:
    node_map: dict[int, dict[str, Any]] = {}
    required = {"id", "node_type", "display_name", "x", "y", "width", "height"}

    for node in nodes:
        missing = required - node.keys()
        if missing:
            return f"node is missing required fields: {', '.join(sorted(missing))}"

        node_type = node["node_type"]
        defaults = resolve_node_defaults(editor_metamodel, node_type)
        if defaults is None:
            return "invalid node_type"

        if node.get("semantic_type_code", defaults["semantic_type_code"]) != defaults["semantic_type_code"]:
            return "semantic_type_code does not match node_type"

        notation_code = node.get("notation_code", defaults["notation_code"])
        notation = editor_metamodel["notation_by_code"].get(notation_code)
        if notation is None or notation["semantic_type_code"] != defaults["semantic_type_code"] or notation["kind"] != "node":
            return "notation_code does not match node_type"
        if node.get("target_id") and not editor_metamodel["semantic_types_by_code"][defaults["semantic_type_code"]]["allows_runtime_binding"]:
            return "target_id is not allowed for this semantic type"
        property_error = validate_node_properties(node, editor_metamodel)
        if property_error:
            return property_error

        if not isinstance(node["id"], int):
            return "node id must be an integer"
        if node["id"] in node_map:
            return "duplicate node id is not allowed"
        if "layer_order" in node and not isinstance(node["layer_order"], int):
            return "layer_order must be an integer"

        node_map[node["id"]] = node

    allowed_parent_codes_by_child = editor_metamodel["allowed_parent_codes_by_child"]
    containment_pairs = editor_metamodel["containment_pairs"]

    for node in nodes:
        child_type = node["node_type"]
        parent_id = node.get("parent_node_id")
        allowed_parents = allowed_parent_codes_by_child.get(child_type, set())
        if not allowed_parents:
            if parent_id is not None:
                return f"{child_type} must not have a parent_node_id"
            continue
        if parent_id is None:
            return f"{child_type} must have a parent_node_id"

        parent_node = node_map.get(parent_id)
        if parent_node is None:
            return "parent_node_id must reference an existing node"
        if (parent_node["node_type"], child_type) not in containment_pairs:
            return "parent_node_id does not satisfy containment rules"

    return None


def validate_edges_against_metamodel(
    edges: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    editor_metamodel: dict[str, Any],
) -> str | None:
    node_by_id = {node["id"]: node for node in nodes}
    node_ids = set(node_by_id)
    seen_ids: set[int] = set()

    for edge in edges:
        missing = {"id", "edge_type", "source_node_id", "target_node_id"} - edge.keys()
        if missing:
            return f"edge is missing required fields: {', '.join(sorted(missing))}"

        edge_type = edge["edge_type"]
        defaults = resolve_edge_defaults(editor_metamodel, edge_type)
        if defaults is None:
            return "invalid edge_type"
        if edge.get("semantic_type_code", defaults["semantic_type_code"]) != defaults["semantic_type_code"]:
            return "semantic_type_code does not match edge_type"
        notation_code = edge.get("notation_code", defaults["notation_code"])
        notation = editor_metamodel["notation_by_code"].get(notation_code)
        if notation is None or notation["semantic_type_code"] != defaults["semantic_type_code"] or notation["kind"] != "edge":
            return "notation_code does not match edge_type"
        if not isinstance(edge["id"], int):
            return "edge id must be an integer"
        if edge["id"] in seen_ids:
            return "duplicate edge id is not allowed"
        seen_ids.add(edge["id"])
        if "layer_order" in edge and not isinstance(edge["layer_order"], int):
            return "layer_order must be an integer"
        if edge["source_node_id"] not in node_ids or edge["target_node_id"] not in node_ids:
            return "edge must reference existing nodes"

        source_node = node_by_id[edge["source_node_id"]]
        target_node = node_by_id[edge["target_node_id"]]
        source_type_code = source_node.get("semantic_type_code") or source_node["node_type"]
        target_type_code = target_node.get("semantic_type_code") or target_node["node_type"]

        association_code = edge.get("association_code")
        if association_code:
            association = find_association_by_code(editor_metamodel, association_code)
            if association is None:
                return "association_code is invalid"
            if not association_matches_nodes(association, source_type_code, target_type_code):
                return "association_code does not match source/target semantic types"
            default_edge_type = (association.get("semantics") or {}).get("default_edge_type")
            if default_edge_type and default_edge_type != edge_type:
                return "association_code does not match edge_type"

    return None


def require_revision(version_row, payload: dict[str, Any]):
    revision = payload.get("revision")
    if revision is None:
        return error_response("validation_error", "revision is required", 400)
    if revision != version_row["revision"]:
        return error_response("revision_mismatch", "revision mismatch", 409)
    return None


def get_current_nodes(version_id: int) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT id, element_key, parent_node_id, node_type, semantic_type_code, notation_code,
               display_name, target_id, instance_mode, cardinality_scope, expected_min, expected_max,
               layer_order, x, y, width, height, collapsed_state, style_json, properties_json,
               (SELECT monitored_object_id
                FROM node_bindings
                WHERE view_version_node_id = view_version_nodes.id AND binding_role = 'primary'
                ORDER BY id
                LIMIT 1) AS monitored_object_id
        FROM view_version_nodes
        WHERE view_version_id = ? AND is_deleted = 0
        ORDER BY layer_order ASC, id ASC
        """,
        (version_id,),
    ).fetchall()
    return [serialize_view_version_node(row) for row in rows]


def get_current_edges(version_id: int) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT id, element_key, edge_type, association_code, semantic_type_code, notation_code,
               source_node_id, target_node_id, source_element_key, target_element_key,
               layer_order, source_anchor, target_anchor, control_points_json, label, style_json
        FROM view_version_edges
        WHERE view_version_id = ? AND is_deleted = 0
        ORDER BY layer_order ASC, id ASC
        """,
        (version_id,),
    ).fetchall()
    return [serialize_view_version_edge(row) for row in rows]


def get_node_row(version_id: int, node_id: int):
    return get_db().execute(
        """
        SELECT id, element_key, parent_node_id, node_type, semantic_type_code, notation_code,
               display_name, target_id, instance_mode, cardinality_scope, expected_min, expected_max,
               layer_order, x, y, width, height, collapsed_state, style_json, properties_json,
               (SELECT monitored_object_id
                FROM node_bindings
                WHERE view_version_node_id = view_version_nodes.id AND binding_role = 'primary'
                ORDER BY id
                LIMIT 1) AS monitored_object_id
        FROM view_version_nodes
        WHERE view_version_id = ? AND id = ? AND is_deleted = 0
        """,
        (version_id, node_id),
    ).fetchone()


def get_edge_row(version_id: int, edge_id: int):
    return get_db().execute(
        """
        SELECT id, element_key, edge_type, association_code, semantic_type_code, notation_code,
               source_node_id, target_node_id, source_element_key, target_element_key,
               layer_order, source_anchor, target_anchor, control_points_json, label, style_json
        FROM view_version_edges
        WHERE view_version_id = ? AND id = ? AND is_deleted = 0
        """,
        (version_id, edge_id),
    ).fetchone()


def bump_version_revision(version_id: int) -> tuple[int, str]:
    timestamp = now_iso()
    db_conn = get_db()
    current_revision = db_conn.execute(
        "SELECT revision FROM view_versions WHERE id = ?",
        (version_id,),
    ).fetchone()["revision"]
    next_revision = current_revision + 1
    db_conn.execute(
        "UPDATE view_versions SET revision = ?, updated_at = ? WHERE id = ?",
        (next_revision, timestamp, version_id),
    )
    return next_revision, timestamp


def replace_version_layout(version_id: int, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], updated_at: str) -> None:
    db_conn = get_db()
    db_conn.execute("DELETE FROM view_version_edges WHERE view_version_id = ?", (version_id,))
    db_conn.execute("DELETE FROM view_version_nodes WHERE view_version_id = ?", (version_id,))

    sorted_nodes = sorted(
        nodes,
        key=lambda item: (
            item.get("parent_node_id") is not None,
            int(item.get("layer_order", 0)),
            item["id"],
        ),
    )
    for node in sorted_nodes:
        cursor = db_conn.execute(
            """
            INSERT INTO view_version_nodes (
                id, view_version_id, element_key, parent_node_id, node_type, semantic_type_code, notation_code,
                display_name, target_id, instance_mode, cardinality_scope, expected_min, expected_max,
                layer_order, x, y, width, height, collapsed_state, is_deleted, style_json, properties_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                node["id"],
                version_id,
                node["element_key"],
                node.get("parent_node_id"),
                node["node_type"],
                node["semantic_type_code"],
                node["notation_code"],
                node["display_name"],
                node.get("target_id"),
                node.get("instance_mode"),
                node.get("cardinality_scope"),
                node.get("expected_min"),
                node.get("expected_max"),
                node.get("layer_order", 0),
                node["x"],
                node["y"],
                node["width"],
                node["height"],
                int(bool(node.get("collapsed_state", False))),
                json.dumps(node.get("style")) if "style" in node else None,
                json.dumps(node.get("properties")) if "properties" in node else None,
                updated_at,
                updated_at,
            ),
        )
        sync_primary_node_binding(
            view_version_node_id=cursor.lastrowid if cursor.lastrowid is not None else node["id"],
            target_id=node.get("target_id"),
            timestamp=updated_at,
        )

    for edge in edges:
        db_conn.execute(
            """
            INSERT INTO view_version_edges (
                id, view_version_id, element_key, edge_type, association_code, semantic_type_code, notation_code,
                source_node_id, target_node_id, source_element_key, target_element_key,
                layer_order, source_anchor, target_anchor, control_points_json, label, style_json, is_deleted,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                edge["id"],
                version_id,
                edge["element_key"],
                edge["edge_type"],
                edge.get("association_code"),
                edge["semantic_type_code"],
                edge["notation_code"],
                edge["source_node_id"],
                edge["target_node_id"],
                edge.get("source_element_key"),
                edge.get("target_element_key"),
                edge.get("layer_order", 0),
                edge.get("source_anchor"),
                edge.get("target_anchor"),
                json.dumps(edge.get("control_points", [])),
                edge.get("label"),
                json.dumps(edge.get("style")) if "style" in edge else None,
                updated_at,
                updated_at,
            ),
        )


@bp.get("/<int:version_id>/metamodel")
@login_required
def get_version_metamodel(version_id: int):
    version_row = get_owned_view_version(version_id, g.user["id"])
    if version_row is None:
        return error_response("not_found", "view version not found", 404)
    snapshot = fetch_version_metamodel(version_row)
    if snapshot is None:
        return error_response("metamodel_not_found", "view version metamodel not found", 404)
    version_payload = serialize_view_version(
        {
            **dict(version_row),
            "metamodel_version_code": snapshot["version"]["version_code"],
        }
    )
    return {
        "version": version_payload,
        "metamodel": snapshot,
    }


@bp.post("/<int:version_id>/nodes")
@login_required
def create_node(version_id: int):
    version_row, error = require_draft_version(version_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(version_row, payload)
    if revision_error:
        return revision_error

    missing = {"node_type", "display_name", "x", "y", "width", "height"} - payload.keys()
    if missing:
        return error_response("validation_error", f"node is missing required fields: {', '.join(sorted(missing))}", 400)
    editor_metamodel = build_editor_metamodel(version_row)
    node_defaults = resolve_node_defaults(editor_metamodel, payload["node_type"])
    if node_defaults is None:
        return error_response("validation_error", "invalid node_type", 400)

    current_nodes = get_current_nodes(version_id)
    temp_id = -1 * (max((node["id"] for node in current_nodes), default=0) + 1)
    try:
        layer_order = resolve_layer_order(payload.get("layer_order"), next_layer_order(current_nodes))
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    node_type = payload["node_type"]
    existing_keys = {node["element_key"] for node in current_nodes}
    candidate = {
        "id": temp_id,
        "element_key": payload.get("element_key") or make_element_key(node_type.lower(), payload["display_name"], existing_keys),
        "parent_node_id": payload.get("parent_node_id"),
        "node_type": node_type,
        "semantic_type_code": payload.get("semantic_type_code", node_defaults["semantic_type_code"]),
        "notation_code": payload.get("notation_code", node_defaults["notation_code"]),
        "display_name": payload["display_name"],
        "target_id": payload.get("target_id"),
        "properties": payload.get("properties", {}),
        "layer_order": layer_order,
        "x": payload["x"],
        "y": payload["y"],
        "width": payload["width"],
        "height": payload["height"],
        "collapsed_state": False,
    }
    if "style" in payload:
        candidate["style"] = payload["style"]

    validation_error = validate_nodes_against_metamodel(current_nodes + [candidate], editor_metamodel)
    if validation_error:
        return error_response("validation_error", validation_error, 400)

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO view_version_nodes (
            view_version_id, element_key, parent_node_id, node_type, semantic_type_code, notation_code,
            display_name, target_id, instance_mode, cardinality_scope, expected_min, expected_max,
            layer_order, x, y, width, height, collapsed_state, is_deleted, style_json, properties_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?)
        """,
        (
            version_id,
            candidate["element_key"],
            payload.get("parent_node_id"),
            node_type,
            candidate["semantic_type_code"],
            candidate["notation_code"],
            payload["display_name"],
            payload.get("target_id"),
            candidate["layer_order"],
            payload["x"],
            payload["y"],
            payload["width"],
            payload["height"],
            json.dumps(payload.get("style")) if "style" in payload else None,
            json.dumps(payload.get("properties", {})),
            timestamp,
            timestamp,
        ),
    )
    sync_primary_node_binding(
        view_version_node_id=cursor.lastrowid,
        target_id=payload.get("target_id"),
        timestamp=timestamp,
    )
    next_revision, updated_at = bump_version_revision(version_id)
    db_conn.commit()

    return {
        "node": serialize_view_version_node(get_node_row(version_id, cursor.lastrowid)),
        "revision": next_revision,
        "updated_at": updated_at,
    }, 201


@bp.patch("/<int:version_id>/nodes/<int:node_id>")
@login_required
def update_node(version_id: int, node_id: int):
    version_row, error = require_draft_version(version_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(version_row, payload)
    if revision_error:
        return revision_error

    node_row = get_node_row(version_id, node_id)
    if node_row is None:
        return error_response("not_found", "node not found", 404)
    editor_metamodel = build_editor_metamodel(version_row)

    unknown = set(payload.keys()) - (NODE_MUTABLE_FIELDS | {"revision"})
    if unknown:
        return error_response("validation_error", f"unknown fields: {', '.join(sorted(unknown))}", 400)

    current_nodes = get_current_nodes(version_id)
    merged = next(node for node in current_nodes if node["id"] == node_id).copy()
    for field in NODE_MUTABLE_FIELDS:
        if field in payload:
            merged[field] = payload[field]

    validation_error = validate_nodes_against_metamodel(
        [merged if node["id"] == node_id else node for node in current_nodes],
        editor_metamodel,
    )
    if validation_error:
        return error_response("validation_error", validation_error, 400)

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE view_version_nodes
        SET parent_node_id = ?, display_name = ?, target_id = ?, layer_order = ?, x = ?, y = ?, width = ?, height = ?,
            style_json = ?, properties_json = ?, updated_at = ?
        WHERE id = ? AND view_version_id = ?
        """,
        (
            merged.get("parent_node_id"),
            merged["display_name"],
            merged.get("target_id"),
            merged.get("layer_order", 0),
            merged["x"],
            merged["y"],
            merged["width"],
            merged["height"],
            json.dumps(merged.get("style")) if "style" in merged else None,
            json.dumps(merged.get("properties", {})),
            timestamp,
            node_id,
            version_id,
        ),
    )
    sync_primary_node_binding(
        view_version_node_id=node_id,
        target_id=merged.get("target_id"),
        timestamp=timestamp,
    )
    next_revision, updated_at = bump_version_revision(version_id)
    db_conn.commit()

    return {
        "node": serialize_view_version_node(get_node_row(version_id, node_id)),
        "revision": next_revision,
        "updated_at": updated_at,
    }


@bp.delete("/<int:version_id>/nodes/<int:node_id>")
@login_required
def delete_node(version_id: int, node_id: int):
    version_row, error = require_draft_version(version_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(version_row, payload)
    if revision_error:
        return revision_error

    if get_node_row(version_id, node_id) is None:
        return error_response("not_found", "node not found", 404)

    db_conn = get_db()
    db_conn.execute("DELETE FROM view_version_nodes WHERE id = ? AND view_version_id = ?", (node_id, version_id))
    next_revision, updated_at = bump_version_revision(version_id)
    db_conn.commit()

    return {"ok": True, "deleted_node_id": node_id, "revision": next_revision, "updated_at": updated_at}


@bp.post("/<int:version_id>/edges")
@login_required
def create_edge(version_id: int):
    version_row, error = require_draft_version(version_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(version_row, payload)
    if revision_error:
        return revision_error

    missing = {"edge_type", "source_node_id", "target_node_id"} - payload.keys()
    if missing:
        return error_response("validation_error", f"edge is missing required fields: {', '.join(sorted(missing))}", 400)
    editor_metamodel = build_editor_metamodel(version_row)
    edge_defaults = resolve_edge_defaults(editor_metamodel, payload["edge_type"])
    if edge_defaults is None:
        return error_response("validation_error", "invalid edge_type", 400)

    current_nodes = get_current_nodes(version_id)
    current_edges = get_current_edges(version_id)
    temp_id = -1 * (max((edge["id"] for edge in current_edges), default=0) + 1)
    try:
        layer_order = resolve_layer_order(payload.get("layer_order"), next_layer_order(current_edges))
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    edge_type = payload["edge_type"]
    existing_keys = {edge["element_key"] for edge in current_edges}
    source_element = next((node["element_key"] for node in current_nodes if node["id"] == payload["source_node_id"]), None)
    target_element = next((node["element_key"] for node in current_nodes if node["id"] == payload["target_node_id"]), None)
    candidate = {
        "id": temp_id,
        "element_key": payload.get("element_key") or make_element_key("edge", payload.get("label") or edge_type, existing_keys),
        "edge_type": edge_type,
        "association_code": payload.get("association_code"),
        "semantic_type_code": payload.get("semantic_type_code", edge_defaults["semantic_type_code"]),
        "notation_code": payload.get("notation_code", edge_defaults["notation_code"]),
        "source_node_id": payload["source_node_id"],
        "target_node_id": payload["target_node_id"],
        "source_element_key": payload.get("source_element_key", source_element),
        "target_element_key": payload.get("target_element_key", target_element),
        "layer_order": layer_order,
        "source_anchor": payload.get("source_anchor"),
        "target_anchor": payload.get("target_anchor"),
        "control_points": payload.get("control_points", []),
    }
    if "label" in payload:
        candidate["label"] = payload["label"]
    if "style" in payload:
        candidate["style"] = payload["style"]

    validation_error = validate_edges_against_metamodel(
        current_edges + [candidate],
        current_nodes,
        editor_metamodel,
    )
    if validation_error:
        return error_response("validation_error", validation_error, 400)

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO view_version_edges (
            view_version_id, element_key, edge_type, association_code, semantic_type_code, notation_code,
            source_node_id, target_node_id, source_element_key, target_element_key,
            layer_order, source_anchor, target_anchor, control_points_json, label, style_json, is_deleted,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            version_id,
            candidate["element_key"],
            edge_type,
            candidate.get("association_code"),
            candidate["semantic_type_code"],
            candidate["notation_code"],
            payload["source_node_id"],
            payload["target_node_id"],
            candidate.get("source_element_key"),
            candidate.get("target_element_key"),
            candidate["layer_order"],
            payload.get("source_anchor"),
            payload.get("target_anchor"),
            json.dumps(payload.get("control_points", [])),
            payload.get("label"),
            json.dumps(payload.get("style")) if "style" in payload else None,
            timestamp,
            timestamp,
        ),
    )
    next_revision, updated_at = bump_version_revision(version_id)
    db_conn.commit()

    return {
        "edge": serialize_view_version_edge(get_edge_row(version_id, cursor.lastrowid)),
        "revision": next_revision,
        "updated_at": updated_at,
    }, 201


@bp.patch("/<int:version_id>/edges/<int:edge_id>")
@login_required
def update_edge(version_id: int, edge_id: int):
    version_row, error = require_draft_version(version_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(version_row, payload)
    if revision_error:
        return revision_error

    edge_row = get_edge_row(version_id, edge_id)
    if edge_row is None:
        return error_response("not_found", "edge not found", 404)
    editor_metamodel = build_editor_metamodel(version_row)

    unknown = set(payload.keys()) - (EDGE_MUTABLE_FIELDS | {"revision"})
    if unknown:
        return error_response("validation_error", f"unknown fields: {', '.join(sorted(unknown))}", 400)

    current_nodes = get_current_nodes(version_id)
    current_edges = get_current_edges(version_id)
    merged = next(edge for edge in current_edges if edge["id"] == edge_id).copy()
    for field in EDGE_MUTABLE_FIELDS:
        if field in payload:
            merged[field] = payload[field]

    validation_error = validate_edges_against_metamodel(
        [merged if edge["id"] == edge_id else edge for edge in current_edges],
        current_nodes,
        editor_metamodel,
    )
    if validation_error:
        return error_response("validation_error", validation_error, 400)

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE view_version_edges
        SET source_node_id = ?, target_node_id = ?, layer_order = ?, source_anchor = ?, target_anchor = ?,
            control_points_json = ?, label = ?, style_json = ?, updated_at = ?
        WHERE id = ? AND view_version_id = ?
        """,
        (
            merged["source_node_id"],
            merged["target_node_id"],
            merged.get("layer_order", 0),
            merged.get("source_anchor"),
            merged.get("target_anchor"),
            json.dumps(merged.get("control_points", [])),
            merged.get("label"),
            json.dumps(merged.get("style")) if "style" in merged else None,
            timestamp,
            edge_id,
            version_id,
        ),
    )
    next_revision, updated_at = bump_version_revision(version_id)
    db_conn.commit()

    return {
        "edge": serialize_view_version_edge(get_edge_row(version_id, edge_id)),
        "revision": next_revision,
        "updated_at": updated_at,
    }


@bp.delete("/<int:version_id>/edges/<int:edge_id>")
@login_required
def delete_edge(version_id: int, edge_id: int):
    version_row, error = require_draft_version(version_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(version_row, payload)
    if revision_error:
        return revision_error

    if get_edge_row(version_id, edge_id) is None:
        return error_response("not_found", "edge not found", 404)

    db_conn = get_db()
    db_conn.execute("DELETE FROM view_version_edges WHERE id = ? AND view_version_id = ?", (edge_id, version_id))
    next_revision, updated_at = bump_version_revision(version_id)
    db_conn.commit()

    return {"ok": True, "deleted_edge_id": edge_id, "revision": next_revision, "updated_at": updated_at}


@bp.put("/<int:version_id>")
@login_required
def replace_version(version_id: int):
    version_row, error = require_draft_version(version_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision = payload.get("revision")
    nodes = payload.get("nodes")
    edges = payload.get("edges")

    if revision is None or nodes is None or edges is None:
        return error_response("validation_error", "revision, nodes and edges are required", 400)
    if revision != version_row["revision"]:
        return error_response("revision_mismatch", "revision mismatch", 409)

    if not isinstance(nodes, list) or not isinstance(edges, list):
        return error_response("validation_error", "nodes and edges must be lists", 400)

    editor_metamodel = build_editor_metamodel(version_row)
    current_nodes = get_current_nodes(version_id)
    current_edges = get_current_edges(version_id)
    existing_node_ids = {node["id"] for node in current_nodes}
    existing_edge_ids = {edge["id"] for edge in current_edges}
    existing_node_keys = {node["element_key"] for node in current_nodes}
    existing_edge_keys = {edge["element_key"] for edge in current_edges}

    normalized_nodes: list[dict[str, Any]] = []
    used_node_ids: set[int] = set()
    used_node_keys: set[str] = set()
    next_generated_node_id = max(existing_node_ids or {0}, default=0)

    for node in nodes:
        if not isinstance(node, dict):
            return error_response("validation_error", "each node must be an object", 400)
        normalized = dict(node)
        node_type = normalized.get("node_type")
        node_defaults = resolve_node_defaults(editor_metamodel, node_type)
        if node_defaults is None:
            return error_response("validation_error", "invalid node_type", 400)
        if not isinstance(normalized.get("id"), int):
            next_generated_node_id += 1
            normalized["id"] = next_generated_node_id
        if normalized["id"] in used_node_ids:
            return error_response("validation_error", "duplicate node id is not allowed", 400)
        used_node_ids.add(normalized["id"])
        element_key = normalized.get("element_key")
        if not element_key:
            element_key = make_element_key(node_type.lower(), str(normalized.get("display_name", node_type)), existing_node_keys | used_node_keys)
            normalized["element_key"] = element_key
        if element_key in used_node_keys:
            return error_response("validation_error", "duplicate node element_key is not allowed", 400)
        used_node_keys.add(element_key)
        normalized.setdefault("semantic_type_code", node_defaults["semantic_type_code"])
        normalized.setdefault("notation_code", node_defaults["notation_code"])
        normalized_nodes.append(normalized)

    node_validation_error = validate_nodes_against_metamodel(normalized_nodes, editor_metamodel)
    if node_validation_error:
        return error_response("validation_error", node_validation_error, 400)

    normalized_edges: list[dict[str, Any]] = []
    used_edge_ids: set[int] = set()
    used_edge_keys: set[str] = set()
    next_generated_edge_id = max(existing_edge_ids or {0}, default=0)
    node_key_by_id = {node["id"]: node["element_key"] for node in normalized_nodes}

    for edge in edges:
        if not isinstance(edge, dict):
            return error_response("validation_error", "each edge must be an object", 400)
        normalized = dict(edge)
        edge_type = normalized.get("edge_type")
        edge_defaults = resolve_edge_defaults(editor_metamodel, edge_type)
        if edge_defaults is None:
            return error_response("validation_error", "invalid edge_type", 400)
        if not isinstance(normalized.get("id"), int):
            next_generated_edge_id += 1
            normalized["id"] = next_generated_edge_id
        if normalized["id"] in used_edge_ids:
            return error_response("validation_error", "duplicate edge id is not allowed", 400)
        used_edge_ids.add(normalized["id"])
        element_key = normalized.get("element_key")
        if not element_key:
            element_key = make_element_key("edge", str(normalized.get("label", edge_type)), existing_edge_keys | used_edge_keys)
            normalized["element_key"] = element_key
        if element_key in used_edge_keys:
            return error_response("validation_error", "duplicate edge element_key is not allowed", 400)
        used_edge_keys.add(element_key)
        normalized.setdefault("semantic_type_code", edge_defaults["semantic_type_code"])
        normalized.setdefault("notation_code", edge_defaults["notation_code"])
        normalized.setdefault("source_element_key", node_key_by_id.get(normalized.get("source_node_id")))
        normalized.setdefault("target_element_key", node_key_by_id.get(normalized.get("target_node_id")))
        normalized_edges.append(normalized)

    edge_validation_error = validate_edges_against_metamodel(
        normalized_edges,
        normalized_nodes,
        editor_metamodel,
    )
    if edge_validation_error:
        return error_response("validation_error", edge_validation_error, 400)

    timestamp = now_iso()
    db_conn = get_db()
    replace_version_layout(version_id, normalized_nodes, normalized_edges, timestamp)
    next_revision = version_row["revision"] + 1
    db_conn.execute(
        "UPDATE view_versions SET revision = ?, updated_at = ? WHERE id = ?",
        (next_revision, timestamp, version_id),
    )
    db_conn.commit()

    return {"ok": True, "revision": next_revision, "updated_at": timestamp}
