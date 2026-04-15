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
