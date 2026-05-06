from __future__ import annotations

import app.views_api as views_api
from app.views_api import (
    detect_view_runtime_changes,
    query_by_runtime_targets,
    serialize_alert_instance,
    serialize_edge,
    serialize_grouped_event,
    serialize_node,
    serialize_raw_event,
    sse_event,
    validate_edges,
    validate_nodes,
)


def test_query_by_runtime_targets_returns_empty_without_runtime_filters() -> None:
    assert query_by_runtime_targets("SELECT 1 WHERE {runtime_filter}", target_ids=[], monitored_object_ids=[]) == []


def test_detect_view_runtime_changes_returns_none_for_initial_or_unchanged_state() -> None:
    current_state = {
        "view_signature": ("active", 1001, ((1101, "app_main", 1302),)),
        "monitored_object_ids": [1302],
        "markers": {1302: {"latest_state_updated_at": "2026-05-06T09:00:00.000+09:00"}},
    }

    assert detect_view_runtime_changes(None, current_state) is None
    assert detect_view_runtime_changes(current_state, current_state) is None


def test_get_monitor_target_rows_uses_active_draft_and_legacy_fallbacks(monkeypatch) -> None:
    monkeypatch.setattr(views_api, "get_monitor_target_node_rows", lambda _view_id: [])
    monkeypatch.setattr(views_api, "get_active_view_target_rows", lambda _view_id: [{"source": "active"}])
    monkeypatch.setattr(views_api, "get_current_draft_view_target_rows", lambda _view_id: [{"source": "draft"}])
    monkeypatch.setattr(views_api, "get_view_target_rows", lambda _view_id: [{"source": "legacy"}])

    assert views_api.get_monitor_target_rows(1) == [{"source": "active"}]

    monkeypatch.setattr(views_api, "get_active_view_target_rows", lambda _view_id: None)
    assert views_api.get_monitor_target_rows(1) == [{"source": "draft"}]

    monkeypatch.setattr(views_api, "get_current_draft_view_target_rows", lambda _view_id: None)
    assert views_api.get_monitor_target_rows(1) == [{"source": "legacy"}]


def test_views_serializers_include_optional_payloads() -> None:
    node = serialize_node(
        {
            "id": 1,
            "parent_node_id": None,
            "node_type": "PhysicalServer",
            "semantic_type_code": "PhysicalServer",
            "notation_code": "server.physical.rect",
            "display_name": "Host",
            "target_id": None,
            "layer_order": 10,
            "x": 10,
            "y": 10,
            "width": 100,
            "height": 80,
            "style_json": '{"fill":"blue"}',
        }
    )
    edge = serialize_edge(
        {
            "id": 2,
            "edge_type": "CommunicationLink",
            "semantic_type_code": "CommunicationLink",
            "notation_code": "communication.line",
            "source_node_id": 1,
            "target_node_id": 2,
            "layer_order": 20,
            "source_anchor": "right",
            "target_anchor": "left",
            "control_points_json": '[{"x":1,"y":2}]',
            "label": "link",
            "style_json": '{"stroke":"red"}',
        }
    )
    raw_event = serialize_raw_event(
        {
            "id": 3,
            "agent_id": "agent_local",
            "monitored_object_id": 1302,
            "target_id": "app_main",
            "event_type": "process_stopped",
            "severity": "warning",
            "message": "stopped",
            "occurred_at": "2026-05-06T09:00:00.000+09:00",
            "received_at": "2026-05-06T09:00:01.000+09:00",
            "event_json": '{"pid":1234}',
        }
    )
    grouped_event = serialize_grouped_event(
        {
            "id": 4,
            "monitored_object_id": 1302,
            "target_id": "app_main",
            "event_type": "process_stopped",
            "severity": "warning",
            "first_occurred_at": "2026-05-06T09:00:00.000+09:00",
            "last_occurred_at": "2026-05-06T09:00:01.000+09:00",
            "repeat_count": 2,
            "latest_message": "stopped",
            "latest_event_json": '{"pid":1234}',
        }
    )
    alert = serialize_alert_instance(
        {
            "id": 5,
            "monitored_object_id": 1302,
            "alert_code": "rule.1501",
            "source_rule_id": 1501,
            "source_rule_metric_key": "cpu_usage",
            "source_rule_target_label": "SoftwareProcess",
            "severity": "warning",
            "status": "open",
            "acknowledged_at": "2026-05-06T09:00:02.000+09:00",
            "acknowledged_by_username": "admin",
            "ack_note": "checked",
            "status_updated_at": "2026-05-06T09:00:03.000+09:00",
            "status_updated_by_username": "admin",
            "status_note": "triage",
            "resolved_at": None,
            "resolved_by_username": None,
            "first_occurred_at": "2026-05-06T09:00:00.000+09:00",
            "last_occurred_at": "2026-05-06T09:00:03.000+09:00",
            "repeat_count": 2,
            "latest_message": "cpu high",
            "metadata_json": '{"threshold":"warning"}',
        }
    )

    assert node["style"] == {"fill": "blue"}
    assert edge["label"] == "link"
    assert edge["style"] == {"stroke": "red"}
    assert raw_event["event"] == {"pid": 1234}
    assert grouped_event["event"] == {"pid": 1234}
    assert alert["metadata"] == {"threshold": "warning"}


