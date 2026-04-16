from __future__ import annotations

from app.db import get_db


def login(client, username: str = "admin", password: str = "admin123!"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def test_view_versions_require_login(seeded_client) -> None:
    response = seeded_client.get("/api/views/1/versions")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_list_view_versions_returns_seed_active_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/views/1/versions")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["items"] == [
        {
            "id": 1001,
            "view_id": 1,
            "version_no": 1,
            "version_code": "v1-active",
            "status": "active",
            "based_on_version_id": None,
            "metamodel_version_id": 1,
            "description": "Initial active operational snapshot for Demo View",
            "published_at": "2026-04-12T10:00:00.000+09:00",
            "activated_at": "2026-04-12T10:00:00.000+09:00",
            "revision": 1,
            "created_at": "2026-04-12T10:00:00.000+09:00",
            "updated_at": "2026-04-12T10:00:00.000+09:00",
            "node_count": 3,
            "edge_count": 1,
        }
    ]


def test_get_active_view_version_detail_returns_seed_snapshot(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/views/1/active")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view"]["id"] == 1
    assert payload["version"]["id"] == 1001
    assert payload["version"]["status"] == "active"
    assert payload["version"]["metamodel_version_code"] == "seed-v1"
    assert [node["element_key"] for node in payload["nodes"]] == [
        "server_host_a",
        "process_app_main",
        "agent_local_main",
    ]
    assert payload["edges"][0]["element_key"] == "edge_agent_link"
    assert payload["edges"][0]["association_code"] == "monitors"


def test_get_view_version_detail_returns_specific_snapshot(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/view-versions/1001")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"]["version_code"] == "v1-active"
    assert payload["nodes"][0]["notation_code"] == "server.physical.rect"
    assert payload["edges"][0]["semantic_type_code"] == "CommunicationLink"


