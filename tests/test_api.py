from __future__ import annotations


def login(client, username: str = "admin", password: str = "admin123!"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def test_login_success_returns_user(seeded_client) -> None:
    response = login(seeded_client)

    assert response.status_code == 200
    assert response.get_json() == {
        "user": {
            "id": 1,
            "username": "admin",
            "role": "admin",
        }
    }


def test_login_failure_returns_401(seeded_client) -> None:
    response = login(seeded_client, password="wrong-password")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_credentials"


def test_views_require_login(seeded_client) -> None:
    response = seeded_client.get("/api/views")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_list_views_returns_seed_view_for_logged_in_user(seeded_client) -> None:
    login_response = login(seeded_client)
    assert login_response.status_code == 200

    response = seeded_client.get("/api/views")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == 1
    assert payload["items"][0]["name"] == "Demo View"


def test_get_view_detail_returns_seed_nodes_and_edges(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/views/1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view"]["id"] == 1
    assert payload["view"]["revision"] == 1
    assert [node["node_type"] for node in payload["nodes"]] == [
        "PhysicalServer",
        "SoftwareProcess",
        "MonitoringAgent",
    ]
    assert [node["layer_order"] for node in payload["nodes"]] == [10, 20, 30]
    assert payload["edges"][0]["edge_type"] == "CommunicationLink"
    assert payload["edges"][0]["layer_order"] == 10


def test_create_view_creates_owned_view(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/views",
        json={
            "name": "New View",
            "description": "Created in API test",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["view"]["name"] == "New View"
    assert payload["view"]["revision"] == 1

    list_response = seeded_client.get("/api/views")
    items = list_response.get_json()["items"]
    assert len(items) == 2


def test_update_view_updates_revision_and_layout(seeded_client) -> None:
    login(seeded_client)
    detail = seeded_client.get("/api/views/1").get_json()

    nodes = detail["nodes"]
    for node in nodes:
        if node["id"] == 102:
            node["display_name"] = "App Process Updated"
            node["layer_order"] = 50
            node["x"] = 120

    response = seeded_client.put(
        "/api/views/1",
        json={
            "revision": detail["view"]["revision"],
            "nodes": nodes,
            "edges": detail["edges"],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["revision"] == 2

    updated_detail = seeded_client.get("/api/views/1").get_json()
    updated_node = next(node for node in updated_detail["nodes"] if node["id"] == 102)
    assert updated_detail["view"]["revision"] == 2
    assert updated_node["display_name"] == "App Process Updated"
    assert updated_node["layer_order"] == 50
    assert updated_node["x"] == 120


def test_update_view_rejects_revision_mismatch(seeded_client) -> None:
    login(seeded_client)
    detail = seeded_client.get("/api/views/1").get_json()

    response = seeded_client.put(
        "/api/views/1",
        json={
            "revision": 999,
            "nodes": detail["nodes"],
            "edges": detail["edges"],
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "revision_mismatch"