def test_validate_nodes_covers_error_matrix() -> None:
    physical_server = {
        "id": 101,
        "node_type": "PhysicalServer",
        "display_name": "Host",
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 80,
    }
    process = {
        "id": 102,
        "node_type": "SoftwareProcess",
        "display_name": "Process",
        "parent_node_id": 101,
        "x": 10,
        "y": 10,
        "width": 80,
        "height": 40,
    }

    assert validate_nodes("bad") == "nodes must be a list"
    assert validate_nodes([1]) == "each node must be an object"
    assert validate_nodes([{"id": 1}]) == "node is missing required fields: display_name, height, node_type, width, x, y"
    assert validate_nodes([{**physical_server, "id": "bad"}]) == "node id must be an integer"
    assert validate_nodes([physical_server, dict(physical_server)]) == "duplicate node id is not allowed"
    assert validate_nodes([{**physical_server, "node_type": "BadNode"}]) == "invalid node_type"
    assert validate_nodes([{**physical_server, "semantic_type_code": "Bad"}]) == "semantic_type_code does not match node_type"
    assert validate_nodes([{**physical_server, "notation_code": "bad"}]) == "notation_code does not match node_type"
    assert validate_nodes([{**physical_server, "layer_order": "front"}]) == "layer_order must be an integer"
    assert validate_nodes([{**physical_server, "parent_node_id": 999}]) == "PhysicalServer must not have a parent_node_id"
    assert validate_nodes([{**process, "parent_node_id": None}]) == "SoftwareProcess must have a parent_node_id"
    assert validate_nodes([process]) == "parent_node_id must reference an existing node"
    assert validate_nodes(
        [
            {**physical_server, "node_type": "MonitoringAgent", "parent_node_id": 101},
            process,
        ]
    ) == "child nodes must be contained by a PhysicalServer"
    assert validate_nodes([physical_server, process]) is None


def test_validate_edges_covers_error_matrix() -> None:
    valid_edge = {
        "id": 201,
        "edge_type": "CommunicationLink",
        "source_node_id": 101,
        "target_node_id": 102,
    }

    assert validate_edges("bad", {101, 102}) == "edges must be a list"
    assert validate_edges([1], {101, 102}) == "each edge must be an object"
    assert validate_edges([{"id": 1}], {101, 102}) == "edge is missing required fields: edge_type, source_node_id, target_node_id"
    assert validate_edges([{**valid_edge, "id": "bad"}], {101, 102}) == "edge id must be an integer"
    assert validate_edges([valid_edge, dict(valid_edge)], {101, 102}) == "duplicate edge id is not allowed"
    assert validate_edges([{**valid_edge, "edge_type": "BadEdge"}], {101, 102}) == "invalid edge_type"
    assert validate_edges([{**valid_edge, "semantic_type_code": "Bad"}], {101, 102}) == "semantic_type_code does not match edge_type"
    assert validate_edges([{**valid_edge, "notation_code": "bad"}], {101, 102}) == "notation_code does not match edge_type"
    assert validate_edges([{**valid_edge, "layer_order": "front"}], {101, 102}) == "layer_order must be an integer"
    assert validate_edges([{**valid_edge, "target_node_id": 999}], {101, 102}) == "edge must reference existing nodes"
    assert validate_edges([{**valid_edge, "target_node_id": 101}], {101, 102}) == "edge cannot connect a node to itself"
    assert validate_edges([valid_edge], {101, 102}) is None


def test_sse_event_formats_event_stream_payload() -> None:
    payload = sse_event("runtime_change", {"view_id": 1, "reason": "runtime_objects_changed"})

    assert payload.startswith("event: runtime_change\n")
    assert '"view_id": 1' in payload
    assert payload.endswith("\n\n")
