from __future__ import annotations

from app.view_version_editor_api import (
    association_matches_nodes,
    find_association_by_code,
    infer_runtime_kind_from_object_type,
    make_element_key,
    parse_monitored_object_limit,
    parse_optional_current_node_id,
    resolve_edge_defaults,
    resolve_node_defaults,
    slugify,
    validate_edges_against_metamodel,
    validate_node_properties,
    validate_nodes_against_metamodel,
    validate_property_value,
)


def make_editor_metamodel() -> dict:
    associations = [
        {
            "code": "monitors",
            "direction": "directed",
            "source_type_code": "MonitoringAgent",
            "target_type_code": "SoftwareProcess",
            "semantics": {"default_edge_type": "CommunicationLink"},
        },
        {
            "code": "peer_link",
            "direction": "undirected",
            "source_type_code": "SoftwareProcess",
            "target_type_code": "MonitoringAgent",
            "semantics": {},
        },
    ]
    semantic_types = {
        "PhysicalServer": {
            "code": "PhysicalServer",
            "allows_runtime_binding": False,
            "default_notation_code": "server.physical.rect",
        },
        "SoftwareProcess": {
            "code": "SoftwareProcess",
            "allows_runtime_binding": True,
            "default_notation_code": "process.rounded_rect",
        },
        "MonitoringAgent": {
            "code": "MonitoringAgent",
            "allows_runtime_binding": True,
            "default_notation_code": "agent.rounded_rect",
        },
        "CommunicationLink": {
            "code": "CommunicationLink",
            "allows_runtime_binding": False,
            "default_notation_code": "communication.line",
        },
    }
    notations = {
        "server.physical.rect": {"code": "server.physical.rect", "semantic_type_code": "PhysicalServer", "kind": "node"},
        "process.rounded_rect": {"code": "process.rounded_rect", "semantic_type_code": "SoftwareProcess", "kind": "node"},
        "agent.rounded_rect": {"code": "agent.rounded_rect", "semantic_type_code": "MonitoringAgent", "kind": "node"},
        "communication.line": {"code": "communication.line", "semantic_type_code": "CommunicationLink", "kind": "edge"},
    }
    return {
        "snapshot": {"associations": associations},
        "semantic_types_by_code": semantic_types,
        "notation_by_code": notations,
        "allowed_node_types": {"PhysicalServer", "SoftwareProcess", "MonitoringAgent"},
        "allowed_edge_types": {"CommunicationLink"},
        "containment_pairs": {("PhysicalServer", "SoftwareProcess"), ("PhysicalServer", "MonitoringAgent")},
        "property_definitions_by_type": {
            "SoftwareProcess": [
                {
                    "code": "replicas",
                    "is_user_editable": True,
                    "is_runtime": False,
                    "is_required": True,
                    "value_type": "integer",
                }
            ]
        },
        "allowed_parent_codes_by_child": {
            "SoftwareProcess": {"PhysicalServer"},
            "MonitoringAgent": {"PhysicalServer"},
        },
    }


def test_view_version_editor_helper_functions_cover_small_branches(seeded_app) -> None:
    assert slugify("  CPU High !!  ") == "cpu_high"
    assert slugify("  ") == "item"
    assert make_element_key("edge", "Process Link", {"edge_process_link"}) == "edge_process_link_2"
    assert infer_runtime_kind_from_object_type("MonitoringAgent") == "agent"
    assert infer_runtime_kind_from_object_type("WorkerProcess") == "process"
    assert infer_runtime_kind_from_object_type("VirtualMachine") == "host"
    assert infer_runtime_kind_from_object_type("CustomThing") is None
    assert validate_property_value("string", "ok") is True
    assert validate_property_value("integer", True) is False
    assert validate_property_value("number", 1.5) is True
    assert validate_property_value("boolean", False) is True

    with seeded_app.test_request_context("/api/view-versions/1/monitored-objects?limit=3&current_node_id=21"):
        limit, error = parse_monitored_object_limit()
        node_id, node_error = parse_optional_current_node_id()
    assert limit == 3
    assert error is None
    assert node_id == 21
    assert node_error is None

    with seeded_app.test_request_context("/api/view-versions/1/monitored-objects?limit=bad"):
        limit, error = parse_monitored_object_limit()
    assert limit is None
    assert error[1] == 400

    with seeded_app.test_request_context("/api/view-versions/1/monitored-objects?current_node_id=nope"):
        node_id, node_error = parse_optional_current_node_id()
    assert node_id is None
    assert node_error[1] == 400


