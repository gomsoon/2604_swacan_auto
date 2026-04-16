from __future__ import annotations

from werkzeug.security import generate_password_hash

from app.db import get_db


def login(client, username: str = "admin", password: str = "admin123!"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def seed_regular_user(app) -> None:
    with app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO users (id, username, password_hash, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 'user', 1, ?, ?)
            """,
            (
                2,
                "viewer",
                generate_password_hash("viewer123!"),
                "2026-04-15T09:00:00.000+09:00",
                "2026-04-15T09:00:00.000+09:00",
            ),
        )
        db_conn.commit()


def test_admin_metamodel_versions_require_admin(seeded_app, seeded_client) -> None:
    response = seeded_client.get("/api/admin/metamodel/versions")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"

    seed_regular_user(seeded_app)
    login_response = login(seeded_client, username="viewer", password="viewer123!")
    assert login_response.status_code == 200

    response = seeded_client.get("/api/admin/metamodel/versions")
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "forbidden"


def test_admin_can_list_metamodel_versions_with_counts(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/metamodel/versions")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    version = payload["items"][0]
    assert version["namespace_code"] == "core"
    assert version["version_code"] == "seed-v1"
    assert version["status"] == "published"
    assert version["semantic_type_count"] == 5
    assert version["notation_count"] == 5
    assert version["palette_group_count"] == 4


def test_admin_can_create_draft_version_by_cloning_existing_version(seeded_app, seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-draft",
            "based_on_version_id": 1,
            "description": "Clone for draft editing",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["version"]["namespace_code"] == "core"
    assert payload["version"]["version_code"] == "seed-v2-draft"
    assert payload["version"]["status"] == "draft"
    assert payload["version"]["based_on_version_id"] == 1

    with seeded_app.app_context():
        db_conn = get_db()
        new_version_id = payload["version"]["id"]
        semantic_type_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM semantic_types WHERE metamodel_version_id = ?",
            (new_version_id,),
        ).fetchone()["count"]
        notation_count = db_conn.execute(
            "SELECT COUNT(*) AS count FROM notation_definitions WHERE metamodel_version_id = ?",
            (new_version_id,),
        ).fetchone()["count"]
        assert semantic_type_count == 5
        assert notation_count == 5

        process_row = db_conn.execute(
            """
            SELECT st.code, nd.code AS default_notation_code
            FROM semantic_types AS st
            LEFT JOIN notation_definitions AS nd ON nd.id = st.default_notation_id
            WHERE st.metamodel_version_id = ? AND st.code = 'SoftwareProcess'
            """,
            (new_version_id,),
        ).fetchone()
        assert process_row["default_notation_code"] == "process.rounded_rect"


def test_admin_can_publish_draft_and_deprecate_previous_published(seeded_app, seeded_client) -> None:
    login(seeded_client)
    create_response = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-draft",
            "based_on_version_id": 1,
            "description": "Clone for publish test",
        },
    )
    assert create_response.status_code == 201
    draft_version_id = create_response.get_json()["version"]["id"]

    publish_response = seeded_client.post(f"/api/admin/metamodel/versions/{draft_version_id}/publish")

    assert publish_response.status_code == 200
    payload = publish_response.get_json()
    assert payload["version"]["id"] == draft_version_id
    assert payload["version"]["status"] == "published"
    assert payload["version"]["published_at"] is not None

    with seeded_app.app_context():
        db_conn = get_db()
        old_version = db_conn.execute(
            "SELECT status FROM metamodel_versions WHERE id = 1",
        ).fetchone()
        new_version = db_conn.execute(
            "SELECT status FROM metamodel_versions WHERE id = ?",
            (draft_version_id,),
        ).fetchone()
        assert old_version["status"] == "deprecated"
        assert new_version["status"] == "published"

    published_response = seeded_client.get("/api/metamodel/versions/published")
    assert published_response.status_code == 200
    published_items = published_response.get_json()["items"]
    assert [item["version_code"] for item in published_items] == ["seed-v2-draft"]


def test_admin_rejects_publish_for_non_draft_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post("/api/admin/metamodel/versions/1/publish")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "publish_conflict"


def test_admin_can_list_semantic_types_for_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/metamodel/versions/1/semantic-types")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"]["version_code"] == "seed-v1"
    assert any(item["code"] == "SoftwareProcess" for item in payload["items"])
    process_type = next(item for item in payload["items"] if item["code"] == "SoftwareProcess")
    assert process_type["default_notation_code"] == "process.rounded_rect"


def test_admin_can_create_semantic_type_in_draft_version(seeded_app, seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v3-draft",
            "based_on_version_id": 1,
            "description": "Draft for semantic type create",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "description": "Grouped worker process type",
            "kind": "node",
            "runtime_kind": "process-group",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["semantic_type"]["code"] == "WorkerPool"
    assert payload["semantic_type"]["display_name"] == "Worker Pool"
    assert payload["semantic_type"]["runtime_kind"] == "process-group"
    assert payload["semantic_type"]["is_groupable"] is True

    with seeded_app.app_context():
        db_conn = get_db()
        row = db_conn.execute(
            "SELECT code, display_name FROM semantic_types WHERE metamodel_version_id = ? AND code = ?",
            (version_id, "WorkerPool"),
        ).fetchone()
        assert row["display_name"] == "Worker Pool"


def test_admin_rejects_semantic_type_create_for_published_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/metamodel/versions/1/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "node",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_can_update_semantic_type_with_boundary_description(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v4-draft",
            "based_on_version_id": 1,
            "description": "Draft for semantic type update",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    create_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "node",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert create_type.status_code == 201
    type_id = create_type.get_json()["semantic_type"]["id"]

    ok_response = seeded_client.patch(
        f"/api/admin/metamodel/semantic-types/{type_id}",
        json={
            "display_name": "Worker Pool Updated",
            "description": "a" * 500,
            "kind": "container",
            "runtime_kind": "process-group",
            "is_groupable": True,
            "allows_runtime_binding": False,
            "is_active": True,
        },
    )
    too_long_response = seeded_client.patch(
        f"/api/admin/metamodel/semantic-types/{type_id}",
        json={
            "display_name": "Worker Pool Updated",
            "description": "a" * 501,
            "kind": "container",
            "runtime_kind": "process-group",
            "is_groupable": True,
            "allows_runtime_binding": False,
            "is_active": True,
        },
    )

    assert ok_response.status_code == 200
    assert ok_response.get_json()["semantic_type"]["display_name"] == "Worker Pool Updated"
    assert ok_response.get_json()["semantic_type"]["kind"] == "container"
    assert ok_response.get_json()["semantic_type"]["allows_runtime_binding"] is False
    assert too_long_response.status_code == 400
    assert too_long_response.get_json()["error"]["code"] == "validation_error"


def test_admin_rejects_invalid_semantic_type_payload_boundaries(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v5-draft",
            "based_on_version_id": 1,
            "description": "Draft for semantic type validation",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    invalid_kind = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "bad-kind",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    invalid_bool = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool2",
            "display_name": "Worker Pool",
            "kind": "node",
            "is_groupable": "true",
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )

    assert invalid_kind.status_code == 400
    assert invalid_kind.get_json()["error"]["code"] == "validation_error"
    assert invalid_bool.status_code == 400
    assert invalid_bool.get_json()["error"]["code"] == "validation_error"


def test_admin_can_list_property_definitions_for_semantic_type(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/metamodel/semantic-types/103/properties")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["semantic_type"]["code"] == "SoftwareProcess"
    assert any(item["code"] == "display_name" for item in payload["items"])
    assert any(item["code"] == "target_id" for item in payload["items"])


def test_admin_can_create_property_definition_in_draft_semantic_type(seeded_app, seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v6-draft",
            "based_on_version_id": 1,
            "description": "Draft for property definition create",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")

    response = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{process_type['id']}/properties",
        json={
            "code": "worker_count",
            "display_name": "Worker Count",
            "description": "Expected worker process count",
            "value_type": "integer",
            "unit": "count",
            "default_value_json": "4",
            "is_required": False,
            "is_runtime": False,
            "is_user_editable": True,
            "sort_order": 30,
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["property_definition"]["code"] == "worker_count"
    assert payload["property_definition"]["default_value"] == 4
    assert payload["property_definition"]["semantic_type_code"] == "SoftwareProcess"

    with seeded_app.app_context():
        db_conn = get_db()
        row = db_conn.execute(
            "SELECT code, display_name, default_value_json FROM property_definitions WHERE semantic_type_id = ? AND code = ?",
            (process_type["id"], "worker_count"),
        ).fetchone()
        assert row["display_name"] == "Worker Count"
        assert row["default_value_json"] == "4"


def test_admin_rejects_property_create_for_published_semantic_type(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/metamodel/semantic-types/103/properties",
        json={
            "code": "worker_count",
            "display_name": "Worker Count",
            "value_type": "integer",
            "is_required": False,
            "is_runtime": False,
            "is_user_editable": True,
            "sort_order": 10,
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_can_update_property_definition_with_boundary_values(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v7-draft",
            "based_on_version_id": 1,
            "description": "Draft for property update",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")
    create_property = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{process_type['id']}/properties",
        json={
            "code": "worker_count",
            "display_name": "Worker Count",
            "value_type": "integer",
            "default_value_json": "4",
            "is_required": False,
            "is_runtime": False,
            "is_user_editable": True,
            "sort_order": 0,
        },
    )
    assert create_property.status_code == 201
    property_id = create_property.get_json()["property_definition"]["id"]

    ok_response = seeded_client.patch(
        f"/api/admin/metamodel/properties/{property_id}",
        json={
            "display_name": "Worker Count Updated",
            "description": "a" * 500,
            "value_type": "number",
            "unit": "threads",
            "default_value_json": "{\"min\":1,\"max\":32}",
            "is_required": True,
            "is_runtime": False,
            "is_user_editable": False,
            "sort_order": 9999,
        },
    )
    too_high_sort_order = seeded_client.patch(
        f"/api/admin/metamodel/properties/{property_id}",
        json={
            "display_name": "Worker Count Updated",
            "description": "ok",
            "value_type": "number",
            "default_value_json": "8",
            "is_required": True,
            "is_runtime": False,
            "is_user_editable": False,
            "sort_order": 10000,
        },
    )

    assert ok_response.status_code == 200
    ok_payload = ok_response.get_json()["property_definition"]
    assert ok_payload["display_name"] == "Worker Count Updated"
    assert ok_payload["sort_order"] == 9999
    assert ok_payload["default_value"] == {"min": 1, "max": 32}
    assert too_high_sort_order.status_code == 400
    assert too_high_sort_order.get_json()["error"]["code"] == "validation_error"


def test_admin_rejects_invalid_property_definition_payload_boundaries(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v8-draft",
            "based_on_version_id": 1,
            "description": "Draft for property validation",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")

    invalid_value_type = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{process_type['id']}/properties",
        json={
            "code": "worker_count",
            "display_name": "Worker Count",
            "value_type": "floatish",
            "is_required": False,
            "is_runtime": False,
            "is_user_editable": True,
            "sort_order": 1,
        },
    )
    invalid_default_json = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{process_type['id']}/properties",
        json={
            "code": "worker_mode",
            "display_name": "Worker Mode",
            "value_type": "json",
            "default_value_json": "{bad-json}",
            "is_required": False,
            "is_runtime": False,
            "is_user_editable": True,
            "sort_order": 1,
        },
    )
    invalid_sort_order = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{process_type['id']}/properties",
        json={
            "code": "worker_flag",
            "display_name": "Worker Flag",
            "value_type": "boolean",
            "is_required": False,
            "is_runtime": False,
            "is_user_editable": True,
            "sort_order": -1,
        },
    )

    assert invalid_value_type.status_code == 400
    assert invalid_value_type.get_json()["error"]["code"] == "validation_error"
    assert invalid_default_json.status_code == 400
    assert invalid_default_json.get_json()["error"]["code"] == "validation_error"
    assert invalid_sort_order.status_code == 400
    assert invalid_sort_order.get_json()["error"]["code"] == "validation_error"
