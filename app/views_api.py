from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from flask import Blueprint, Response, current_app, g, request, stream_with_context

from .alert_archive import serialize_alert_archive_row
from .auth import error_response, login_required
from .db import close_db, get_db
from .runtime_state import derive_latest_state
from .view_versioning import (
    get_active_view_target_rows,
    get_active_view_version,
    get_current_draft_view_target_rows,
    get_current_draft_view_version,
)

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
        "agent_id": event_row["agent_id"],
        "monitored_object_id": event_row["monitored_object_id"],
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


def serialize_grouped_event(event_row) -> dict[str, Any]:
    payload = {
        "id": event_row["id"],
        "monitored_object_id": event_row["monitored_object_id"],
        "target_id": event_row["target_id"],
        "event_type": event_row["event_type"],
        "severity": event_row["severity"],
        "first_occurred_at": event_row["first_occurred_at"],
        "last_occurred_at": event_row["last_occurred_at"],
        "repeat_count": event_row["repeat_count"],
        "latest_message": event_row["latest_message"],
    }
    if event_row["latest_event_json"]:
        payload["event"] = json.loads(event_row["latest_event_json"])
    return payload


def serialize_alert_instance(alert_row) -> dict[str, Any]:
    payload = {
        "id": alert_row["id"],
        "monitored_object_id": alert_row["monitored_object_id"],
        "alert_code": alert_row["alert_code"],
        "source_rule_id": alert_row["source_rule_id"],
        "source_rule_metric_key": alert_row["source_rule_metric_key"],
        "source_rule_target_label": alert_row["source_rule_target_label"],
        "severity": alert_row["severity"],
        "status": alert_row["status"],
        "is_acknowledged": bool(alert_row["acknowledged_at"]),
        "acknowledged_at": alert_row["acknowledged_at"],
        "acknowledged_by_username": alert_row["acknowledged_by_username"],
        "ack_note": alert_row["ack_note"],
        "status_updated_at": alert_row["status_updated_at"],
        "status_updated_by_username": alert_row["status_updated_by_username"],
        "status_note": alert_row["status_note"],
        "resolved_at": alert_row["resolved_at"],
        "resolved_by_username": alert_row["resolved_by_username"],
        "first_occurred_at": alert_row["first_occurred_at"],
        "last_occurred_at": alert_row["last_occurred_at"],
        "repeat_count": alert_row["repeat_count"],
        "latest_message": alert_row["latest_message"],
    }
    if alert_row["metadata_json"]:
        payload["metadata"] = json.loads(alert_row["metadata_json"])
    return payload


def get_view_target_rows(view_id: int):
    return get_db().execute(
        """
        SELECT n.id, n.target_id, mo.id AS monitored_object_id
        FROM view_nodes AS n
        LEFT JOIN monitored_objects AS mo ON mo.runtime_binding_key = n.target_id
        WHERE n.view_id = ? AND n.is_deleted = 0 AND n.target_id IS NOT NULL
        ORDER BY n.layer_order ASC, n.id ASC
        """,
        (view_id,),
    ).fetchall()


def get_monitor_target_node_rows(view_id: int):
    active_row = get_active_view_version(view_id)
    if active_row is not None:
        return get_db().execute(
            """
            SELECT n.id, n.display_name, n.node_type, n.semantic_type_code, n.notation_code,
                   n.target_id, n.layer_order, b.monitored_object_id
            FROM view_version_nodes AS n
            LEFT JOIN node_bindings AS b ON b.view_version_node_id = n.id AND b.binding_role = 'primary'
            WHERE n.view_version_id = ? AND n.is_deleted = 0
              AND (n.target_id IS NOT NULL OR b.monitored_object_id IS NOT NULL)
            ORDER BY n.layer_order ASC, n.id ASC
            """,
            (active_row["id"],),
        ).fetchall()

    draft_row = get_current_draft_view_version(view_id)
    if draft_row is not None:
        return get_db().execute(
            """
            SELECT n.id, n.display_name, n.node_type, n.semantic_type_code, n.notation_code,
                   n.target_id, n.layer_order, b.monitored_object_id
            FROM view_version_nodes AS n
            LEFT JOIN node_bindings AS b ON b.view_version_node_id = n.id AND b.binding_role = 'primary'
            WHERE n.view_version_id = ? AND n.is_deleted = 0
              AND (n.target_id IS NOT NULL OR b.monitored_object_id IS NOT NULL)
            ORDER BY n.layer_order ASC, n.id ASC
            """,
            (draft_row["id"],),
        ).fetchall()

    return get_db().execute(
        """
        SELECT n.id, n.display_name, n.node_type, n.semantic_type_code, n.notation_code,
               n.target_id, n.layer_order, mo.id AS monitored_object_id
        FROM view_nodes AS n
        LEFT JOIN monitored_objects AS mo ON mo.runtime_binding_key = n.target_id
        WHERE n.view_id = ? AND n.is_deleted = 0
          AND (n.target_id IS NOT NULL OR mo.id IS NOT NULL)
        ORDER BY n.layer_order ASC, n.id ASC
        """,
        (view_id,),
    ).fetchall()


