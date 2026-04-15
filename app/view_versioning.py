from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .db import get_db


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def serialize_view_version(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "view_id": row["view_id"],
        "version_no": row["version_no"],
        "version_code": row["version_code"],
        "status": row["status"],
        "based_on_version_id": row["based_on_version_id"],
        "metamodel_version_id": row["metamodel_version_id"],
        "description": row["description"],
        "published_at": row["published_at"],
        "activated_at": row["activated_at"],
        "revision": row["revision"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if "metamodel_version_code" in row.keys():
        payload["metamodel_version_code"] = row["metamodel_version_code"]
    return payload


def serialize_view_version_summary(row) -> dict[str, Any]:
    payload = serialize_view_version(row)
    payload["node_count"] = row["node_count"]
    payload["edge_count"] = row["edge_count"]
    return payload


def serialize_view_version_node(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "element_key": row["element_key"],
        "parent_node_id": row["parent_node_id"],
        "node_type": row["node_type"],
        "semantic_type_code": row["semantic_type_code"],
        "notation_code": row["notation_code"],
        "display_name": row["display_name"],
        "target_id": row["target_id"],
        "instance_mode": row["instance_mode"],
        "cardinality_scope": row["cardinality_scope"],
        "expected_min": row["expected_min"],
        "expected_max": row["expected_max"],
        "layer_order": row["layer_order"],
        "x": row["x"],
        "y": row["y"],
        "width": row["width"],
        "height": row["height"],
        "collapsed_state": bool(row["collapsed_state"]),
    }
    if row["style_json"]:
        payload["style"] = json.loads(row["style_json"])
    if row["properties_json"]:
        payload["properties"] = json.loads(row["properties_json"])
    return payload


def serialize_view_version_edge(row) -> dict[str, Any]:
    payload = {
        "id": row["id"],
        "element_key": row["element_key"],
        "edge_type": row["edge_type"],
        "association_code": row["association_code"],
        "semantic_type_code": row["semantic_type_code"],
        "notation_code": row["notation_code"],
        "source_node_id": row["source_node_id"],
        "target_node_id": row["target_node_id"],
        "source_element_key": row["source_element_key"],
        "target_element_key": row["target_element_key"],
        "layer_order": row["layer_order"],
        "source_anchor": row["source_anchor"],
        "target_anchor": row["target_anchor"],
        "control_points": json.loads(row["control_points_json"] or "[]"),
    }
    if row["label"] is not None:
        payload["label"] = row["label"]
    if row["style_json"]:
        payload["style"] = json.loads(row["style_json"])
    return payload


def get_owned_view(view_id: int, user_id: int):
    row = get_db().execute(
        """
        SELECT id, name, description, owner_user_id, metamodel_version, revision, created_at, updated_at
        FROM views
        WHERE id = ?
        """,
        (view_id,),
    ).fetchone()
    if row is None or row["owner_user_id"] != user_id:
        return None
    return row


def get_owned_view_version(version_id: int, user_id: int):
    row = get_db().execute(
        """
        SELECT vv.id, vv.view_id, vv.version_no, vv.version_code, vv.status, vv.based_on_version_id,
               vv.metamodel_version_id, vv.description, vv.published_at, vv.activated_at, vv.revision,
               vv.created_at, vv.updated_at, v.owner_user_id
        FROM view_versions AS vv
        JOIN views AS v ON v.id = vv.view_id
        WHERE vv.id = ?
        """,
        (version_id,),
    ).fetchone()
    if row is None or row["owner_user_id"] != user_id:
        return None
    return row


def list_view_versions(view_id: int) -> list[dict[str, Any]]:
    rows = get_db().execute(
        """
        SELECT vv.id, vv.view_id, vv.version_no, vv.version_code, vv.status, vv.based_on_version_id,
               vv.metamodel_version_id, vv.description, vv.published_at, vv.activated_at, vv.revision,
               vv.created_at, vv.updated_at,
               (SELECT COUNT(*) FROM view_version_nodes AS n
                WHERE n.view_version_id = vv.id AND n.is_deleted = 0) AS node_count,
               (SELECT COUNT(*) FROM view_version_edges AS e
                WHERE e.view_version_id = vv.id AND e.is_deleted = 0) AS edge_count
        FROM view_versions AS vv
        WHERE vv.view_id = ?
        ORDER BY vv.version_no DESC, vv.id DESC
        """,
        (view_id,),
    ).fetchall()
    return [serialize_view_version_summary(row) for row in rows]


def get_active_view_version(view_id: int):
    return get_db().execute(
        """
        SELECT id, view_id, version_no, version_code, status, based_on_version_id,
               metamodel_version_id, description, published_at, activated_at, revision,
               created_at, updated_at
        FROM view_versions
        WHERE view_id = ? AND status = 'active'
        ORDER BY (activated_at IS NULL) ASC, activated_at DESC, version_no DESC, id DESC
        LIMIT 1
        """,
        (view_id,),
    ).fetchone()


def get_active_view_target_rows(view_id: int):
    active_row = get_active_view_version(view_id)
    if active_row is None:
        return None
    rows = get_db().execute(
        """
        SELECT id, target_id
        FROM view_version_nodes
        WHERE view_version_id = ? AND is_deleted = 0 AND target_id IS NOT NULL
        ORDER BY layer_order ASC, id ASC
        """,
        (active_row["id"],),
    ).fetchall()
    return rows


def get_current_draft_view_version(view_id: int):
    return get_db().execute(
        """
        SELECT id, view_id, version_no, version_code, status, based_on_version_id,
               metamodel_version_id, description, published_at, activated_at, revision,
               created_at, updated_at
        FROM view_versions
        WHERE view_id = ? AND status = 'draft'
        ORDER BY version_no DESC, id DESC
        LIMIT 1
        """,
        (view_id,),
    ).fetchone()


def fetch_version_detail(version_id: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]] | None:
    version_row = get_db().execute(
        """
        SELECT id, view_id, version_no, version_code, status, based_on_version_id,
               metamodel_version_id, description, published_at, activated_at, revision,
               created_at, updated_at,
               (SELECT version_code FROM metamodel_versions WHERE id = view_versions.metamodel_version_id) AS metamodel_version_code
        FROM view_versions
        WHERE id = ?
        """,
        (version_id,),
    ).fetchone()
    if version_row is None:
        return None

    node_rows = get_db().execute(
        """
        SELECT id, element_key, parent_node_id, node_type, semantic_type_code, notation_code,
               display_name, target_id, instance_mode, cardinality_scope, expected_min, expected_max,
               layer_order, x, y, width, height, collapsed_state, style_json, properties_json
        FROM view_version_nodes
        WHERE view_version_id = ? AND is_deleted = 0
        ORDER BY layer_order ASC, id ASC
        """,
        (version_id,),
    ).fetchall()
    edge_rows = get_db().execute(
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
    return (
        serialize_view_version(version_row),
        [serialize_view_version_node(row) for row in node_rows],
        [serialize_view_version_edge(row) for row in edge_rows],
    )


def fetch_active_view_detail(view_id: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]] | None:
    active_row = get_active_view_version(view_id)
    if active_row is None:
        return None
    return fetch_version_detail(active_row["id"])


def resolve_default_metamodel_version_id(view_row) -> int | None:
    if not view_row["metamodel_version"]:
        return None
    row = get_db().execute(
        """
        SELECT id
        FROM metamodel_versions
        WHERE version_code = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (view_row["metamodel_version"],),
    ).fetchone()
    if row is None:
        return None
    return row["id"]


def create_draft_view_version(*, view_row, user_id: int, based_on_version_id: int | None, description: str | None) -> int:
    db_conn = get_db()
    draft_row = get_current_draft_view_version(view_row["id"])
    if draft_row is not None:
        raise ValueError("draft_conflict")

    source_row = None
    if based_on_version_id is not None:
        source_row = db_conn.execute(
            """
            SELECT id, view_id, status, metamodel_version_id
            FROM view_versions
            WHERE id = ?
            """,
            (based_on_version_id,),
        ).fetchone()
        if source_row is None or source_row["view_id"] != view_row["id"]:
            raise LookupError("invalid_based_on_version")
        if source_row["status"] not in {"published", "active", "deprecated"}:
            raise RuntimeError("invalid_based_on_status")
    else:
        source_row = get_active_view_version(view_row["id"])

    timestamp = now_iso()
    max_version_no = db_conn.execute(
        "SELECT COALESCE(MAX(version_no), 0) AS max_version_no FROM view_versions WHERE view_id = ?",
        (view_row["id"],),
    ).fetchone()["max_version_no"]
    version_no = max_version_no + 1
    version_code = f"v{version_no}-draft"
    metamodel_version_id = (
        source_row["metamodel_version_id"] if source_row is not None else resolve_default_metamodel_version_id(view_row)
    )

    cursor = db_conn.execute(
        """
        INSERT INTO view_versions (
            view_id, version_no, version_code, status, based_on_version_id, metamodel_version_id,
            created_by_user_id, approved_by_user_id, activated_by_user_id, description,
            published_at, activated_at, is_edit_locked, lock_owner_user_id, lock_acquired_at, lock_expires_at,
            revision, created_at, updated_at
        ) VALUES (?, ?, ?, 'draft', ?, ?, ?, NULL, NULL, ?, NULL, NULL, 0, NULL, NULL, NULL, 1, ?, ?)
        """,
        (
            view_row["id"],
            version_no,
            version_code,
            source_row["id"] if source_row is not None else None,
            metamodel_version_id,
            user_id,
            description,
            timestamp,
            timestamp,
        ),
    )
    new_version_id = cursor.lastrowid

    if source_row is None:
        db_conn.commit()
        return new_version_id

    source_nodes = db_conn.execute(
        """
        SELECT id, element_key, parent_node_id, node_type, semantic_type_code, notation_code,
               display_name, target_id, instance_mode, cardinality_scope, expected_min, expected_max,
               layer_order, x, y, width, height, collapsed_state, is_deleted, style_json, properties_json
        FROM view_version_nodes
        WHERE view_version_id = ?
        ORDER BY layer_order ASC, id ASC
        """,
        (source_row["id"],),
    ).fetchall()
    node_id_map: dict[int, int] = {}

    for row in source_nodes:
        inserted = db_conn.execute(
            """
            INSERT INTO view_version_nodes (
                view_version_id, element_key, parent_node_id, node_type, semantic_type_code, notation_code,
                display_name, target_id, instance_mode, cardinality_scope, expected_min, expected_max,
                layer_order, x, y, width, height, collapsed_state, is_deleted, style_json, properties_json,
                created_at, updated_at
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_version_id,
                row["element_key"],
                row["node_type"],
                row["semantic_type_code"],
                row["notation_code"],
                row["display_name"],
                row["target_id"],
                row["instance_mode"],
                row["cardinality_scope"],
                row["expected_min"],
                row["expected_max"],
                row["layer_order"],
                row["x"],
                row["y"],
                row["width"],
                row["height"],
                row["collapsed_state"],
                row["is_deleted"],
                row["style_json"],
                row["properties_json"],
                timestamp,
                timestamp,
            ),
        )
        node_id_map[row["id"]] = inserted.lastrowid

    for row in source_nodes:
        if row["parent_node_id"] is None:
            continue
        db_conn.execute(
            """
            UPDATE view_version_nodes
            SET parent_node_id = ?
            WHERE id = ?
            """,
            (node_id_map[row["parent_node_id"]], node_id_map[row["id"]]),
        )

    source_edges = db_conn.execute(
        """
        SELECT element_key, edge_type, association_code, semantic_type_code, notation_code,
               source_node_id, target_node_id, source_element_key, target_element_key,
               layer_order, source_anchor, target_anchor, control_points_json, label, style_json, is_deleted
        FROM view_version_edges
        WHERE view_version_id = ?
        ORDER BY layer_order ASC, id ASC
        """,
        (source_row["id"],),
    ).fetchall()

    for row in source_edges:
        db_conn.execute(
            """
            INSERT INTO view_version_edges (
                view_version_id, element_key, edge_type, association_code, semantic_type_code, notation_code,
                source_node_id, target_node_id, source_element_key, target_element_key,
                layer_order, source_anchor, target_anchor, control_points_json, label, style_json, is_deleted,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_version_id,
                row["element_key"],
                row["edge_type"],
                row["association_code"],
                row["semantic_type_code"],
                row["notation_code"],
                node_id_map[row["source_node_id"]],
                node_id_map[row["target_node_id"]],
                row["source_element_key"],
                row["target_element_key"],
                row["layer_order"],
                row["source_anchor"],
                row["target_anchor"],
                row["control_points_json"],
                row["label"],
                row["style_json"],
                row["is_deleted"],
                timestamp,
                timestamp,
            ),
        )

    db_conn.commit()
    return new_version_id
