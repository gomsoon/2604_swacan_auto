from __future__ import annotations


def login(client, username: str = "admin", password: str = "admin123!"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def test_metamodel_versions_require_login(seeded_client) -> None:
    response = seeded_client.get("/api/metamodel/versions/published")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_list_published_metamodel_versions_returns_seed_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/metamodel/versions/published")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["items"] == [
        {
            "id": 1,
            "namespace_id": 1,
            "namespace_code": "core",
            "namespace_name": "Core",
            "version_code": "seed-v1",
            "status": "published",
            "description": "Seed metamodel for current MVP baseline",
            "published_at": "2026-04-15T09:00:00.000+09:00",
        }
    ]


def test_palette_returns_grouped_notations(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/metamodel/versions/1/palette")

    assert response.status_code == 200
    payload = response.get_json()
    assert [group["code"] for group in payload["palette_groups"]] == [
        "servers",
        "processes",
        "monitoring",
        "communication",
    ]
    monitoring_group = next(group for group in payload["palette_groups"] if group["code"] == "monitoring")
    agent_item = monitoring_group["items"][0]
    assert agent_item["notation_code"] == "agent.rounded_rect.double_border"
    assert agent_item["render_schema"]["modifiers"]["double_border"] is True


def test_semantic_types_and_properties_return_registry_information(seeded_client) -> None:
    login(seeded_client)

    type_response = seeded_client.get("/api/metamodel/versions/1/semantic-types")
    assert type_response.status_code == 200
    items = type_response.get_json()["items"]
    process_type = next(item for item in items if item["code"] == "SoftwareProcess")
    assert process_type["default_notation_code"] == "process.rounded_rect"
    assert process_type["is_groupable"] is True

    property_response = seeded_client.get("/api/metamodel/versions/1/semantic-types/MonitoringAgent/properties")
    assert property_response.status_code == 200
    property_payload = property_response.get_json()
    assert property_payload["semantic_type_code"] == "MonitoringAgent"
    backend_status = next(item for item in property_payload["items"] if item["code"] == "backend_connection_status")
    assert backend_status["is_runtime"] is True
    assert backend_status["is_user_editable"] is False


def test_containment_association_and_notation_queries_work(seeded_client) -> None:
    login(seeded_client)

    containment_response = seeded_client.get("/api/metamodel/versions/1/containment-rules")
    assert containment_response.status_code == 200
    containment_items = containment_response.get_json()["items"]
    assert any(
        item["parent_type_code"] == "PhysicalServer" and item["child_type_code"] == "SoftwareProcess"
        for item in containment_items
    )

    association_response = seeded_client.get("/api/metamodel/versions/1/associations")
    assert association_response.status_code == 200
    association_items = association_response.get_json()["items"]
    monitors = next(item for item in association_items if item["code"] == "monitors")
    assert monitors["source_type_code"] == "MonitoringAgent"
    assert monitors["target_type_code"] == "SoftwareProcess"

    notation_response = seeded_client.get("/api/metamodel/versions/1/notations?semantic_type_code=MonitoringAgent")
    assert notation_response.status_code == 200
    notation_items = notation_response.get_json()["items"]
    assert len(notation_items) == 1
    assert notation_items[0]["render_primitive"] == "rounded_rect"
