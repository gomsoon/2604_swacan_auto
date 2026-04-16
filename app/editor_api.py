from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import Blueprint, g, request

from .auth import error_response, login_required
from .db import get_db

bp = Blueprint("editor_api", __name__, url_prefix="/api/views")

ALLOWED_NODE_TYPES = {"PhysicalServer", "SoftwareProcess", "MonitoringAgent"}
ALLOWED_EDGE_TYPES = {"CommunicationLink"}
NODE_METAMODEL_DEFAULTS = {
    "PhysicalServer": {"semantic_type_code": "PhysicalServer", "notation_code": "server.physical.rect"},
    "SoftwareProcess": {"semantic_type_code": "SoftwareProcess", "notation_code": "process.rounded_rect"},
    "MonitoringAgent": {
        "semantic_type_code": "MonitoringAgent",
        "notation_code": "agent.rounded_rect.double_border",
    },
}
EDGE_METAMODEL_DEFAULTS = {
    "CommunicationLink": {"semantic_type_code": "CommunicationLink", "notation_code": "communication.line"},
}
NODE_MUTABLE_FIELDS = {
    "parent_node_id",
    "display_name",
    "target_id",
    "properties",
    "layer_order",
    "x",
    "y",
    "width",
    "height",
    "style",
}
EDGE_MUTABLE_FIELDS = {
    "source_node_id",
    "target_node_id",
    "layer_order",
    "source_anchor",
    "target_anchor",
    "control_points",
    "label",
    "style",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def get_view_for_user(view_id: int):
    view_row = get_db().execute(
        """
        SELECT id, owner_user_id, revision
        FROM views
        WHERE id = ?
        """,
        (view_id,),
    ).fetchone()

    if view_row is None:
        return None, error_response("not_found", "view not found", 404)

    if view_row["owner_user_id"] != g.user["id"]:
        return None, error_response("forbidden", "permission denied", 403)

    return view_row, None


def serialize_node(node_row) -> dict[str, Any]:
    payload = {
        "id": node_row["id"],
        "parent_node_id": node_row["parent_node_id"],
        "node_type": node_row["node_type"],
        "semantic_type_code": node_row["semantic_type_code"],
        "notation_code": node_row["notation_code"],
        "display_name": node_row["display_name"],
        "target_id": node_row["target_id"],
        "layer_order": node_row["layer_order"],
        "x": node_row["x"],
        "y": node_row["y"],
        "width": node_row["width"],
        "height": node_row["height"],
    }
    if node_row["style_json"]:
        payload["style"] = json.loads(node_row["style_json"])
    return payload


def serialize_edge(edge_row) -> dict[str, Any]:
    payload = {
        "id": edge_row["id"],
        "edge_type": edge_row["edge_type"],
        "semantic_type_code": edge_row["semantic_type_code"],
        "notation_code": edge_row["notation_code"],
        "source_node_id": edge_row["source_node_id"],
        "target_node_id": edge_row["target_node_id"],
        "layer_order": edge_row["layer_order"],
        "source_anchor": edge_row["source_anchor"],
        "target_anchor": edge_row["target_anchor"],
        "control_points": json.loads(edge_row["control_points_json"] or "[]"),
    }
    if edge_row["label"] is not None:
        payload["label"] = edge_row["label"]
    if edge_row["style_json"]:
        payload["style"] = json.loads(edge_row["style_json"])
    return payload


def get_current_nodes(view_id: int) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT id, parent_node_id, node_type, semantic_type_code, notation_code,
               display_name, target_id, layer_order, x, y, width, height, style_json
        FROM view_nodes
        WHERE view_id = ? AND is_deleted = 0
        ORDER BY layer_order ASC, id ASC
        """,
        (view_id,),
    ).fetchall()
    return [serialize_node(row) for row in rows]


def get_current_edges(view_id: int) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT id, edge_type, semantic_type_code, notation_code, source_node_id, target_node_id, layer_order, source_anchor, target_anchor,
               control_points_json, label, style_json
        FROM view_edges
        WHERE view_id = ? AND is_deleted = 0
        ORDER BY layer_order ASC, id ASC
        """,
        (view_id,),
    ).fetchall()
    return [serialize_edge(row) for row in rows]


