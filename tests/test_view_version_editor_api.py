from __future__ import annotations


def login(client, username: str = "admin", password: str = "admin123!"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def create_draft(client):
    response = client.post(
        "/api/views/1/drafts",
        json={"description": "draft for editor api"},
    )
    assert response.status_code == 201
    return response.get_json()


def test_create_version_node_returns_backend_generated_id_and_revision(seeded_client) -> None:
    login(seeded_client)
    draft_payload = create_draft(seeded_client)
    version_id = draft_payload["version"]["id"]
    server_node = next(node for node in draft_payload["nodes"] if node["node_type"] == "PhysicalServer")

    response = seeded_client.post(
        f"/api/view-versions/{version_id}/nodes",
        json={
            "revision": draft_payload["version"]["revision"],
            "node_type": "SoftwareProcess",
            "parent_node_id": server_node["id"],
            "display_name": "Worker Process",
            "target_id": "worker_1",
            "x": 90,
            "y": 170,
            "width": 160,
            "height": 56,
            "style": {"shape": "rounded-rect"},
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["node"]["id"] > max(node["id"] for node in draft_payload["nodes"])
    assert payload["node"]["node_type"] == "SoftwareProcess"
    assert payload["node"]["semantic_type_code"] == "SoftwareProcess"
    assert payload["node"]["notation_code"] == "process.rounded_rect"
    assert payload["node"]["layer_order"] == 40
    assert payload["node"]["element_key"].startswith("softwareprocess_")
    assert payload["revision"] == draft_payload["version"]["revision"] + 1


def test_create_version_node_rejects_invalid_node_type(seeded_client) -> None:
    login(seeded_client)
    draft_payload = create_draft(seeded_client)
    version_id = draft_payload["version"]["id"]

    response = seeded_client.post(
        f"/api/view-versions/{version_id}/nodes",
        json={
            "revision": draft_payload["version"]["revision"],
            "node_type": "UnknownNode",
            "display_name": "Bad Node",
            "x": 10,
            "y": 10,
            "width": 100,
            "height": 50,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_create_version_node_rejects_non_integer_layer_order(seeded_client) -> None:
    login(seeded_client)
    draft_payload = create_draft(seeded_client)
    version_id = draft_payload["version"]["id"]
    server_node = next(node for node in draft_payload["nodes"] if node["node_type"] == "PhysicalServer")

    response = seeded_client.post(
        f"/api/view-versions/{version_id}/nodes",
        json={
            "revision": draft_payload["version"]["revision"],
            "node_type": "SoftwareProcess",
            "parent_node_id": server_node["id"],
            "display_name": "Bad Layer",
            "layer_order": "front",
            "x": 10,
            "y": 10,
            "width": 100,
            "height": 50,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_create_version_node_rejects_non_draft_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/view-versions/1001/nodes",
        json={
            "revision": 1,
            "node_type": "SoftwareProcess",
            "parent_node_id": 1101,
            "display_name": "Blocked",
            "x": 10,
            "y": 10,
            "width": 100,
            "height": 50,
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "version_state_conflict"


def test_update_version_node_updates_layout_and_revision(seeded_client) -> None:
    login(seeded_client)
    draft_payload = create_draft(seeded_client)
    version_id = draft_payload["version"]["id"]
    process_node = next(node for node in draft_payload["nodes"] if node["node_type"] == "SoftwareProcess")

    response = seeded_client.patch(
        f"/api/view-versions/{version_id}/nodes/{process_node['id']}",
        json={
            "revision": draft_payload["version"]["revision"],
            "display_name": "Updated Process",
            "layer_order": 60,
            "x": 140,
            "y": 110,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["node"]["display_name"] == "Updated Process"
    assert payload["node"]["layer_order"] == 60
    assert payload["node"]["x"] == 140
    assert payload["revision"] == draft_payload["version"]["revision"] + 1


def test_create_version_edge_returns_backend_generated_id(seeded_client) -> None:
    login(seeded_client)
    draft_payload = create_draft(seeded_client)
    version_id = draft_payload["version"]["id"]
    process_node = next(node for node in draft_payload["nodes"] if node["node_type"] == "SoftwareProcess")
    agent_node = next(node for node in draft_payload["nodes"] if node["node_type"] == "MonitoringAgent")

    response = seeded_client.post(
        f"/api/view-versions/{version_id}/edges",
        json={
            "revision": draft_payload["version"]["revision"],
            "edge_type": "CommunicationLink",
            "source_node_id": process_node["id"],
            "target_node_id": agent_node["id"],
            "source_anchor": "right",
            "target_anchor": "left",
            "control_points": [],
            "label": "new edge",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["edge"]["id"] > max(edge["id"] for edge in draft_payload["edges"])
    assert payload["edge"]["semantic_type_code"] == "CommunicationLink"
    assert payload["edge"]["notation_code"] == "communication.line"
    assert payload["edge"]["layer_order"] == 20
    assert payload["edge"]["element_key"].startswith("edge_")
    assert payload["revision"] == draft_payload["version"]["revision"] + 1


def test_create_version_edge_rejects_invalid_edge_type(seeded_client) -> None:
    login(seeded_client)
    draft_payload = create_draft(seeded_client)
    version_id = draft_payload["version"]["id"]
    process_node = next(node for node in draft_payload["nodes"] if node["node_type"] == "SoftwareProcess")
    agent_node = next(node for node in draft_payload["nodes"] if node["node_type"] == "MonitoringAgent")

    response = seeded_client.post(
        f"/api/view-versions/{version_id}/edges",
        json={
            "revision": draft_payload["version"]["revision"],
            "edge_type": "BadEdge",
            "source_node_id": process_node["id"],
            "target_node_id": agent_node["id"],
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_replace_version_assigns_ids_for_missing_items_and_increments_revision(seeded_client) -> None:
    login(seeded_client)
    draft_payload = create_draft(seeded_client)
    version_id = draft_payload["version"]["id"]
    server_node = next(node for node in draft_payload["nodes"] if node["node_type"] == "PhysicalServer")

    response = seeded_client.put(
        f"/api/view-versions/{version_id}",
        json={
            "revision": draft_payload["version"]["revision"],
            "nodes": [
                {
                    "id": server_node["id"],
                    "element_key": server_node["element_key"],
                    "node_type": "PhysicalServer",
                    "semantic_type_code": "PhysicalServer",
                    "notation_code": "server.physical.rect",
                    "display_name": "Updated Host",
                    "target_id": None,
                    "layer_order": 10,
                    "x": 40,
                    "y": 40,
                    "width": 500,
                    "height": 280,
                },
                {
                    "node_type": "SoftwareProcess",
                    "parent_node_id": server_node["id"],
                    "display_name": "Generated Worker",
                    "target_id": "generated_worker",
                    "layer_order": 20,
                    "x": 90,
                    "y": 100,
                    "width": 170,
                    "height": 56,
                },
            ],
            "edges": [],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["revision"] == draft_payload["version"]["revision"] + 1

    detail = seeded_client.get(f"/api/view-versions/{version_id}").get_json()
    assert len(detail["nodes"]) == 2
    generated_node = next(node for node in detail["nodes"] if node["display_name"] == "Generated Worker")
    assert isinstance(generated_node["id"], int)
    assert generated_node["id"] > 0
    assert generated_node["element_key"].startswith("softwareprocess_")
