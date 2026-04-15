from __future__ import annotations

import json
import re
from typing import Any

from flask import Blueprint, g, request

from .auth import error_response, login_required
from .editor_api import (
    EDGE_METAMODEL_DEFAULTS,
    EDGE_MUTABLE_FIELDS,
    NODE_METAMODEL_DEFAULTS,
    NODE_MUTABLE_FIELDS,
    next_layer_order,
    resolve_layer_order,
    validate_edges,
    validate_nodes,
)
from .view_versioning import (
    get_owned_view_version,
    now_iso,
    sync_primary_node_binding,
    serialize_view_version_edge,
    serialize_view_version_node,
)
from .db import get_db

bp = Blueprint("view_version_editor_api", __name__, url_prefix="/api/view-versions")


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
    if payload["node_type"] not in NODE_METAMODEL_DEFAULTS:
        return error_response("validation_error", "invalid node_type", 400)

    current_nodes = get_current_nodes(version_id)
    temp_id = -1 * (max((node["id"] for node in current_nodes), default=0) + 1)
    try:
        layer_order = resolve_layer_order(payload.get("layer_order"), next_layer_order(current_nodes))
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    node_type = payload["node_type"]
    metamodel_defaults = NODE_METAMODEL_DEFAULTS[node_type]
    existing_keys = {node["element_key"] for node in current_nodes}
    candidate = {
        "id": temp_id,
        "element_key": payload.get("element_key") or make_element_key(node_type.lower(), payload["display_name"], existing_keys),
        "parent_node_id": payload.get("parent_node_id"),
        "node_type": node_type,
        "semantic_type_code": payload.get("semantic_type_code", metamodel_defaults["semantic_type_code"]),
        "notation_code": payload.get("notation_code", metamodel_defaults["notation_code"]),
        "display_name": payload["display_name"],
        "target_id": payload.get("target_id"),
        "layer_order": layer_order,
        "x": payload["x"],
        "y": payload["y"],
        "width": payload["width"],
        "height": payload["height"],
        "collapsed_state": False,
    }
    if "style" in payload:
        candidate["style"] = payload["style"]

    validation_error = validate_nodes(current_nodes + [candidate])
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?, ?, ?, ?, 0, 0, ?, NULL, ?, ?)
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

    unknown = set(payload.keys()) - (NODE_MUTABLE_FIELDS | {"revision"})
    if unknown:
        return error_response("validation_error", f"unknown fields: {', '.join(sorted(unknown))}", 400)

    current_nodes = get_current_nodes(version_id)
    merged = next(node for node in current_nodes if node["id"] == node_id).copy()
    for field in NODE_MUTABLE_FIELDS:
        if field in payload:
            merged[field] = payload[field]

    validation_error = validate_nodes([merged if node["id"] == node_id else node for node in current_nodes])
    if validation_error:
        return error_response("validation_error", validation_error, 400)

    timestamp = now_iso()
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE view_version_nodes
        SET parent_node_id = ?, display_name = ?, target_id = ?, layer_order = ?, x = ?, y = ?, width = ?, height = ?,
            style_json = ?, updated_at = ?
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
    if payload["edge_type"] not in EDGE_METAMODEL_DEFAULTS:
        return error_response("validation_error", "invalid edge_type", 400)

    current_nodes = get_current_nodes(version_id)
    current_edges = get_current_edges(version_id)
    temp_id = -1 * (max((edge["id"] for edge in current_edges), default=0) + 1)
    try:
        layer_order = resolve_layer_order(payload.get("layer_order"), next_layer_order(current_edges))
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)

    edge_type = payload["edge_type"]
    metamodel_defaults = EDGE_METAMODEL_DEFAULTS[edge_type]
    existing_keys = {edge["element_key"] for edge in current_edges}
    source_element = next((node["element_key"] for node in current_nodes if node["id"] == payload["source_node_id"]), None)
    target_element = next((node["element_key"] for node in current_nodes if node["id"] == payload["target_node_id"]), None)
    candidate = {
        "id": temp_id,
        "element_key": payload.get("element_key") or make_element_key("edge", payload.get("label") or edge_type, existing_keys),
        "edge_type": edge_type,
        "association_code": payload.get("association_code"),
        "semantic_type_code": payload.get("semantic_type_code", metamodel_defaults["semantic_type_code"]),
        "notation_code": payload.get("notation_code", metamodel_defaults["notation_code"]),
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

    validation_error = validate_edges(current_edges + [candidate], {node["id"] for node in current_nodes})
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

    unknown = set(payload.keys()) - (EDGE_MUTABLE_FIELDS | {"revision"})
    if unknown:
        return error_response("validation_error", f"unknown fields: {', '.join(sorted(unknown))}", 400)

    current_nodes = get_current_nodes(version_id)
    current_edges = get_current_edges(version_id)
    merged = next(edge for edge in current_edges if edge["id"] == edge_id).copy()
    for field in EDGE_MUTABLE_FIELDS:
        if field in payload:
            merged[field] = payload[field]

    validation_error = validate_edges([merged if edge["id"] == edge_id else edge for edge in current_edges], {node["id"] for node in current_nodes})
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

    existing_node_ids = {node["id"] for node in get_current_nodes(version_id)}
    existing_edge_ids = {edge["id"] for edge in get_current_edges(version_id)}
    existing_node_keys = {node["element_key"] for node in get_current_nodes(version_id)}
    existing_edge_keys = {edge["element_key"] for edge in get_current_edges(version_id)}

    normalized_nodes: list[dict[str, Any]] = []
    used_node_ids: set[int] = set()
    used_node_keys: set[str] = set()
    next_generated_node_id = max(existing_node_ids or {0}, default=0)

    for node in nodes:
        if not isinstance(node, dict):
            return error_response("validation_error", "each node must be an object", 400)
        normalized = dict(node)
        node_type = normalized.get("node_type")
        if node_type not in NODE_METAMODEL_DEFAULTS:
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
        normalized.setdefault("semantic_type_code", NODE_METAMODEL_DEFAULTS[node_type]["semantic_type_code"])
        normalized.setdefault("notation_code", NODE_METAMODEL_DEFAULTS[node_type]["notation_code"])
        normalized_nodes.append(normalized)

    node_validation_error = validate_nodes(normalized_nodes)
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
        if edge_type not in EDGE_METAMODEL_DEFAULTS:
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
        normalized.setdefault("semantic_type_code", EDGE_METAMODEL_DEFAULTS[edge_type]["semantic_type_code"])
        normalized.setdefault("notation_code", EDGE_METAMODEL_DEFAULTS[edge_type]["notation_code"])
        normalized.setdefault("source_element_key", node_key_by_id.get(normalized.get("source_node_id")))
        normalized.setdefault("target_element_key", node_key_by_id.get(normalized.get("target_node_id")))
        normalized_edges.append(normalized)

    edge_validation_error = validate_edges(normalized_edges, {node["id"] for node in normalized_nodes})
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