def get_node_row(view_id: int, node_id: int):
    return get_db().execute(
        """
        SELECT id, parent_node_id, node_type, semantic_type_code, notation_code,
               display_name, target_id, layer_order, x, y, width, height, style_json
        FROM view_nodes
        WHERE view_id = ? AND id = ? AND is_deleted = 0
        """,
        (view_id, node_id),
    ).fetchone()


def get_edge_row(view_id: int, edge_id: int):
    return get_db().execute(
        """
        SELECT id, edge_type, semantic_type_code, notation_code, source_node_id, target_node_id, layer_order, source_anchor, target_anchor,
               control_points_json, label, style_json
        FROM view_edges
        WHERE view_id = ? AND id = ? AND is_deleted = 0
        """,
        (view_id, edge_id),
    ).fetchone()


def require_revision(view_row, payload: dict[str, Any]):
    revision = payload.get("revision")
    if revision is None:
        return error_response("validation_error", "revision is required", 400)
    if revision != view_row["revision"]:
        return error_response("revision_mismatch", "revision mismatch", 409)
    return None


def next_layer_order(items: list[dict[str, Any]], step: int = 10) -> int:
    current_max = max((int(item.get("layer_order", 0)) for item in items), default=0)
    return current_max + step


def resolve_layer_order(raw_value: Any, default_value: int) -> int:
    if raw_value is None:
        return default_value
    if not isinstance(raw_value, int):
        raise ValueError("layer_order must be an integer")
    return raw_value


def bump_view_revision(view_id: int) -> tuple[int, str]:
    timestamp = now_iso()
    db_conn = get_db()
    current_revision = db_conn.execute(
        "SELECT revision FROM views WHERE id = ?",
        (view_id,),
    ).fetchone()["revision"]
    next_revision = current_revision + 1
    db_conn.execute(
        "UPDATE views SET revision = ?, updated_at = ? WHERE id = ?",
        (next_revision, timestamp, view_id),
    )
    return next_revision, timestamp


def validate_nodes(nodes: list[dict[str, Any]]) -> str | None:
    node_map: dict[int, dict[str, Any]] = {}
    required = {"id", "node_type", "display_name", "x", "y", "width", "height"}

    for node in nodes:
        missing = required - node.keys()
        if missing:
            return f"node is missing required fields: {', '.join(sorted(missing))}"

        if node["node_type"] not in ALLOWED_NODE_TYPES:
            return "invalid node_type"

        metamodel_defaults = NODE_METAMODEL_DEFAULTS[node["node_type"]]
        if node.get("semantic_type_code", metamodel_defaults["semantic_type_code"]) != metamodel_defaults["semantic_type_code"]:
            return "semantic_type_code does not match node_type"
        if node.get("notation_code", metamodel_defaults["notation_code"]) != metamodel_defaults["notation_code"]:
            return "notation_code does not match node_type"

        if not isinstance(node["id"], int):
            return "node id must be an integer"

        if node["id"] in node_map:
            return "duplicate node id is not allowed"

        if "layer_order" in node and not isinstance(node["layer_order"], int):
            return "layer_order must be an integer"

        node_map[node["id"]] = node

    for node in nodes:
        parent_id = node.get("parent_node_id")
        if node["node_type"] == "PhysicalServer":
            if parent_id is not None:
                return "PhysicalServer must not have a parent_node_id"
            continue

        if parent_id is None:
            return f"{node['node_type']} must have a parent_node_id"

        parent_node = node_map.get(parent_id)
        if parent_node is None:
            return "parent_node_id must reference an existing node"

        if parent_node["node_type"] != "PhysicalServer":
            return "child nodes must be contained by a PhysicalServer"

    return None


def validate_edges(edges: list[dict[str, Any]], node_ids: set[int]) -> str | None:
    seen_ids: set[int] = set()
    for edge in edges:
        missing = {"id", "edge_type", "source_node_id", "target_node_id"} - edge.keys()
        if missing:
            return f"edge is missing required fields: {', '.join(sorted(missing))}"

        if edge["edge_type"] not in ALLOWED_EDGE_TYPES:
            return "invalid edge_type"

        metamodel_defaults = EDGE_METAMODEL_DEFAULTS[edge["edge_type"]]
        if edge.get("semantic_type_code", metamodel_defaults["semantic_type_code"]) != metamodel_defaults["semantic_type_code"]:
            return "semantic_type_code does not match edge_type"
        if edge.get("notation_code", metamodel_defaults["notation_code"]) != metamodel_defaults["notation_code"]:
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

        if edge["source_node_id"] == edge["target_node_id"]:
            return "edge cannot connect a node to itself"

    return None


