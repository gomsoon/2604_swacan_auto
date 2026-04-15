from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from flask import Blueprint, g, request

from .auth import error_response, login_required
from .db import get_db
from .runtime_state import derive_latest_state

bp = Blueprint("views_api", __name__, url_prefix="/api/views")

ALLOWED_NODE_TYPES = {"PhysicalServer", "SoftwareProcess", "MonitoringAgent"}
ALLOWED_EDGE_TYPES = {"CommunicationLink"}
DEFAULT_EVENTS_LIMIT = 20
MAX_EVENTS_LIMIT = 100
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


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def get_view_for_user(view_id: int):
    view_row = get_db().execute(
        """
        SELECT id, name, description, owner_user_id, metamodel_version, revision, created_at, updated_at
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


def serialize_raw_event(event_row) -> dict[str, Any]:
    payload = {
        "id": event_row["id"],
        "target_id": event_row["target_id"],
        "event_type": event_row["event_type"],
        "severity": event_row["severity"],
        "message": event_row["message"],
        "occurred_at": event_row["occurred_at"],
        "received_at": event_row["received_at"],
    }
    if event_row["event_json"]:
        payload["event"] = json.loads(event_row["event_json"])
    return payload


def get_view_target_rows(view_id: int):
    return get_db().execute(
        """
        SELECT id, target_id
        FROM view_nodes
        WHERE view_id = ? AND is_deleted = 0 AND target_id IS NOT NULL
        ORDER BY layer_order ASC, id ASC
        """,
        (view_id,),
    ).fetchall()


def query_by_targets(sql_prefix: str, target_ids: list[str], extra_params: tuple[Any, ...] = ()):  # noqa: ANN401
    placeholders = ", ".join("?" for _ in target_ids)
    sql = sql_prefix.format(placeholders=placeholders)
    params = tuple(target_ids) + extra_params
    return get_db().execute(sql, params).fetchall()


def validate_nodes(nodes: list[dict[str, Any]]) -> str | None:
    if not isinstance(nodes, list):
        return "nodes must be a list"

    node_map: dict[int, dict[str, Any]] = {}
    required = {"id", "node_type", "display_name", "x", "y", "width", "height"}

    for node in nodes:
        if not isinstance(node, dict):
            return "each node must be an object"

        missing = required - node.keys()
        if missing:
            return f"node is missing required fields: {', '.join(sorted(missing))}"

        node_id = node.get("id")
        if not isinstance(node_id, int):
            return "node id must be an integer"

        if node_id in node_map:
            return "duplicate node id is not allowed"

        node_type = node.get("node_type")
        if node_type not in ALLOWED_NODE_TYPES:
            return "invalid node_type"

        metamodel_defaults = NODE_METAMODEL_DEFAULTS[node_type]
        if node.get("semantic_type_code", metamodel_defaults["semantic_type_code"]) != metamodel_defaults["semantic_type_code"]:
            return "semantic_type_code does not match node_type"
        if node.get("notation_code", metamodel_defaults["notation_code"]) != metamodel_defaults["notation_code"]:
            return "notation_code does not match node_type"

        if "layer_order" in node and not isinstance(node["layer_order"], int):
            return "layer_order must be an integer"

        node_map[node_id] = node

    for node in nodes:
        parent_id = node.get("parent_node_id")
        node_type = node["node_type"]

        if node_type == "PhysicalServer":
            if parent_id is not None:
                return "PhysicalServer must not have a parent_node_id"
            continue

        if parent_id is None:
            return f"{node_type} must have a parent_node_id"

        parent_node = node_map.get(parent_id)
        if parent_node is None:
            return "parent_node_id must reference an existing node"

        if parent_node["node_type"] != "PhysicalServer":
            return "child nodes must be contained by a PhysicalServer"

    return None


def validate_edges(edges: list[dict[str, Any]], node_ids: set[int]) -> str | None:
    if not isinstance(edges, list):
        return "edges must be a list"

    edge_ids: set[int] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            return "each edge must be an object"

        missing = {"id", "edge_type", "source_node_id", "target_node_id"} - edge.keys()
        if missing:
            return f"edge is missing required fields: {', '.join(sorted(missing))}"

        edge_id = edge.get("id")
        if not isinstance(edge_id, int):
            return "edge id must be an integer"
        if edge_id in edge_ids:
            return "duplicate edge id is not allowed"
        edge_ids.add(edge_id)

        if edge["edge_type"] not in ALLOWED_EDGE_TYPES:
            return "invalid edge_type"

        metamodel_defaults = EDGE_METAMODEL_DEFAULTS[edge["edge_type"]]
        if edge.get("semantic_type_code", metamodel_defaults["semantic_type_code"]) != metamodel_defaults["semantic_type_code"]:
            return "semantic_type_code does not match edge_type"
        if edge.get("notation_code", metamodel_defaults["notation_code"]) != metamodel_defaults["notation_code"]:
            return "notation_code does not match edge_type"

        if "layer_order" in edge and not isinstance(edge["layer_order"], int):
            return "layer_order must be an integer"

        source_id = edge["source_node_id"]
        target_id = edge["target_node_id"]
        if source_id not in node_ids or target_id not in node_ids:
            return "edge must reference existing nodes"
        if source_id == target_id:
            return "edge cannot connect a node to itself"

    return None


def replace_view_layout(view_id: int, nodes: list[dict[str, Any]], edges: list[dict[str, Any]], updated_at: str) -> None:
    db_conn = get_db()
    db_conn.execute("DELETE FROM view_edges WHERE view_id = ?", (view_id,))
    db_conn.execute("DELETE FROM view_nodes WHERE view_id = ?", (view_id,))

    sorted_nodes = sorted(
        nodes,
        key=lambda item: (
            item.get("parent_node_id") is not None,
            int(item.get("layer_order", 0)),
            item["id"],
        ),
    )
    for node in sorted_nodes:
        metamodel_defaults = NODE_METAMODEL_DEFAULTS[node["node_type"]]
        style_json = json.dumps(node.get("style")) if "style" in node else None
        db_conn.execute(
            """
            INSERT INTO view_nodes (
                id, view_id, parent_node_id, node_type, semantic_type_code, notation_code, display_name, target_id,
                layer_order, x, y, width, height, is_deleted, style_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                node["id"],
                view_id,
                node.get("parent_node_id"),
                node["node_type"],
                node.get("semantic_type_code", metamodel_defaults["semantic_type_code"]),
                node.get("notation_code", metamodel_defaults["notation_code"]),
                node["display_name"],
                node.get("target_id"),
                node.get("layer_order", 0),
                node["x"],
                node["y"],
                node["width"],
                node["height"],
                style_json,
                updated_at,
                updated_at,
            ),
        )

    for edge in edges:
        metamodel_defaults = EDGE_METAMODEL_DEFAULTS[edge["edge_type"]]
        control_points_json = json.dumps(edge.get("control_points", []))
        style_json = json.dumps(edge.get("style")) if "style" in edge else None
        db_conn.execute(
            """
            INSERT INTO view_edges (
                id, view_id, edge_type, semantic_type_code, notation_code, source_node_id, target_node_id,
                layer_order, source_anchor, target_anchor, control_points_json, label, style_json,
                is_deleted, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                edge["id"],
                view_id,
                edge["edge_type"],
                edge.get("semantic_type_code", metamodel_defaults["semantic_type_code"]),
                edge.get("notation_code", metamodel_defaults["notation_code"]),
                edge["source_node_id"],
                edge["target_node_id"],
                edge.get("layer_order", 0),
                edge.get("source_anchor"),
                edge.get("target_anchor"),
                control_points_json,
                edge.get("label"),
                style_json,
                updated_at,
                updated_at,
            ),
        )


@bp.get("")
@login_required
def list_views():
    rows = get_db().execute(
        """
        SELECT id, name, description, revision, updated_at
        FROM views
        WHERE owner_user_id = ?
        ORDER BY updated_at DESC, id DESC
        """,
        (g.user["id"],),
    ).fetchall()

    return {
        "items": [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "revision": row["revision"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
    }


@bp.get("/<int:view_id>")
@login_required
def get_view_detail(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    db_conn = get_db()
    node_rows = db_conn.execute(
        """
        SELECT id, parent_node_id, node_type, semantic_type_code, notation_code,
               display_name, target_id, layer_order, x, y, width, height, style_json
        FROM view_nodes
        WHERE view_id = ? AND is_deleted = 0
        ORDER BY layer_order ASC, id ASC
        """,
        (view_id,),
    ).fetchall()
    edge_rows = db_conn.execute(
        """
        SELECT id, edge_type, semantic_type_code, notation_code, source_node_id, target_node_id, layer_order, source_anchor, target_anchor,
               control_points_json, label, style_json
        FROM view_edges
        WHERE view_id = ? AND is_deleted = 0
        ORDER BY layer_order ASC, id ASC
        """,
        (view_id,),
    ).fetchall()

    return {
        "view": {
            "id": view_row["id"],
            "name": view_row["name"],
            "revision": view_row["revision"],
            "metamodel_version": view_row["metamodel_version"],
        },
        "nodes": [serialize_node(row) for row in node_rows],
        "edges": [serialize_edge(row) for row in edge_rows],
    }


@bp.get("/<int:view_id>/latest-state")
@login_required
def get_latest_state(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    target_rows = get_view_target_rows(view_row["id"])
    target_ids = [row["target_id"] for row in target_rows]
    if not target_ids:
        return {"items": []}

    rows = query_by_targets(
        """
        SELECT target_id, state_type, status, severity, state_json, occurred_at, received_at
        FROM latest_states
        WHERE target_id IN ({placeholders})
        """,
        target_ids,
    )

    order = {target_id: index for index, target_id in enumerate(target_ids)}
    sorted_rows = sorted(rows, key=lambda row: (order.get(row["target_id"], 10**9), row["state_type"]))

    return {"items": [derive_latest_state(row) for row in sorted_rows]}


@bp.get("/<int:view_id>/events")
@login_required
def get_view_events(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    limit_raw = request.args.get("limit", default=str(DEFAULT_EVENTS_LIMIT))
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        return error_response("validation_error", "limit must be an integer", 400)

    if limit <= 0 or limit > MAX_EVENTS_LIMIT:
        return error_response("validation_error", f"limit must be between 1 and {MAX_EVENTS_LIMIT}", 400)

    target_rows = get_view_target_rows(view_row["id"])
    target_ids = [row["target_id"] for row in target_rows]
    if not target_ids:
        return {"items": []}

    rows = query_by_targets(
        """
        SELECT id, target_id, event_type, severity, message, event_json, occurred_at, received_at
        FROM raw_events
        WHERE target_id IN ({placeholders})
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
        """,
        target_ids,
        (limit,),
    )

    return {"items": [serialize_raw_event(row) for row in rows]}


@bp.post("")
@login_required
def create_view():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    description = data.get("description")

    if not name:
        return error_response("validation_error", "name is required", 400)

    timestamp = now_iso()
    db_conn = get_db()
    cursor = db_conn.execute(
        """
        INSERT INTO views (name, description, owner_user_id, metamodel_version, revision, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        (name, description, g.user["id"], "seed-v1", timestamp, timestamp),
    )
    db_conn.commit()

    return (
        {
            "view": {
                "id": cursor.lastrowid,
                "name": name,
                "revision": 1,
            }
        },
        201,
    )


@bp.put("/<int:view_id>")
@login_required
def update_view(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    data = request.get_json(silent=True) or {}
    revision = data.get("revision")
    nodes = data.get("nodes")
    edges = data.get("edges")

    if revision is None or nodes is None or edges is None:
        return error_response("validation_error", "revision, nodes and edges are required", 400)

    if revision != view_row["revision"]:
        return error_response("revision_mismatch", "revision mismatch", 409)

    node_error = validate_nodes(nodes)
    if node_error:
        return error_response("validation_error", node_error, 400)

    node_ids = {node["id"] for node in nodes}
    edge_error = validate_edges(edges, node_ids)
    if edge_error:
        return error_response("validation_error", edge_error, 400)

    timestamp = now_iso()
    db_conn = get_db()
    replace_view_layout(view_id, nodes, edges, timestamp)
    next_revision = view_row["revision"] + 1
    db_conn.execute(
        "UPDATE views SET revision = ?, updated_at = ? WHERE id = ?",
        (next_revision, timestamp, view_id),
    )
    db_conn.commit()

    return {
        "ok": True,
        "revision": next_revision,
        "updated_at": timestamp,
    }