def test_create_draft_clones_active_version(seeded_app, seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/views/1/drafts",
        json={"description": "운영 버전 기반 수정 초안"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["version"]["status"] == "draft"
    assert payload["version"]["version_no"] == 2
    assert payload["version"]["version_code"] == "v2-draft"
    assert payload["version"]["based_on_version_id"] == 1001
    assert len(payload["nodes"]) == 3
    assert len(payload["edges"]) == 1
    assert [node["element_key"] for node in payload["nodes"]] == [
        "server_host_a",
        "process_app_main",
        "agent_local_main",
    ]

    with seeded_app.app_context():
        db_conn = get_db()
        draft_row = db_conn.execute(
            """
            SELECT id, status, based_on_version_id, metamodel_version_id
            FROM view_versions
            WHERE view_id = 1 AND status = 'draft'
            """
        ).fetchone()
        assert draft_row["based_on_version_id"] == 1001
        assert draft_row["metamodel_version_id"] == 1

        cloned_nodes = db_conn.execute(
            """
            SELECT id, element_key, parent_node_id
            FROM view_version_nodes
            WHERE view_version_id = ?
            ORDER BY layer_order ASC, id ASC
            """,
            (draft_row["id"],),
        ).fetchall()
        cloned_bindings = db_conn.execute(
            """
            SELECT n.element_key, b.monitored_object_id, b.binding_role
            FROM node_bindings AS b
            JOIN view_version_nodes AS n ON n.id = b.view_version_node_id
            WHERE n.view_version_id = ?
            ORDER BY n.id
            """,
            (draft_row["id"],),
        ).fetchall()
        assert len(cloned_nodes) == 3
        assert cloned_nodes[1]["parent_node_id"] is not None
        assert [(row["element_key"], row["monitored_object_id"], row["binding_role"]) for row in cloned_bindings] == [
            ("server_host_a", 1301, "primary"),
            ("process_app_main", 1302, "primary"),
            ("agent_local_main", 1303, "primary"),
        ]


def test_create_draft_rejects_second_open_draft(seeded_client) -> None:
    login(seeded_client)

    first = seeded_client.post("/api/views/1/drafts", json={"description": "first draft"})
    assert first.status_code == 201

    second = seeded_client.post("/api/views/1/drafts", json={"description": "second draft"})
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] == "draft_conflict"


def test_create_draft_rejects_non_integer_based_on_version_id(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/views/1/drafts",
        json={"based_on_version_id": "1001"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_create_draft_rejects_unknown_based_on_version_id(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/views/1/drafts",
        json={"based_on_version_id": 999999},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_create_draft_rejects_cross_view_based_on_version_id(seeded_client) -> None:
    login(seeded_client)

    create_view_response = seeded_client.post(
        "/api/views",
        json={"name": "Cross View Draft", "description": "cross view source test"},
    )
    assert create_view_response.status_code == 201
    view_id = create_view_response.get_json()["view"]["id"]

    response = seeded_client.post(
        f"/api/views/{view_id}/drafts",
        json={"based_on_version_id": 1001},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_get_active_view_version_returns_404_when_missing(seeded_client) -> None:
    login(seeded_client)

    create_view_response = seeded_client.post(
        "/api/views",
        json={"name": "No Active Version View", "description": "no active version"},
    )
    assert create_view_response.status_code == 201
    view_id = create_view_response.get_json()["view"]["id"]

    response = seeded_client.get(f"/api/views/{view_id}/active")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_create_draft_for_new_view_without_source_creates_empty_draft(seeded_app, seeded_client) -> None:
    login(seeded_client)
    create_view_response = seeded_client.post(
        "/api/views",
        json={"name": "Versioned Draft View", "description": "empty draft test"},
    )
    assert create_view_response.status_code == 201
    view_id = create_view_response.get_json()["view"]["id"]

    response = seeded_client.post(
        f"/api/views/{view_id}/drafts",
        json={"description": "빈 초안"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["version"]["view_id"] == view_id
    assert payload["version"]["status"] == "draft"
    assert payload["version"]["version_no"] == 1
    assert payload["version"]["based_on_version_id"] is None
    assert payload["version"]["metamodel_version_id"] == 1
    assert payload["nodes"] == []
    assert payload["edges"] == []

    with seeded_app.app_context():
        db_conn = get_db()
        draft_row = db_conn.execute(
            "SELECT COUNT(*) AS count FROM view_versions WHERE view_id = ? AND status = 'draft'",
            (view_id,),
        ).fetchone()
        assert draft_row["count"] == 1


def test_get_current_draft_returns_created_draft_snapshot(seeded_client) -> None:
    login(seeded_client)
    created = seeded_client.post(
        "/api/views/1/drafts",
        json={"description": "current draft"},
    )
    assert created.status_code == 201
    created_payload = created.get_json()

    response = seeded_client.get("/api/views/1/draft")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["view"]["id"] == 1
    assert payload["version"]["id"] == created_payload["version"]["id"]
    assert payload["version"]["status"] == "draft"
    assert len(payload["nodes"]) == 3
    assert len(payload["edges"]) == 1


def test_get_current_draft_returns_404_when_missing(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/views/1/draft")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_publish_version_changes_draft_to_published(seeded_client) -> None:
    login(seeded_client)
    created = seeded_client.post(
        "/api/views/1/drafts",
        json={"description": "publish me"},
    ).get_json()

    response = seeded_client.post(
        f"/api/view-versions/{created['version']['id']}/publish",
        json={"revision": created["version"]["revision"]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"]["status"] == "published"
    assert payload["version"]["version_code"] == "v2-published"
    assert payload["version"]["published_at"] is not None
    assert payload["version"]["revision"] == created["version"]["revision"] + 1


def test_publish_version_rejects_non_integer_revision(seeded_client) -> None:
    login(seeded_client)
    created = seeded_client.post(
        "/api/views/1/drafts",
        json={"description": "publish bad revision"},
    ).get_json()

    response = seeded_client.post(
        f"/api/view-versions/{created['version']['id']}/publish",
        json={"revision": "2"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_publish_version_rejects_non_draft_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/view-versions/1001/publish",
        json={"revision": 1},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "version_state_conflict"


def test_activate_version_changes_published_to_active_and_deprecates_previous_active(seeded_app, seeded_client) -> None:
    login(seeded_client)
    created = seeded_client.post(
        "/api/views/1/drafts",
        json={"description": "activate me"},
    ).get_json()
    published = seeded_client.post(
        f"/api/view-versions/{created['version']['id']}/publish",
        json={"revision": created["version"]["revision"]},
    ).get_json()

    response = seeded_client.post(
        f"/api/view-versions/{published['version']['id']}/activate",
        json={"revision": published["version"]["revision"]},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"]["status"] == "active"
    assert payload["version"]["version_code"] == "v2-active"
    assert payload["version"]["activated_at"] is not None
    assert payload["version"]["revision"] == published["version"]["revision"] + 1

    with seeded_app.app_context():
        db_conn = get_db()
        previous_active = db_conn.execute(
            "SELECT status, version_code FROM view_versions WHERE id = 1001"
        ).fetchone()
        assert previous_active["status"] == "deprecated"
        assert previous_active["version_code"] == "v1-deprecated"


def test_activate_version_rejects_draft_version(seeded_client) -> None:
    login(seeded_client)
    created = seeded_client.post(
        "/api/views/1/drafts",
        json={"description": "cannot activate draft"},
    ).get_json()

    response = seeded_client.post(
        f"/api/view-versions/{created['version']['id']}/activate",
        json={"revision": created["version"]["revision"]},
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "version_state_conflict"