@bp.post("/<int:view_id>/nodes")
@login_required
def create_node(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(view_row, payload)
    if revision_error:
        return revision_error

    missing = {"node_type", "display_name", "x", "y", "width", "height"} - payload.keys()
    if missing:
        return error_response("validation_error", f"node is missing required fields: {', '.join(sorted(missing))}", 400)
    if payload["node_type"] not in NODE_METAMODEL_DEFAULTS:
        return error_response("validation_error", "invalid node_type", 400)

    current_nodes = get_current_nodes(view_id)
    temp_id = -1 * (max((node["id"] for node in current_nodes), default=0) + 1)
    try:
        layer_order = resolve_layer_order(payload.get("layer_order"), next_layer_order(current_nodes))
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)
    candidate = {
        "id": temp_id,
        "parent_node_id": payload.get("parent_node_id"),
        "node_type": payload["node_type"],
        "semantic_type_code": payload.get("semantic_type_code", NODE_METAMODEL_DEFAULTS[payload["node_type"]]["semantic_type_code"]),
        "notation_code": payload.get("notation_code", NODE_METAMODEL_DEFAULTS[payload["node_type"]]["notation_code"]),
        "display_name": payload["display_name"],
        "target_id": payload.get("target_id"),
        "layer_order": layer_order,
        "x": payload["x"],
        "y": payload["y"],
        "width": payload["width"],
        "height": payload["height"],
    }
    if "style" in payload:
        candidate["style"] = payload["style"]

    validation_error = validate_nodes(current_nodes + [candidate])
    if validation_error:
        return error_response("validation_error", validation_error, 400)

    timestamp = now_iso()
    style_json = json.dumps(payload.get("style")) if "style" in payload else None
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO view_nodes (
            view_id, parent_node_id, node_type, semantic_type_code, notation_code, display_name, target_id,
            layer_order, x, y, width, height, is_deleted, style_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        """,
        (
            view_id,
            payload.get("parent_node_id"),
            payload["node_type"],
            candidate["semantic_type_code"],
            candidate["notation_code"],
            payload["display_name"],
            payload.get("target_id"),
            candidate["layer_order"],
            payload["x"],
            payload["y"],
            payload["width"],
            payload["height"],
            style_json,
            timestamp,
            timestamp,
        ),
    )
    next_revision, updated_at = bump_view_revision(view_id)
    db_conn.commit()

    return {
        "node": serialize_node(get_node_row(view_id, cursor.lastrowid)),
        "revision": next_revision,
        "updated_at": updated_at,
    }, 201


@bp.patch("/<int:view_id>/nodes/<int:node_id>")
@login_required
def update_node(view_id: int, node_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(view_row, payload)
    if revision_error:
        return revision_error

    node_row = get_node_row(view_id, node_id)
    if node_row is None:
        return error_response("not_found", "node not found", 404)

    unknown = set(payload.keys()) - (NODE_MUTABLE_FIELDS | {"revision"})
    if unknown:
        return error_response("validation_error", f"unknown fields: {', '.join(sorted(unknown))}", 400)

    current_nodes = get_current_nodes(view_id)
    merged = next(node for node in current_nodes if node["id"] == node_id).copy()
    for field in NODE_MUTABLE_FIELDS:
        if field in payload:
            merged[field] = payload[field]

    validation_error = validate_nodes([merged if node["id"] == node_id else node for node in current_nodes])
    if validation_error:
        return error_response("validation_error", validation_error, 400)

    timestamp = now_iso()
    style_json = json.dumps(merged.get("style")) if "style" in merged else None
    db_conn = get_db()
    db_conn.execute(
        """
        UPDATE view_nodes
        SET parent_node_id = ?, display_name = ?, target_id = ?, layer_order = ?, x = ?, y = ?, width = ?, height = ?, style_json = ?, updated_at = ?
        WHERE id = ? AND view_id = ?
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
            style_json,
            timestamp,
            node_id,
            view_id,
        ),
    )
    next_revision, updated_at = bump_view_revision(view_id)
    db_conn.commit()

    return {
        "node": serialize_node(get_node_row(view_id, node_id)),
        "revision": next_revision,
        "updated_at": updated_at,
    }


