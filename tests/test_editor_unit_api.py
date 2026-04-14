from __future__ import annotations


def login(client, username: str = "admin", password: str = "admin123!"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def get_view_detail(client, view_id: int = 1):
    return client.get(f"/api/views/{view_id}").get_json()


def test_create_node_returns_backend_generated_id_and_revision(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/views/1/nodes",
        json={
            "revision": 1,
            "node_type": "SoftwareProcess",
            "parent_node_id": 101,
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
    assert payload["node"]["id"] > 103
    assert payload["node"]["node_type"] == "SoftwareProcess"
    assert payload["node"]["layer_order"] == 40
    assert payload["revision"] == 2

    detail = get_view_detail(seeded_client)
    created = next(node for node in detail["nodes"] if node["id"] == payload["node"]["id"])
    assert created["display_name"] == "Worker Process"
    assert detail["view"]["revision"] == 2


def test_create_node_rejects_invalid_containment(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/views/1/nodes",
        json={
            "revision": 1,
            "node_type": "SoftwareProcess",
            "parent_node_id": 102,
            "display_name": "Bad Child",
            "x": 10,
            "y": 10,
            "width": 100,
            "height": 50,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_create_node_rejects_non_integer_layer_order(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/views/1/nodes",
        json={
            "revision": 1,
            "node_type": "SoftwareProcess",
            "parent_node_id": 101,
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


def test_update_node_updates_layout_and_revision(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.patch(
        "/api/views/1/nodes/102",
        json={
            "revision": 1,
            "display_name": "App Process Patched",
            "layer_order": 60,
            "x": 140,
            "y": 110,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["node"]["display_name"] == "App Process Patched"
    assert payload["node"]["layer_order"] == 60
    assert payload["node"]["x"] == 140
    assert payload["revision"] == 2


def test_delete_node_removes_node_and_increments_revision(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.delete(
        "/api/views/1/nodes/103",
        json={"revision": 1},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["deleted_node_id"] == 103
    assert payload["revision"] == 2

    detail = get_view_detail(seeded_client)
    assert all(node["id"] != 103 for node in detail["nodes"])


def test_create_edge_returns_backend_generated_id(seeded_client) -> None:
    login(seeded_client)

    node_response = seeded_client.post(
        "/api/views/1/nodes",
        json={
            "revision": 1,
            "node_type": "SoftwareProcess",
            "parent_node_id": 101,
            "display_name": "Edge Target",
            "target_id": "edge_target",
            "x": 90,
            "y": 170,
            "width": 160,
            "height": 56,
        },
    )
    node_id = node_response.get_json()["node"]["id"]
    next_revision = node_response.get_json()["revision"]

    response = seeded_client.post(
        "/api/views/1/edges",
        json={
            "revision": next_revision,
            "edge_type": "CommunicationLink",
            "source_node_id": 102,
            "target_node_id": node_id,
            "source_anchor": "right",
            "target_anchor": "left",
            "control_points": [],
            "label": "new edge",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["edge"]["id"] > 201
    assert payload["edge"]["target_node_id"] == node_id
    assert payload["edge"]["layer_order"] == 20
    assert payload["revision"] == next_revision + 1


def test_update_edge_updates_label_and_control_points(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.patch(
        "/api/views/1/edges/201",
        json={
            "revision": 1,
            "label": "updated edge",
            "layer_order": 30,
            "control_points": [{"x": 200, "y": 120}],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["edge"]["label"] == "updated edge"
    assert payload["edge"]["layer_order"] == 30
    assert payload["edge"]["control_points"] == [{"x": 200, "y": 120}]
    assert payload["revision"] == 2


def test_delete_edge_removes_edge_and_increments_revision(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.delete(
        "/api/views/1/edges/201",
        json={"revision": 1},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["deleted_edge_id"] == 201
    assert payload["revision"] == 2

    detail = get_view_detail(seeded_client)
    assert detail["edges"] == []