def test_view_version_editor_validator_helpers_cover_decision_matrix() -> None:
    editor_metamodel = make_editor_metamodel()

    assert resolve_node_defaults(editor_metamodel, "SoftwareProcess") == {
        "semantic_type_code": "SoftwareProcess",
        "notation_code": "process.rounded_rect",
    }
    assert resolve_node_defaults(editor_metamodel, "BadNode") is None
    assert resolve_edge_defaults(editor_metamodel, "CommunicationLink") == {
        "semantic_type_code": "CommunicationLink",
        "notation_code": "communication.line",
    }
    assert resolve_edge_defaults(editor_metamodel, "BadEdge") is None
    assert find_association_by_code(editor_metamodel, "monitors")["code"] == "monitors"
    assert find_association_by_code(editor_metamodel, "missing") is None
    assert association_matches_nodes(
        find_association_by_code(editor_metamodel, "monitors"),
        "MonitoringAgent",
        "SoftwareProcess",
    ) is True
    assert association_matches_nodes(
        find_association_by_code(editor_metamodel, "peer_link"),
        "MonitoringAgent",
        "SoftwareProcess",
    ) is True

    process_node = {
        "id": 102,
        "node_type": "SoftwareProcess",
        "display_name": "Worker",
        "parent_node_id": 101,
        "semantic_type_code": "SoftwareProcess",
        "notation_code": "process.rounded_rect",
        "x": 10,
        "y": 10,
        "width": 120,
        "height": 60,
        "properties": {"replicas": 2},
    }
    server_node = {
        "id": 101,
        "node_type": "PhysicalServer",
        "display_name": "Host",
        "semantic_type_code": "PhysicalServer",
        "notation_code": "server.physical.rect",
        "x": 0,
        "y": 0,
        "width": 300,
        "height": 200,
        "properties": {},
    }
    agent_node = {
        "id": 103,
        "node_type": "MonitoringAgent",
        "display_name": "Agent",
        "parent_node_id": 101,
        "semantic_type_code": "MonitoringAgent",
        "notation_code": "agent.rounded_rect",
        "x": 20,
        "y": 20,
        "width": 120,
        "height": 60,
        "properties": {},
    }

    assert validate_node_properties({**process_node, "properties": ["bad"]}, editor_metamodel) == "properties must be an object"
    assert validate_node_properties({**process_node, "properties": {"unknown": 1}}, editor_metamodel) == "unknown property codes: unknown"
    assert validate_node_properties({**process_node, "properties": {}}, editor_metamodel) == "property 'replicas' is required"
    assert (
        validate_node_properties({**process_node, "properties": {"replicas": "two"}}, editor_metamodel)
        == "property 'replicas' does not match value_type 'integer'"
    )
    assert validate_node_properties(process_node, editor_metamodel) is None

    assert validate_nodes_against_metamodel([{**server_node, "target_id": "host1"}], editor_metamodel) == "target_id is not allowed for this semantic type"
    assert validate_nodes_against_metamodel([{**server_node, "id": "bad"}], editor_metamodel) == "node id must be an integer"
    assert validate_nodes_against_metamodel([server_node, dict(server_node)], editor_metamodel) == "duplicate node id is not allowed"
    assert validate_nodes_against_metamodel([{**server_node, "layer_order": "front"}], editor_metamodel) == "layer_order must be an integer"
    assert validate_nodes_against_metamodel([{**process_node, "parent_node_id": None}], editor_metamodel) == "SoftwareProcess must have a parent_node_id"
    assert validate_nodes_against_metamodel([process_node], editor_metamodel) == "parent_node_id must reference an existing node"
    assert validate_nodes_against_metamodel([server_node, process_node, agent_node], editor_metamodel) is None

    valid_edge = {
        "id": 201,
        "edge_type": "CommunicationLink",
        "semantic_type_code": "CommunicationLink",
        "notation_code": "communication.line",
        "source_node_id": 103,
        "target_node_id": 102,
    }
    nodes = [server_node, process_node, agent_node]
    assert validate_edges_against_metamodel([{**valid_edge, "association_code": "missing"}], nodes, editor_metamodel) == "association_code is invalid"
    assert (
        validate_edges_against_metamodel(
            [{**valid_edge, "association_code": "monitors", "source_node_id": 102, "target_node_id": 103}],
            nodes,
            editor_metamodel,
        )
        == "association_code does not match source/target semantic types"
    )
    mismatch_editor_metamodel = make_editor_metamodel()
    mismatch_editor_metamodel["snapshot"]["associations"][0]["semantics"]["default_edge_type"] = "TelemetryLink"
    assert (
        validate_edges_against_metamodel(
            [{**valid_edge, "association_code": "monitors"}],
            nodes,
            mismatch_editor_metamodel,
        )
        == "association_code does not match edge_type"
    )
    assert validate_edges_against_metamodel([{**valid_edge, "association_code": "monitors"}], nodes, editor_metamodel) is None