@bp.delete("/<int:view_id>/nodes/<int:node_id>")
@login_required
def delete_node(view_id: int, node_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(view_row, payload)
    if revision_error:
        return revision_error

    if get_node_row(view_id, node_id) is None:
        return error_response("not_found", "node not found", 404)

    db_conn = get_db()
    db_conn.execute("DELETE FROM view_nodes WHERE id = ? AND view_id = ?", (node_id, view_id))
    next_revision, updated_at = bump_view_revision(view_id)
    db_conn.commit()

    return {
        "ok": True,
        "deleted_node_id": node_id,
        "revision": next_revision,
        "updated_at": updated_at,
    }


@bp.post("/<int:view_id>/edges")
@login_required
def create_edge(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(view_row, payload)
    if revision_error:
        return revision_error

    missing = {"edge_type", "source_node_id", "target_node_id"} - payload.keys()
    if missing:
        return error_response("validation_error", f"edge is missing required fields: {', '.join(sorted(missing))}", 400)
    if payload["edge_type"] not in EDGE_METAMODEL_DEFAULTS:
        return error_response("validation_error", "invalid edge_type", 400)

    current_nodes = get_current_nodes(view_id)
    current_edges = get_current_edges(view_id)
    temp_id = -1 * (max((edge["id"] for edge in current_edges), default=0) + 1)
    try:
        layer_order = resolve_layer_order(payload.get("layer_order"), next_layer_order(current_edges))
    except ValueError as exc:
        return error_response("validation_error", str(exc), 400)
    candidate = {
        "id": temp_id,
        "edge_type": payload["edge_type"],
        "semantic_type_code": payload.get("semantic_type_code", EDGE_METAMODEL_DEFAULTS[payload["edge_type"]]["semantic_type_code"]),
        "notation_code": payload.get("notation_code", EDGE_METAMODEL_DEFAULTS[payload["edge_type"]]["notation_code"]),
        "source_node_id": payload["source_node_id"],
        "target_node_id": payload["target_node_id"],
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
        INSERT INTO view_edges (
            view_id, edge_type, semantic_type_code, notation_code, source_node_id, target_node_id,
            layer_order, source_anchor, target_anchor, control_points_json, label, style_json,
            is_deleted, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            view_id,
            payload["edge_type"],
            candidate["semantic_type_code"],
            candidate["notation_code"],
            payload["source_node_id"],
            payload["target_node_id"],
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
    next_revision, updated_at = bump_view_revision(view_id)
    db_conn.commit()

    return {
        "edge": serialize_edge(get_edge_row(view_id, cursor.lastrowid)),
        "revision": next_revision,
        "updated_at": updated_at,
    }, 201


@bp.patch("/<int:view_id>/edges/<int:edge_id>")
@login_required
def update_edge(view_id: int, edge_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(view_row, payload)
    if revision_error:
        return revision_error

    edge_row = get_edge_row(view_id, edge_id)
    if edge_row is None:
        return error_response("not_found", "edge not found", 404)

    unknown = set(payload.keys()) - (EDGE_MUTABLE_FIELDS | {"revision"})
    if unknown:
        return error_response("validation_error", f"unknown fields: {', '.join(sorted(unknown))}", 400)

    current_nodes = get_current_nodes(view_id)
    current_edges = get_current_edges(view_id)
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
        UPDATE view_edges
        SET source_node_id = ?, target_node_id = ?, layer_order = ?, source_anchor = ?, target_anchor = ?,
            control_points_json = ?, label = ?, style_json = ?, updated_at = ?
        WHERE id = ? AND view_id = ?
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
            view_id,
        ),
    )
    next_revision, updated_at = bump_view_revision(view_id)
    db_conn.commit()

    return {
        "edge": serialize_edge(get_edge_row(view_id, edge_id)),
        "revision": next_revision,
        "updated_at": updated_at,
    }


@bp.delete("/<int:view_id>/edges/<int:edge_id>")
@login_required
def delete_edge(view_id: int, edge_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    revision_error = require_revision(view_row, payload)
    if revision_error:
        return revision_error

    if get_edge_row(view_id, edge_id) is None:
        return error_response("not_found", "edge not found", 404)

    db_conn = get_db()
    db_conn.execute("DELETE FROM view_edges WHERE id = ? AND view_id = ?", (edge_id, view_id))
    next_revision, updated_at = bump_view_revision(view_id)
    db_conn.commit()

    return {
        "ok": True,
        "deleted_edge_id": edge_id,
        "revision": next_revision,
        "updated_at": updated_at,
    }