def get_monitor_target_rows(view_id: int):
    node_rows = get_monitor_target_node_rows(view_id)
    if node_rows:
        return node_rows
    active_rows = get_active_view_target_rows(view_id)
    if active_rows is not None:
        return active_rows
    draft_rows = get_current_draft_view_target_rows(view_id)
    if draft_rows is not None:
        return draft_rows
    return get_view_target_rows(view_id)


def query_by_runtime_targets(
    sql_prefix: str,
    *,
    target_ids: list[str],
    monitored_object_ids: list[int],
    extra_params: tuple[Any, ...] = (),
):  # noqa: ANN401
    clauses: list[str] = []
    params: list[Any] = []

    if monitored_object_ids:
        clauses.append(
            "monitored_object_id IN (" + ", ".join("?" for _ in monitored_object_ids) + ")"
        )
        params.extend(monitored_object_ids)
    if target_ids:
        clauses.append("target_id IN (" + ", ".join("?" for _ in target_ids) + ")")
        params.extend(target_ids)

    if not clauses:
        return []

    sql = sql_prefix.format(
        runtime_filter=" OR ".join(clauses),
    )
    params.extend(extra_params)
    return get_db().execute(sql, tuple(params)).fetchall()


def fetch_grouped_event_for_runtime(
    grouped_event_id: int,
    *,
    target_ids: list[str],
    monitored_object_ids: list[int],
):
    rows = query_by_runtime_targets(
        """
        SELECT id, monitored_object_id, target_id, event_type, severity,
               first_occurred_at, last_occurred_at, repeat_count, latest_message, latest_event_json
        FROM grouped_events
        WHERE ({runtime_filter})
          AND id = ?
        LIMIT 1
        """,
        target_ids=target_ids,
        monitored_object_ids=monitored_object_ids,
        extra_params=(grouped_event_id,),
    )
    return rows[0] if rows else None


def load_grouped_event_raw_rows(grouped_event_row, limit: int):
    clauses = [
        "event_type = ?",
        "severity = ?",
        "occurred_at >= ?",
        "occurred_at <= ?",
    ]
    params: list[Any] = [
        grouped_event_row["event_type"],
        grouped_event_row["severity"],
        grouped_event_row["first_occurred_at"],
        grouped_event_row["last_occurred_at"],
    ]

    if grouped_event_row["monitored_object_id"] is not None:
        clauses.append("monitored_object_id = ?")
        params.append(grouped_event_row["monitored_object_id"])
    else:
        clauses.append("monitored_object_id IS NULL")
        clauses.append("target_id = ?")
        params.append(grouped_event_row["target_id"])

    params.append(limit)
    return get_db().execute(
        f"""
        SELECT id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
        FROM raw_events
        WHERE {' AND '.join(clauses)}
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
        """,
        tuple(params),
    ).fetchall()


def build_runtime_order_maps(target_rows):
    object_order: dict[int, int] = {}
    target_order: dict[str, int] = {}
    for index, row in enumerate(target_rows):
        monitored_object_id = row["monitored_object_id"]
        target_id = row["target_id"]
        if monitored_object_id is not None and monitored_object_id not in object_order:
            object_order[monitored_object_id] = index
        if target_id is not None and target_id not in target_order:
            target_order[target_id] = index
    return object_order, target_order


def parse_limit_query_arg(limit_raw: str | None):
    limit_raw = limit_raw or str(DEFAULT_EVENTS_LIMIT)
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        return None, error_response("validation_error", "limit must be an integer", 400)

    if limit <= 0 or limit > MAX_EVENTS_LIMIT:
        return None, error_response("validation_error", f"limit must be between 1 and {MAX_EVENTS_LIMIT}", 400)

    return limit, None


