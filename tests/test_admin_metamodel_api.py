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
