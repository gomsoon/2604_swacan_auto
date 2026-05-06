from __future__ import annotations

from app.editor_api import (
    next_layer_order,
    require_revision,
    resolve_layer_order,
    serialize_edge,
    serialize_node,
    validate_edges,
    validate_nodes,
)


def test_editor_serializers_include_optional_payloads() -> None:
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
            "x": 0,
            "y": 0,
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

    assert node["style"] == {"fill": "blue"}
    assert edge["label"] == "link"
    assert edge["style"] == {"stroke": "red"}
    assert edge["control_points"] == [{"x": 1, "y": 2}]


def test_editor_layer_and_revision_helpers_cover_small_branches(seeded_app) -> None:
    assert next_layer_order([]) == 10
    assert next_layer_order([{"layer_order": 10}, {"layer_order": 40}]) == 50
    assert resolve_layer_order(None, 30) == 30
    assert resolve_layer_order(80, 30) == 80

    try:
        resolve_layer_order("front", 30)
    except ValueError as exc:
        assert str(exc) == "layer_order must be an integer"
    else:
        raise AssertionError("expected ValueError")

    fake_view_row = {"revision": 7}
    with seeded_app.app_context():
        assert require_revision(fake_view_row, {})[1] == 400
        assert require_revision(fake_view_row, {"revision": 99})[1] == 409
        assert require_revision(fake_view_row, {"revision": 7}) is None


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

    assert validate_nodes([{"id": 1}]) == "node is missing required fields: display_name, height, node_type, width, x, y"
    assert validate_nodes([{**physical_server, "node_type": "BadNode"}]) == "invalid node_type"
    assert validate_nodes([{**physical_server, "semantic_type_code": "Bad"}]) == "semantic_type_code does not match node_type"
    assert validate_nodes([{**physical_server, "notation_code": "bad"}]) == "notation_code does not match node_type"
    assert validate_nodes([{**physical_server, "id": "bad"}]) == "node id must be an integer"
    assert validate_nodes([physical_server, dict(physical_server)]) == "duplicate node id is not allowed"
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

    assert validate_edges([{"id": 1}], {101, 102}) == "edge is missing required fields: edge_type, source_node_id, target_node_id"
    assert validate_edges([{**valid_edge, "edge_type": "BadEdge"}], {101, 102}) == "invalid edge_type"
    assert validate_edges([{**valid_edge, "semantic_type_code": "Bad"}], {101, 102}) == "semantic_type_code does not match edge_type"
    assert validate_edges([{**valid_edge, "notation_code": "bad"}], {101, 102}) == "notation_code does not match edge_type"
    assert validate_edges([{**valid_edge, "id": "bad"}], {101, 102}) == "edge id must be an integer"
    assert validate_edges([valid_edge, dict(valid_edge)], {101, 102}) == "duplicate edge id is not allowed"
    assert validate_edges([{**valid_edge, "layer_order": "front"}], {101, 102}) == "layer_order must be an integer"
    assert validate_edges([{**valid_edge, "target_node_id": 999}], {101, 102}) == "edge must reference existing nodes"
    assert validate_edges([{**valid_edge, "target_node_id": 101}], {101, 102}) == "edge cannot connect a node to itself"
    assert validate_edges([valid_edge], {101, 102}) is None