def fetch_alert_rows_for_monitored_objects(monitored_object_ids: list[int], *, status_filter: str, limit: int):
    if not monitored_object_ids:
        return []

    placeholders = ", ".join("?" for _ in monitored_object_ids)
    status_clause = "alerts.status != 'resolved'" if status_filter == "active" else "alerts.status = ?"
    params: tuple[Any, ...]
    if status_filter == "active":
        params = tuple(monitored_object_ids) + (limit,)
    else:
        params = tuple(monitored_object_ids) + (status_filter, limit)

    return get_db().execute(
        f"""
        SELECT alerts.id, alerts.monitored_object_id, alerts.alert_code, alerts.source_rule_id,
               rules.metric_key AS source_rule_metric_key,
               COALESCE(rule_mo.display_name, rules.object_type) AS source_rule_target_label,
               alerts.severity, alerts.status, alerts.acknowledged_at,
               ack_user.username AS acknowledged_by_username, alerts.ack_note,
               alerts.status_updated_at, status_user.username AS status_updated_by_username,
               alerts.status_note,
               alerts.resolved_at, resolved_user.username AS resolved_by_username,
               alerts.first_occurred_at, alerts.last_occurred_at, alerts.repeat_count,
               alerts.latest_message, alerts.metadata_json
        FROM alert_instances AS alerts
        LEFT JOIN alert_rules AS rules ON rules.id = alerts.source_rule_id
        LEFT JOIN monitored_objects AS rule_mo ON rule_mo.id = rules.monitored_object_id
        LEFT JOIN users AS ack_user ON ack_user.id = alerts.acknowledged_by_user_id
        LEFT JOIN users AS status_user ON status_user.id = alerts.status_updated_by_user_id
        LEFT JOIN users AS resolved_user ON resolved_user.id = alerts.resolved_by_user_id
        WHERE alerts.monitored_object_id IN ({placeholders})
          AND {status_clause}
        ORDER BY
            CASE alerts.severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END,
            alerts.last_occurred_at DESC,
            alerts.id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def fetch_alert_archive_rows_for_monitored_object(monitored_object_id: int, *, limit: int):
    return get_db().execute(
        """
        SELECT archive.id, archive.monitored_object_id, mo.runtime_binding_key, mo.display_name,
               mo.object_type AS semantic_type_code,
               archive.alert_code, archive.source_rule_id, archive.source_rule_key,
               archive.source_rule_display_name_snapshot,
               rules.metric_key AS source_rule_metric_key, rules.scope_type AS source_rule_scope_type,
               COALESCE(rule_mo.display_name, rules.object_type) AS source_rule_target_label,
               archive.opened_at, archive.resolved_at,
               archive.first_severity, archive.highest_severity, archive.final_severity, archive.final_status,
               archive.repeat_count, archive.was_acknowledged,
               archive.last_acknowledged_at, archive.last_acknowledged_by_user_id,
               ack_user.username AS last_acknowledged_by_username,
               archive.resolution_source, archive.resolution_reason,
               archive.resolved_by_user_id, resolved_user.username AS resolved_by_username,
               archive.latest_message, archive.metadata_json, archive.created_at, archive.updated_at
        FROM alert_history_archive AS archive
        JOIN monitored_objects AS mo ON mo.id = archive.monitored_object_id
        LEFT JOIN alert_rules AS rules ON rules.id = archive.source_rule_id
        LEFT JOIN monitored_objects AS rule_mo ON rule_mo.id = rules.monitored_object_id
        LEFT JOIN users AS ack_user ON ack_user.id = archive.last_acknowledged_by_user_id
        LEFT JOIN users AS resolved_user ON resolved_user.id = archive.resolved_by_user_id
        WHERE archive.monitored_object_id = ?
        ORDER BY archive.resolved_at DESC, archive.id DESC
        LIMIT ?
        """,
        (monitored_object_id, limit),
    ).fetchall()


def build_runtime_object_history(monitored_object_id: int, *, limit: int) -> dict[str, Any]:
    archive_rows = fetch_alert_archive_rows_for_monitored_object(monitored_object_id, limit=limit)
    raw_event_rows = get_db().execute(
        """
        SELECT id, agent_id, monitored_object_id, target_id, event_type, severity, message, event_json, occurred_at, received_at
        FROM raw_events
        WHERE monitored_object_id = ?
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
        """,
        (monitored_object_id, limit),
    ).fetchall()
    summary_row = get_db().execute(
        """
        SELECT
            (SELECT COUNT(*) FROM alert_history_archive WHERE monitored_object_id = ?) AS resolved_alert_count,
            (SELECT MAX(resolved_at) FROM alert_history_archive WHERE monitored_object_id = ?) AS latest_resolved_at,
            (SELECT COUNT(*) FROM raw_events WHERE monitored_object_id = ?) AS raw_event_count,
            (SELECT MAX(occurred_at) FROM raw_events WHERE monitored_object_id = ?) AS latest_event_at
        """,
        (monitored_object_id, monitored_object_id, monitored_object_id, monitored_object_id),
    ).fetchone()

    return {
        "summary": {
            "resolved_alert_count": summary_row["resolved_alert_count"],
            "latest_resolved_at": summary_row["latest_resolved_at"],
            "raw_event_count": summary_row["raw_event_count"],
            "latest_event_at": summary_row["latest_event_at"],
        },
        # `alert_archive` is the canonical resolved-lifecycle summary payload.
        # Keep `alert_history` as a compatibility alias for existing clients.
        "alert_archive": [serialize_alert_archive_row(row) for row in archive_rows],
        "alert_history": [serialize_alert_archive_row(row) for row in archive_rows],
        "raw_events": [serialize_raw_event(row) for row in raw_event_rows],
    }


def serialize_monitor_target_node(row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "display_name": row["display_name"],
        "node_type": row["node_type"],
        "semantic_type_code": row["semantic_type_code"],
        "notation_code": row["notation_code"],
        "target_id": row["target_id"],
        "monitored_object_id": row["monitored_object_id"],
        "layer_order": row["layer_order"],
    }


def get_monitor_view_source(view_id: int) -> tuple[str, int]:
    active_row = get_active_view_version(view_id)
    if active_row is not None:
        return "active", active_row["id"]

    draft_row = get_current_draft_view_version(view_id)
    if draft_row is not None:
        return "draft", draft_row["id"]

    return "legacy", view_id


def fetch_runtime_object_update_markers(monitored_object_ids: list[int]) -> dict[int, dict[str, Any]]:
    markers: dict[int, dict[str, Any]] = {}
    if not monitored_object_ids:
        return markers

    placeholders = ", ".join("?" for _ in monitored_object_ids)
    params = tuple(monitored_object_ids)
    db_conn = get_db()

    for row in db_conn.execute(
        f"""
        SELECT monitored_object_id, MAX(updated_at) AS latest_state_updated_at
        FROM latest_states
        WHERE monitored_object_id IN ({placeholders})
        GROUP BY monitored_object_id
        """,
        params,
    ).fetchall():
        markers.setdefault(
            row["monitored_object_id"],
            {
                "latest_state_updated_at": None,
                "alerts_updated_at": None,
                "alert_count": 0,
                "events_updated_at": None,
                "event_count": 0,
            },
        )["latest_state_updated_at"] = row["latest_state_updated_at"]

    for row in db_conn.execute(
        f"""
        SELECT monitored_object_id, MAX(updated_at) AS alerts_updated_at, COUNT(*) AS alert_count
        FROM alert_instances
        WHERE monitored_object_id IN ({placeholders})
        GROUP BY monitored_object_id
        """,
        params,
    ).fetchall():
        marker = markers.setdefault(
            row["monitored_object_id"],
            {
                "latest_state_updated_at": None,
                "alerts_updated_at": None,
                "alert_count": 0,
                "events_updated_at": None,
                "event_count": 0,
            },
        )
        marker["alerts_updated_at"] = row["alerts_updated_at"]
        marker["alert_count"] = row["alert_count"]

    for row in db_conn.execute(
        f"""
        SELECT monitored_object_id, MAX(updated_at) AS events_updated_at, COUNT(*) AS event_count
        FROM grouped_events
        WHERE monitored_object_id IN ({placeholders})
        GROUP BY monitored_object_id
        """,
        params,
    ).fetchall():
        marker = markers.setdefault(
            row["monitored_object_id"],
            {
                "latest_state_updated_at": None,
                "alerts_updated_at": None,
                "alert_count": 0,
                "events_updated_at": None,
                "event_count": 0,
            },
        )
        marker["events_updated_at"] = row["events_updated_at"]
        marker["event_count"] = row["event_count"]

    return markers


def build_view_runtime_watch_state(view_id: int) -> dict[str, Any]:
    source_mode, source_id = get_monitor_view_source(view_id)
    target_rows = get_monitor_target_node_rows(view_id)
    monitored_object_ids = sorted(
        {
            row["monitored_object_id"]
            for row in target_rows
            if row["monitored_object_id"] is not None
        }
    )
    markers = fetch_runtime_object_update_markers(monitored_object_ids)
    view_signature = (
        source_mode,
        source_id,
        tuple(
            (row["id"], row["target_id"], row["monitored_object_id"])
            for row in target_rows
        ),
    )

    return {
        "source_mode": source_mode,
        "source_id": source_id,
        "view_signature": view_signature,
        "monitored_object_ids": monitored_object_ids,
        "markers": markers,
    }


def detect_view_runtime_changes(
    previous_state: dict[str, Any] | None,
    current_state: dict[str, Any],
) -> dict[str, Any] | None:
    if previous_state is None:
        return None

    if previous_state["view_signature"] != current_state["view_signature"]:
        return {
            "full_refresh": True,
            "reason": "view_structure_changed",
            "monitored_object_ids": current_state["monitored_object_ids"],
        }

    changed_object_ids: list[int] = []
    object_ids = set(previous_state["markers"].keys()) | set(current_state["markers"].keys())
    for monitored_object_id in sorted(object_ids):
        if previous_state["markers"].get(monitored_object_id) != current_state["markers"].get(monitored_object_id):
            changed_object_ids.append(monitored_object_id)

    if not changed_object_ids:
        return None

    return {
        "full_refresh": False,
        "reason": "runtime_objects_changed",
        "monitored_object_ids": changed_object_ids,
    }


def sse_event(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


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

    target_rows = get_monitor_target_rows(view_row["id"])
    target_ids = [row["target_id"] for row in target_rows if row["target_id"] is not None]
    monitored_object_ids = [row["monitored_object_id"] for row in target_rows if row["monitored_object_id"] is not None]
    if not target_ids and not monitored_object_ids:
        return {"items": []}

    rows = query_by_runtime_targets(
        """
        SELECT monitored_object_id, target_id, state_type, status, severity, state_json, occurred_at, received_at
        FROM latest_states
        WHERE {runtime_filter}
        """,
        target_ids=target_ids,
        monitored_object_ids=monitored_object_ids,
    )

    object_order, target_order = build_runtime_order_maps(target_rows)
    sorted_rows = sorted(
        rows,
        key=lambda row: (
            object_order.get(row["monitored_object_id"], target_order.get(row["target_id"], 10**9)),
            row["state_type"],
        ),
    )

    return {"items": [derive_latest_state(row) for row in sorted_rows]}


@bp.get("/<int:view_id>/events")
@login_required
def get_view_events(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    limit, limit_error = parse_limit_query_arg(request.args.get("limit"))
    if limit_error:
        return limit_error

    target_rows = get_monitor_target_rows(view_row["id"])
    target_ids = [row["target_id"] for row in target_rows if row["target_id"] is not None]
    monitored_object_ids = [row["monitored_object_id"] for row in target_rows if row["monitored_object_id"] is not None]
    if not target_ids and not monitored_object_ids:
        return {"items": []}

    rows = query_by_runtime_targets(
        """
        SELECT id, monitored_object_id, target_id, event_type, severity,
               first_occurred_at, last_occurred_at, repeat_count, latest_message, latest_event_json
        FROM grouped_events
        WHERE {runtime_filter}
        ORDER BY last_occurred_at DESC, id DESC
        LIMIT ?
        """,
        target_ids=target_ids,
        monitored_object_ids=monitored_object_ids,
        extra_params=(limit,),
    )

    return {"items": [serialize_grouped_event(row) for row in rows]}


@bp.get("/<int:view_id>/events/<int:grouped_event_id>/raw-events")
@login_required
def get_view_grouped_event_raw_events(view_id: int, grouped_event_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    limit, limit_error = parse_limit_query_arg(request.args.get("limit"))
    if limit_error:
        return limit_error

    target_rows = get_monitor_target_rows(view_row["id"])
    target_ids = [row["target_id"] for row in target_rows if row["target_id"] is not None]
    monitored_object_ids = [row["monitored_object_id"] for row in target_rows if row["monitored_object_id"] is not None]
    if not target_ids and not monitored_object_ids:
        return error_response("not_found", "grouped event not found", 404)

    grouped_event_row = fetch_grouped_event_for_runtime(
        grouped_event_id,
        target_ids=target_ids,
        monitored_object_ids=monitored_object_ids,
    )
    if grouped_event_row is None:
        return error_response("not_found", "grouped event not found", 404)

    raw_rows = load_grouped_event_raw_rows(grouped_event_row, limit)
    return {
        "grouped_event": serialize_grouped_event(grouped_event_row),
        "items": [serialize_raw_event(row) for row in raw_rows],
    }


@bp.get("/<int:view_id>/alerts")
@login_required
def get_view_alerts(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    limit, limit_error = parse_limit_query_arg(request.args.get("limit"))
    if limit_error:
        return limit_error

    status_filter = (request.args.get("status") or "active").strip().lower()
    if status_filter not in {"active", "open", "in_progress", "suppressed", "resolved"}:
        return error_response(
            "validation_error",
            "status must be active, open, in_progress, suppressed or resolved",
            400,
        )

    target_rows = get_monitor_target_rows(view_row["id"])
    monitored_object_ids = [row["monitored_object_id"] for row in target_rows if row["monitored_object_id"] is not None]
    if not monitored_object_ids:
        return {"items": []}

    rows = fetch_alert_rows_for_monitored_objects(
        monitored_object_ids,
        status_filter=status_filter,
        limit=limit,
    )

    return {"items": [serialize_alert_instance(row) for row in rows]}


@bp.get("/<int:view_id>/stream")
@login_required
def stream_view_runtime(view_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    poll_seconds = float(current_app.config.get("MONITORING_SSE_POLL_SECONDS", 1.0))
    keepalive_seconds = float(current_app.config.get("MONITORING_SSE_KEEPALIVE_SECONDS", 15.0))

    @stream_with_context
    def generate():
        try:
            previous_state = build_view_runtime_watch_state(view_row["id"])
            close_db()
            yield sse_event(
                "connected",
                {
                    "view_id": view_row["id"],
                    "source_mode": previous_state["source_mode"],
                    "source_id": previous_state["source_id"],
                },
            )
            last_keepalive = time.monotonic()

            while True:
                time.sleep(poll_seconds)
                current_state = build_view_runtime_watch_state(view_row["id"])
                close_db()
                change_payload = detect_view_runtime_changes(previous_state, current_state)
                previous_state = current_state

                if change_payload is not None:
                    yield sse_event(
                        "runtime_change",
                        {
                            "view_id": view_row["id"],
                            "source_mode": current_state["source_mode"],
                            "source_id": current_state["source_id"],
                            **change_payload,
                        },
                    )
                    last_keepalive = time.monotonic()
                    continue

                if time.monotonic() - last_keepalive >= keepalive_seconds:
                    yield ": keepalive\n\n"
                    last_keepalive = time.monotonic()
        finally:
            close_db()

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@bp.get("/<int:view_id>/runtime-objects/<int:monitored_object_id>/slice")
@login_required
def get_view_runtime_object_slice(view_id: int, monitored_object_id: int):
    view_row, error = get_view_for_user(view_id)
    if error:
        return error

    limit, limit_error = parse_limit_query_arg(request.args.get("limit"))
    if limit_error:
        return limit_error

    target_rows = get_monitor_target_node_rows(view_row["id"])
    fanout_rows = [row for row in target_rows if row["monitored_object_id"] == monitored_object_id]
    if not fanout_rows:
        return error_response("not_found", "runtime object not found in current view", 404)

    latest_rows = query_by_runtime_targets(
        """
        SELECT monitored_object_id, target_id, state_type, status, severity, state_json, occurred_at, received_at
        FROM latest_states
        WHERE {runtime_filter}
        """,
        target_ids=[],
        monitored_object_ids=[monitored_object_id],
    )
    latest_items = [derive_latest_state(row) for row in sorted(latest_rows, key=lambda row: row["state_type"])]

    alert_rows = fetch_alert_rows_for_monitored_objects(
        [monitored_object_id],
        status_filter="active",
        limit=limit,
    )
    event_rows = query_by_runtime_targets(
        """
        SELECT id, monitored_object_id, target_id, event_type, severity,
               first_occurred_at, last_occurred_at, repeat_count, latest_message, latest_event_json
        FROM grouped_events
        WHERE {runtime_filter}
        ORDER BY last_occurred_at DESC, id DESC
        LIMIT ?
        """,
        target_ids=[],
        monitored_object_ids=[monitored_object_id],
        extra_params=(limit,),
    )

    return {
        "monitored_object_id": monitored_object_id,
        "fanout_nodes": [serialize_monitor_target_node(row) for row in fanout_rows],
        "latest_states": latest_items,
        "alerts": [serialize_alert_instance(row) for row in alert_rows],
        "events": [serialize_grouped_event(row) for row in event_rows],
        "history": build_runtime_object_history(monitored_object_id, limit=min(limit, 5)),
    }


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
