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
            INSERT INTO users (id, username, password_hash, role, metamodel_permission, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 'user', 'view', 1, ?, ?)
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


def seed_admin_user(app, *, user_id: int, username: str, password: str, metamodel_permission: str) -> None:
    with app.app_context():
        db_conn = get_db()
        db_conn.execute(
            """
            INSERT INTO users (id, username, password_hash, role, metamodel_permission, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 'admin', ?, 1, ?, ?)
            """,
            (
                user_id,
                username,
                generate_password_hash(password),
                metamodel_permission,
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


def test_metamodel_view_permission_allows_read_but_blocks_edit(seeded_app, seeded_client) -> None:
    seed_admin_user(
        seeded_app,
        user_id=3,
        username="meta_viewer",
        password="viewer123!",
        metamodel_permission="view",
    )
    login_response = login(seeded_client, username="meta_viewer", password="viewer123!")
    assert login_response.status_code == 200
    assert login_response.get_json()["user"]["metamodel_permission"] == "view"

    list_response = seeded_client.get("/api/admin/metamodel/versions")
    create_response = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-view-blocked",
            "based_on_version_id": 1,
            "description": "should fail",
        },
    )

    assert list_response.status_code == 200
    assert create_response.status_code == 403
    assert create_response.get_json()["error"]["code"] == "forbidden"


def test_metamodel_edit_permission_allows_edit_but_blocks_publish(seeded_app, seeded_client) -> None:
    seed_admin_user(
        seeded_app,
        user_id=4,
        username="meta_editor",
        password="editor123!",
        metamodel_permission="edit",
    )
    login_response = login(seeded_client, username="meta_editor", password="editor123!")
    assert login_response.status_code == 200
    assert login_response.get_json()["user"]["metamodel_permission"] == "edit"

    create_response = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-edit-allowed",
            "based_on_version_id": 1,
            "description": "edit allowed",
        },
    )
    assert create_response.status_code == 201
    version_id = create_response.get_json()["version"]["id"]

    publish_response = seeded_client.post(f"/api/admin/metamodel/versions/{version_id}/publish")

    assert publish_response.status_code == 403
    assert publish_response.get_json()["error"]["code"] == "forbidden"


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
    assert payload["version"]["based_on_version_code"] == "seed-v1"

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


def test_admin_can_list_metamodel_audit_logs_for_recent_actions(seeded_client) -> None:
    login(seeded_client)

    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-audit-draft",
            "based_on_version_id": 1,
            "description": "Draft for audit test",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    create_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Audit target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert create_type.status_code == 201

    response = seeded_client.get(f"/api/admin/metamodel/audit-logs?version_id={version_id}&limit=20")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) >= 2
    assert payload["items"][0]["actor_username"] == "admin"
    assert any(item["entity_type"] == "metamodel_version" and item["action_type"] == "create" for item in payload["items"])
    assert any(item["entity_type"] == "semantic_type" and item["action_type"] == "create" for item in payload["items"])


def test_admin_metamodel_audit_logs_limit_uses_boundary_validation(seeded_client) -> None:
    login(seeded_client)

    ok_min = seeded_client.get("/api/admin/metamodel/audit-logs?limit=1")
    ok_max = seeded_client.get("/api/admin/metamodel/audit-logs?limit=100")
    too_low = seeded_client.get("/api/admin/metamodel/audit-logs?limit=0")
    too_high = seeded_client.get("/api/admin/metamodel/audit-logs?limit=101")
    not_integer = seeded_client.get("/api/admin/metamodel/audit-logs?limit=abc")

    assert ok_min.status_code == 200
    assert ok_max.status_code == 200
    assert too_low.status_code == 400
    assert too_high.status_code == 400
    assert not_integer.status_code == 400


def test_admin_rejects_publish_for_non_draft_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post("/api/admin/metamodel/versions/1/publish")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "publish_conflict"


def test_admin_can_validate_draft_version_before_publish(seeded_client) -> None:
    login(seeded_client)
    create_response = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-validation-draft",
            "based_on_version_id": 1,
            "description": "Clone for validation test",
        },
    )
    assert create_response.status_code == 201
    draft_version_id = create_response.get_json()["version"]["id"]

    response = seeded_client.get(f"/api/admin/metamodel/versions/{draft_version_id}/validation")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"]["id"] == draft_version_id
    assert payload["validation"]["is_valid"] is True
    assert payload["validation"]["summary"]["error_count"] == 0


def test_admin_rejects_publish_when_validation_fails_missing_default_notation(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-invalid-default-notation",
            "based_on_version_id": 1,
            "description": "Draft with missing default notation",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    create_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Missing default notation target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert create_type.status_code == 201

    validation_response = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/validation")
    assert validation_response.status_code == 200
    validation_payload = validation_response.get_json()["validation"]
    assert validation_payload["is_valid"] is False
    assert any(issue["code"] == "missing_default_notation" for issue in validation_payload["issues"])

    publish_response = seeded_client.post(f"/api/admin/metamodel/versions/{version_id}/publish")
    assert publish_response.status_code == 409
    publish_payload = publish_response.get_json()
    assert publish_payload["error"]["code"] == "validation_failed"
    assert any(issue["code"] == "missing_default_notation" for issue in publish_payload["validation"]["issues"])


def test_admin_rejects_publish_when_validation_fails_containment_cycle(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-invalid-cycle",
            "based_on_version_id": 1,
            "description": "Draft with containment cycle",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    server_type = next(item for item in semantic_types if item["code"] == "PhysicalServer")
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")

    create_cycle = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/containment-rules",
        json={
            "parent_type_id": process_type["id"],
            "child_type_id": server_type["id"],
            "min_count": 0,
            "max_count": 1,
            "cardinality_scope": "group_total",
            "is_required": False,
        },
    )
    assert create_cycle.status_code == 201

    validation_response = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/validation")
    assert validation_response.status_code == 200
    validation_payload = validation_response.get_json()["validation"]
    assert validation_payload["is_valid"] is False
    assert any(issue["code"] == "containment_cycle" for issue in validation_payload["issues"])

    publish_response = seeded_client.post(f"/api/admin/metamodel/versions/{version_id}/publish")
    assert publish_response.status_code == 409
    publish_payload = publish_response.get_json()
    assert publish_payload["error"]["code"] == "validation_failed"
    assert any(issue["code"] == "containment_cycle" for issue in publish_payload["validation"]["issues"])


def test_admin_can_load_metamodel_diff_against_based_on_version(seeded_client) -> None:
    login(seeded_client)
    create_response = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v2-diff-draft",
            "based_on_version_id": 1,
            "description": "Clone for diff test",
        },
    )
    assert create_response.status_code == 201
    version_id = create_response.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")

    update_type = seeded_client.patch(
        f"/api/admin/metamodel/semantic-types/{process_type['id']}",
        json={"display_name": "App Process V2"},
    )
    assert update_type.status_code == 200

    create_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Diff preview type",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert create_type.status_code == 201
    worker_pool_type_id = create_type.get_json()["semantic_type"]["id"]

    create_property = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{worker_pool_type_id}/properties",
        json={
            "code": "worker_count",
            "display_name": "Worker Count",
            "value_type": "integer",
            "unit": "count",
            "default_value_json": "4",
            "sort_order": 10,
            "is_required": False,
            "is_runtime": True,
            "is_user_editable": True,
        },
    )
    assert create_property.status_code == 201

    response = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/diff")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"]["id"] == version_id
    assert payload["diff"]["baseline_version"]["id"] == 1
    assert payload["diff"]["baseline_strategy"] == "based_on_version"
    assert payload["diff"]["summary"]["semantic_types"]["added"] == 1
    assert payload["diff"]["summary"]["semantic_types"]["changed"] == 1
    assert payload["diff"]["summary"]["properties"]["added"] == 1
    assert payload["diff"]["impacts"]["active_view_count"] >= 1
    assert payload["diff"]["impacts"]["active_logical_view_count"] >= 1
    assert any(item["key"] == "WorkerPool" for item in payload["diff"]["sections"]["semantic_types"]["added"])
    assert any(item["key"] == "SoftwareProcess" for item in payload["diff"]["sections"]["semantic_types"]["changed"])


def test_admin_metamodel_diff_returns_not_found_for_unknown_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/metamodel/versions/999999/diff")

    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "metamodel_not_found"


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


def test_admin_can_clone_semantic_type_with_properties_and_notations(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v5-clone-draft",
            "based_on_version_id": 1,
            "description": "Draft for semantic type clone",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    create_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Clone source",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert create_type.status_code == 201
    source_type_id = create_type.get_json()["semantic_type"]["id"]

    property_response = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{source_type_id}/properties",
        json={
            "code": "worker_count",
            "display_name": "Worker Count",
            "value_type": "integer",
            "unit": "count",
            "default_value_json": "4",
            "sort_order": 10,
            "is_required": False,
            "is_runtime": True,
            "is_user_editable": True,
        },
    )
    assert property_response.status_code == 201

    palette_groups = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/palette-groups").get_json()["items"]
    process_palette = next(item for item in palette_groups if item["code"] == "processes")
    notation_response = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{source_type_id}/notations",
        json={
            "semantic_type_id": source_type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.rounded_rect",
            "display_name": "Worker Pool Notation",
            "kind": "node",
            "render_primitive": "rounded_rect",
            "sort_order": 10,
            "render_schema_json": "{\"primitive\":\"rounded_rect\"}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": True,
            "is_visible_in_palette": True,
        },
    )
    assert notation_response.status_code == 201

    clone_response = seeded_client.post(f"/api/admin/metamodel/semantic-types/{source_type_id}/clone")

    assert clone_response.status_code == 201
    payload = clone_response.get_json()
    assert payload["semantic_type"]["id"] != source_type_id
    assert payload["semantic_type"]["code"].startswith("WorkerPool")
    assert payload["clone_summary"]["property_count"] == 1
    assert payload["clone_summary"]["notation_count"] == 1
    assert payload["clone_summary"]["default_notation_cloned"] is True

    properties_payload = seeded_client.get(
        f"/api/admin/metamodel/semantic-types/{payload['semantic_type']['id']}/properties"
    ).get_json()
    notations_payload = seeded_client.get(
        f"/api/admin/metamodel/semantic-types/{payload['semantic_type']['id']}/notations"
    ).get_json()
    assert len(properties_payload["items"]) == 1
    assert properties_payload["items"][0]["code"] == "worker_count"
    assert len(notations_payload["items"]) == 1
    assert notations_payload["items"][0]["is_default"] is True
    assert notations_payload["items"][0]["code"] != "workerpool.rounded_rect"


def test_admin_rejects_clone_for_published_semantic_type(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post("/api/admin/metamodel/semantic-types/103/clone")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_can_delete_unreferenced_semantic_type_and_owned_children(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v5-delete-draft",
            "based_on_version_id": 1,
            "description": "Draft for semantic type delete",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    create_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Delete target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert create_type.status_code == 201
    type_id = create_type.get_json()["semantic_type"]["id"]

    property_response = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/properties",
        json={
            "code": "worker_count",
            "display_name": "Worker Count",
            "value_type": "integer",
            "unit": "count",
            "default_value_json": "4",
            "sort_order": 10,
            "is_required": False,
            "is_runtime": True,
            "is_user_editable": True,
        },
    )
    assert property_response.status_code == 201

    palette_groups = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/palette-groups").get_json()["items"]
    process_palette = next(item for item in palette_groups if item["code"] == "processes")
    notation_response = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/notations",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.rounded_rect",
            "display_name": "Worker Pool Notation",
            "kind": "node",
            "render_primitive": "rounded_rect",
            "sort_order": 10,
            "render_schema_json": "{\"primitive\":\"rounded_rect\"}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": True,
            "is_visible_in_palette": True,
        },
    )
    assert notation_response.status_code == 201

    delete_response = seeded_client.delete(f"/api/admin/metamodel/semantic-types/{type_id}")

    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted"] is True
    list_response = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types")
    assert all(item["id"] != type_id for item in list_response.get_json()["items"])


def test_admin_rejects_delete_when_semantic_type_has_cross_references(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v5-protected-delete-draft",
            "based_on_version_id": 1,
            "description": "Draft for semantic type delete protection",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    create_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Protected delete target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert create_type.status_code == 201
    type_id = create_type.get_json()["semantic_type"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    server_type = next(item for item in semantic_types if item["code"] == "PhysicalServer")
    containment_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/containment-rules",
        json={
            "parent_type_id": server_type["id"],
            "child_type_id": type_id,
            "min_count": 0,
            "max_count": 4,
            "cardinality_scope": "group_total",
            "is_required": False,
        },
    )
    assert containment_response.status_code == 201

    delete_response = seeded_client.delete(f"/api/admin/metamodel/semantic-types/{type_id}")

    assert delete_response.status_code == 409
    payload = delete_response.get_json()
    assert payload["error"]["code"] == "semantic_type_in_use"
    assert payload["dependency_counts"]["containment_in_count"] == 1


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


def test_admin_can_list_containment_rules_for_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/metamodel/versions/1/containment-rules")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"]["version_code"] == "seed-v1"
    assert any(item["parent_type_code"] == "PhysicalServer" and item["child_type_code"] == "SoftwareProcess" for item in payload["items"])


def test_admin_can_create_containment_rule_in_draft_version(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v9-draft",
            "based_on_version_id": 1,
            "description": "Draft for containment rule create",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    parent_type = next(item for item in semantic_types if item["code"] == "PhysicalServer")
    child_type = next(item for item in semantic_types if item["code"] == "CommunicationLink")

    response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/containment-rules",
        json={
            "parent_type_id": parent_type["id"],
            "child_type_id": child_type["id"],
            "min_count": 0,
            "max_count": 1,
            "cardinality_scope": "group_total",
            "is_required": False,
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["containment_rule"]["parent_type_code"] == "PhysicalServer"
    assert payload["containment_rule"]["child_type_code"] == "CommunicationLink"
    assert payload["containment_rule"]["max_count"] == 1


def test_admin_rejects_containment_rule_create_for_published_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/metamodel/versions/1/containment-rules",
        json={
            "parent_type_id": 101,
            "child_type_id": 105,
            "min_count": 0,
            "max_count": 1,
            "cardinality_scope": "group_total",
            "is_required": False,
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_can_update_containment_rule_with_boundary_values(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v10-draft",
            "based_on_version_id": 1,
            "description": "Draft for containment rule update",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    server_type = next(item for item in semantic_types if item["code"] == "PhysicalServer")
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")
    rules = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/containment-rules").get_json()["items"]
    existing_rule = next(
        item
        for item in rules
        if item["parent_type_code"] == "PhysicalServer" and item["child_type_code"] == "SoftwareProcess"
    )
    rule_id = existing_rule["id"]

    ok_response = seeded_client.patch(
        f"/api/admin/metamodel/containment-rules/{rule_id}",
        json={
            "parent_type_id": server_type["id"],
            "child_type_id": process_type["id"],
            "min_count": 1,
            "max_count": 9999,
            "cardinality_scope": "per_member",
            "is_required": True,
        },
    )
    invalid_range = seeded_client.patch(
        f"/api/admin/metamodel/containment-rules/{rule_id}",
        json={
            "parent_type_id": server_type["id"],
            "child_type_id": process_type["id"],
            "min_count": 2,
            "max_count": 1,
            "cardinality_scope": "group_total",
            "is_required": False,
        },
    )

    assert ok_response.status_code == 200
    ok_payload = ok_response.get_json()["containment_rule"]
    assert ok_payload["min_count"] == 1
    assert ok_payload["max_count"] == 9999
    assert ok_payload["cardinality_scope"] == "per_member"
    assert ok_payload["is_required"] is True
    assert invalid_range.status_code == 400
    assert invalid_range.get_json()["error"]["code"] == "validation_error"


def test_admin_rejects_invalid_containment_rule_payload_boundaries(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v11-draft",
            "based_on_version_id": 1,
            "description": "Draft for containment rule validation",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    server_type = next(item for item in semantic_types if item["code"] == "PhysicalServer")
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")

    same_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/containment-rules",
        json={
            "parent_type_id": server_type["id"],
            "child_type_id": server_type["id"],
            "min_count": 0,
            "max_count": None,
            "cardinality_scope": "group_total",
            "is_required": False,
        },
    )
    invalid_scope = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/containment-rules",
        json={
            "parent_type_id": server_type["id"],
            "child_type_id": process_type["id"],
            "min_count": 0,
            "max_count": None,
            "cardinality_scope": "weird_scope",
            "is_required": False,
        },
    )
    invalid_type_membership = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/containment-rules",
        json={
            "parent_type_id": 101,
            "child_type_id": process_type["id"],
            "min_count": 0,
            "max_count": None,
            "cardinality_scope": "group_total",
            "is_required": False,
        },
    )

    assert same_type.status_code == 400
    assert same_type.get_json()["error"]["code"] == "validation_error"
    assert invalid_scope.status_code == 400
    assert invalid_scope.get_json()["error"]["code"] == "validation_error"
    assert invalid_type_membership.status_code == 400
    assert invalid_type_membership.get_json()["error"]["code"] == "validation_error"


def test_admin_can_delete_containment_rule_in_draft_version(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v12-draft",
            "based_on_version_id": 1,
            "description": "Draft for containment delete",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    rules = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/containment-rules").get_json()["items"]
    existing_rule = next(
        item
        for item in rules
        if item["parent_type_code"] == "PhysicalServer" and item["child_type_code"] == "SoftwareProcess"
    )

    delete_response = seeded_client.delete(f"/api/admin/metamodel/containment-rules/{existing_rule['id']}")

    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted"] is True
    remaining_rules = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/containment-rules").get_json()["items"]
    assert all(item["id"] != existing_rule["id"] for item in remaining_rules)


def test_admin_rejects_delete_containment_rule_for_published_version(seeded_client) -> None:
    login(seeded_client)

    rules = seeded_client.get("/api/admin/metamodel/versions/1/containment-rules").get_json()["items"]
    published_rule = next(
        item
        for item in rules
        if item["parent_type_code"] == "PhysicalServer" and item["child_type_code"] == "SoftwareProcess"
    )

    response = seeded_client.delete(f"/api/admin/metamodel/containment-rules/{published_rule['id']}")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_can_list_notation_definitions_for_semantic_type(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/metamodel/semantic-types/103/notations")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["semantic_type"]["code"] == "SoftwareProcess"
    assert any(item["code"] == "process.rounded_rect" for item in payload["items"])
    notation = next(item for item in payload["items"] if item["code"] == "process.rounded_rect")
    assert notation["render_primitive"] == "rounded_rect"


def test_admin_can_create_notation_definition_in_draft_semantic_type(seeded_app, seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v12-draft",
            "based_on_version_id": 1,
            "description": "Draft for notation definition create",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_type_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Notation target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert semantic_type_response.status_code == 201
    type_id = semantic_type_response.get_json()["semantic_type"]["id"]

    palette_groups = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/palette-groups").get_json()["items"]
    process_palette = next(item for item in palette_groups if item["code"] == "processes")

    response = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/notations",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.rounded_rect",
            "display_name": "Worker Pool Notation",
            "kind": "node",
            "render_primitive": "rounded_rect",
            "sort_order": 10,
            "render_schema_json": "{\"primitive\":\"rounded_rect\",\"default_size\":{\"width\":220,\"height\":88}}",
            "style_tokens_json": "{\"fill\":\"process-fill\",\"stroke\":\"process-stroke\"}",
            "is_default": True,
            "is_visible_in_palette": True,
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["notation_definition"]["code"] == "workerpool.rounded_rect"
    assert payload["notation_definition"]["palette_group_code"] == "processes"
    assert payload["notation_definition"]["is_default"] is True
    assert payload["notation_definition"]["render_schema"]["primitive"] == "rounded_rect"

    with seeded_app.app_context():
        db_conn = get_db()
        notation_row = db_conn.execute(
            """
            SELECT code, render_primitive, is_default
            FROM notation_definitions
            WHERE semantic_type_id = ? AND code = ?
            """,
            (type_id, "workerpool.rounded_rect"),
        ).fetchone()
        semantic_type_row = db_conn.execute(
            "SELECT default_notation_id FROM semantic_types WHERE id = ?",
            (type_id,),
        ).fetchone()
        assert notation_row["render_primitive"] == "rounded_rect"
        assert notation_row["is_default"] == 1
        assert semantic_type_row["default_notation_id"] is not None


def test_admin_rejects_notation_create_for_published_semantic_type(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/metamodel/semantic-types/103/notations",
        json={
            "semantic_type_id": 103,
            "palette_group_id": 2,
            "code": "process.alt",
            "display_name": "Process Alt",
            "kind": "node",
            "render_primitive": "rounded_rect",
            "sort_order": 50,
            "render_schema_json": "{\"primitive\":\"rounded_rect\"}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": False,
            "is_visible_in_palette": True,
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_can_update_notation_definition_with_boundary_values(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v13-draft",
            "based_on_version_id": 1,
            "description": "Draft for notation update",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_type_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Notation update target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    type_id = semantic_type_response.get_json()["semantic_type"]["id"]
    palette_groups = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/palette-groups").get_json()["items"]
    process_palette = next(item for item in palette_groups if item["code"] == "processes")

    create_notation = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/notations",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.rounded_rect",
            "display_name": "Worker Pool Notation",
            "kind": "node",
            "render_primitive": "rounded_rect",
            "sort_order": 10,
            "render_schema_json": "{\"primitive\":\"rounded_rect\"}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": True,
            "is_visible_in_palette": True,
        },
    )
    assert create_notation.status_code == 201
    notation_id = create_notation.get_json()["notation_definition"]["id"]

    ok_response = seeded_client.patch(
        f"/api/admin/metamodel/notations/{notation_id}",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.rounded_rect.alt",
            "display_name": "Worker Pool Notation Updated",
            "kind": "node",
            "render_primitive": "rect",
            "sort_order": 9999,
            "render_schema_json": "{\"primitive\":\"rect\",\"default_size\":{\"width\":180,\"height\":72}}",
            "style_tokens_json": "{\"fill\":\"process-fill\",\"stroke\":\"process-stroke\",\"label\":\"process-label\"}",
            "is_default": False,
            "is_visible_in_palette": False,
        },
    )
    too_high_sort_order = seeded_client.patch(
        f"/api/admin/metamodel/notations/{notation_id}",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.rounded_rect.alt",
            "display_name": "Worker Pool Notation Updated",
            "kind": "node",
            "render_primitive": "rect",
            "sort_order": 10000,
            "render_schema_json": "{\"primitive\":\"rect\"}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": False,
            "is_visible_in_palette": False,
        },
    )

    assert ok_response.status_code == 200
    ok_payload = ok_response.get_json()["notation_definition"]
    assert ok_payload["code"] == "workerpool.rounded_rect.alt"
    assert ok_payload["sort_order"] == 9999
    assert ok_payload["render_primitive"] == "rect"
    assert ok_payload["is_visible_in_palette"] is False
    assert too_high_sort_order.status_code == 400
    assert too_high_sort_order.get_json()["error"]["code"] == "validation_error"


def test_admin_rejects_invalid_notation_definition_payload_boundaries(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v14-draft",
            "based_on_version_id": 1,
            "description": "Draft for notation validation",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_type_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Notation validation target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    type_id = semantic_type_response.get_json()["semantic_type"]["id"]
    palette_groups = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/palette-groups").get_json()["items"]
    process_palette = next(item for item in palette_groups if item["code"] == "processes")

    invalid_render_primitive = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/notations",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.bad.primitive",
            "display_name": "Worker Pool Bad Primitive",
            "kind": "node",
            "render_primitive": "ellipse",
            "sort_order": 1,
            "render_schema_json": "{\"primitive\":\"ellipse\"}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": False,
            "is_visible_in_palette": True,
        },
    )
    invalid_schema_json = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/notations",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.bad.schema",
            "display_name": "Worker Pool Bad Schema",
            "kind": "node",
            "render_primitive": "rounded_rect",
            "sort_order": 1,
            "render_schema_json": "{bad-json}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": False,
            "is_visible_in_palette": True,
        },
    )
    invalid_kind_for_node_type = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/notations",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.edge.kind",
            "display_name": "Worker Pool Edge Kind",
            "kind": "edge",
            "render_primitive": "line",
            "sort_order": 1,
            "render_schema_json": "{\"primitive\":\"line\"}",
            "style_tokens_json": "{\"stroke\":\"process-stroke\"}",
            "is_default": False,
            "is_visible_in_palette": True,
        },
    )
    invalid_palette_group_membership = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/notations",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": 1,
            "code": "workerpool.bad.palette",
            "display_name": "Worker Pool Bad Palette",
            "kind": "node",
            "render_primitive": "rounded_rect",
            "sort_order": 1,
            "render_schema_json": "{\"primitive\":\"rounded_rect\"}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": False,
            "is_visible_in_palette": True,
        },
    )

    assert invalid_render_primitive.status_code == 400
    assert invalid_render_primitive.get_json()["error"]["code"] == "validation_error"
    assert invalid_schema_json.status_code == 400
    assert invalid_schema_json.get_json()["error"]["code"] == "validation_error"
    assert invalid_kind_for_node_type.status_code == 400
    assert invalid_kind_for_node_type.get_json()["error"]["code"] == "validation_error"
    assert invalid_palette_group_membership.status_code == 400
    assert invalid_palette_group_membership.get_json()["error"]["code"] == "validation_error"


def test_admin_can_clone_notation_definition_as_secondary(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v14-notation-clone-draft",
            "based_on_version_id": 1,
            "description": "Draft for notation clone",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_type_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Notation clone target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    type_id = semantic_type_response.get_json()["semantic_type"]["id"]
    palette_groups = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/palette-groups").get_json()["items"]
    process_palette = next(item for item in palette_groups if item["code"] == "processes")

    create_notation = seeded_client.post(
        f"/api/admin/metamodel/semantic-types/{type_id}/notations",
        json={
            "semantic_type_id": type_id,
            "palette_group_id": process_palette["id"],
            "code": "workerpool.rounded_rect",
            "display_name": "Worker Pool Notation",
            "kind": "node",
            "render_primitive": "rounded_rect",
            "sort_order": 10,
            "render_schema_json": "{\"primitive\":\"rounded_rect\"}",
            "style_tokens_json": "{\"fill\":\"process-fill\"}",
            "is_default": True,
            "is_visible_in_palette": False,
        },
    )
    assert create_notation.status_code == 201
    notation_id = create_notation.get_json()["notation_definition"]["id"]

    clone_response = seeded_client.post(f"/api/admin/metamodel/notations/{notation_id}/clone")

    assert clone_response.status_code == 201
    payload = clone_response.get_json()
    assert payload["notation_definition"]["id"] != notation_id
    assert payload["notation_definition"]["code"] != "workerpool.rounded_rect"
    assert payload["notation_definition"]["display_name"].startswith("Worker Pool Notation")
    assert payload["notation_definition"]["is_default"] is False
    assert payload["notation_definition"]["is_visible_in_palette"] is False
    assert payload["clone_summary"]["default_copied_as_secondary"] is True


def test_admin_rejects_clone_for_published_notation_definition(seeded_client) -> None:
    login(seeded_client)
    published_notations = seeded_client.get("/api/admin/metamodel/semantic-types/103/notations").get_json()["items"]
    published_notation = next(item for item in published_notations if item["code"] == "process.rounded_rect")

    response = seeded_client.post(f"/api/admin/metamodel/notations/{published_notation['id']}/clone")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_can_delete_non_default_notation_definition(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v14-notation-delete-draft",
            "based_on_version_id": 1,
            "description": "Draft for notation delete",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")
    notations = seeded_client.get(f"/api/admin/metamodel/semantic-types/{process_type['id']}/notations").get_json()["items"]
    default_notation = next(item for item in notations if item["is_default"] is True)

    clone_response = seeded_client.post(f"/api/admin/metamodel/notations/{default_notation['id']}/clone")
    assert clone_response.status_code == 201
    cloned_id = clone_response.get_json()["notation_definition"]["id"]

    delete_response = seeded_client.delete(f"/api/admin/metamodel/notations/{cloned_id}")

    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted"] is True
    list_response = seeded_client.get(f"/api/admin/metamodel/semantic-types/{process_type['id']}/notations")
    assert all(item["id"] != cloned_id for item in list_response.get_json()["items"])


def test_admin_rejects_delete_for_default_notation_definition(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v14-notation-delete-protected-draft",
            "based_on_version_id": 1,
            "description": "Draft for protected notation delete",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    process_type = next(item for item in semantic_types if item["code"] == "SoftwareProcess")
    notations = seeded_client.get(f"/api/admin/metamodel/semantic-types/{process_type['id']}/notations").get_json()["items"]
    default_notation = next(item for item in notations if item["is_default"] is True)

    delete_response = seeded_client.delete(f"/api/admin/metamodel/notations/{default_notation['id']}")

    assert delete_response.status_code == 409
    payload = delete_response.get_json()
    assert payload["error"]["code"] == "notation_in_use"
    assert payload["dependency_counts"]["default_reference_count"] == 1


def test_admin_can_list_association_definitions_for_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/api/admin/metamodel/versions/1/associations")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"]["version_code"] == "seed-v1"
    assert any(item["code"] == "communicates_with" for item in payload["items"])
    assert any(item["code"] == "monitors" for item in payload["items"])


def test_admin_can_create_association_definition_in_draft_version(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v15-draft",
            "based_on_version_id": 1,
            "description": "Draft for association definition create",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_type_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Association target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    assert semantic_type_response.status_code == 201
    worker_pool_id = semantic_type_response.get_json()["semantic_type"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    agent_type = next(item for item in semantic_types if item["code"] == "MonitoringAgent")

    response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/associations",
        json={
            "code": "monitors_worker_pool",
            "display_name": "Monitors Worker Pool",
            "description": "Monitoring agent observes worker pool state",
            "source_type_id": agent_type["id"],
            "target_type_id": worker_pool_id,
            "direction": "directed",
            "multiplicity_source": "1",
            "multiplicity_target": "0..n",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\"}",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["association_definition"]["code"] == "monitors_worker_pool"
    assert payload["association_definition"]["source_type_code"] == "MonitoringAgent"
    assert payload["association_definition"]["target_type_code"] == "WorkerPool"
    assert payload["association_definition"]["semantics"]["default_edge_type"] == "CommunicationLink"


def test_admin_rejects_association_create_for_published_version(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.post(
        "/api/admin/metamodel/versions/1/associations",
        json={
            "code": "monitors_worker_pool",
            "display_name": "Monitors Worker Pool",
            "description": "Monitoring agent observes worker pool state",
            "source_type_id": 104,
            "target_type_id": 103,
            "direction": "directed",
            "multiplicity_source": "1",
            "multiplicity_target": "0..n",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\"}",
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"


def test_admin_can_update_association_definition_with_boundary_values(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v16-draft",
            "based_on_version_id": 1,
            "description": "Draft for association update",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_type_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Association update target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    worker_pool_id = semantic_type_response.get_json()["semantic_type"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    agent_type = next(item for item in semantic_types if item["code"] == "MonitoringAgent")

    create_association = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/associations",
        json={
            "code": "monitors_worker_pool",
            "display_name": "Monitors Worker Pool",
            "description": "Monitoring agent observes worker pool state",
            "source_type_id": agent_type["id"],
            "target_type_id": worker_pool_id,
            "direction": "directed",
            "multiplicity_source": "1",
            "multiplicity_target": "0..n",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\"}",
        },
    )
    assert create_association.status_code == 201
    association_id = create_association.get_json()["association_definition"]["id"]

    ok_response = seeded_client.patch(
        f"/api/admin/metamodel/associations/{association_id}",
        json={
            "code": "monitors_worker_pool_updated",
            "display_name": "Monitors Worker Pool Updated",
            "description": "a" * 500,
            "source_type_id": agent_type["id"],
            "target_type_id": worker_pool_id,
            "direction": "undirected",
            "multiplicity_source": "0..1",
            "multiplicity_target": "1..n",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\",\"visual_hint\":\"dashed\"}",
        },
    )
    invalid_description = seeded_client.patch(
        f"/api/admin/metamodel/associations/{association_id}",
        json={
            "code": "monitors_worker_pool_updated",
            "display_name": "Monitors Worker Pool Updated",
            "description": "a" * 501,
            "source_type_id": agent_type["id"],
            "target_type_id": worker_pool_id,
            "direction": "undirected",
            "multiplicity_source": "0..1",
            "multiplicity_target": "1..n",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\"}",
        },
    )

    assert ok_response.status_code == 200
    ok_payload = ok_response.get_json()["association_definition"]
    assert ok_payload["code"] == "monitors_worker_pool_updated"
    assert ok_payload["direction"] == "undirected"
    assert ok_payload["multiplicity_target"] == "1..n"
    assert ok_payload["semantics"]["visual_hint"] == "dashed"
    assert invalid_description.status_code == 400
    assert invalid_description.get_json()["error"]["code"] == "validation_error"


def test_admin_rejects_invalid_association_definition_payload_boundaries(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v17-draft",
            "based_on_version_id": 1,
            "description": "Draft for association validation",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_type_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Association validation target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    worker_pool_id = semantic_type_response.get_json()["semantic_type"]["id"]

    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    agent_type = next(item for item in semantic_types if item["code"] == "MonitoringAgent")

    same_type = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/associations",
        json={
            "code": "self_link",
            "display_name": "Self Link",
            "description": "Invalid self link",
            "source_type_id": worker_pool_id,
            "target_type_id": worker_pool_id,
            "direction": "directed",
            "multiplicity_source": "1",
            "multiplicity_target": "1",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\"}",
        },
    )
    invalid_direction = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/associations",
        json={
            "code": "bad_direction",
            "display_name": "Bad Direction",
            "description": "Invalid direction",
            "source_type_id": agent_type["id"],
            "target_type_id": worker_pool_id,
            "direction": "two_way",
            "multiplicity_source": "1",
            "multiplicity_target": "1",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\"}",
        },
    )
    invalid_semantics_json = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/associations",
        json={
            "code": "bad_semantics",
            "display_name": "Bad Semantics",
            "description": "Invalid semantics json",
            "source_type_id": agent_type["id"],
            "target_type_id": worker_pool_id,
            "direction": "directed",
            "multiplicity_source": "1",
            "multiplicity_target": "1",
            "semantics_json": "{bad-json}",
        },
    )
    invalid_type_membership = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/associations",
        json={
            "code": "bad_membership",
            "display_name": "Bad Membership",
            "description": "Foreign type membership",
            "source_type_id": 104,
            "target_type_id": worker_pool_id,
            "direction": "directed",
            "multiplicity_source": "1",
            "multiplicity_target": "1",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\"}",
        },
    )

    assert same_type.status_code == 400
    assert same_type.get_json()["error"]["code"] == "validation_error"
    assert invalid_direction.status_code == 400
    assert invalid_direction.get_json()["error"]["code"] == "validation_error"
    assert invalid_semantics_json.status_code == 400
    assert invalid_semantics_json.get_json()["error"]["code"] == "validation_error"
    assert invalid_type_membership.status_code == 400
    assert invalid_type_membership.get_json()["error"]["code"] == "validation_error"


def test_admin_can_delete_association_definition_in_draft_version(seeded_client) -> None:
    login(seeded_client)
    create_version = seeded_client.post(
        "/api/admin/metamodel/versions",
        json={
            "namespace_code": "core",
            "version_code": "seed-v18-draft",
            "based_on_version_id": 1,
            "description": "Draft for association delete",
        },
    )
    assert create_version.status_code == 201
    version_id = create_version.get_json()["version"]["id"]

    semantic_type_response = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/semantic-types",
        json={
            "code": "WorkerPool",
            "display_name": "Worker Pool",
            "kind": "container",
            "runtime_kind": "process-group",
            "description": "Association delete target",
            "is_groupable": True,
            "allows_runtime_binding": True,
            "is_active": True,
        },
    )
    worker_pool_id = semantic_type_response.get_json()["semantic_type"]["id"]
    semantic_types = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/semantic-types").get_json()["items"]
    agent_type = next(item for item in semantic_types if item["code"] == "MonitoringAgent")

    create_association = seeded_client.post(
        f"/api/admin/metamodel/versions/{version_id}/associations",
        json={
            "code": "monitors_worker_pool",
            "display_name": "Monitors Worker Pool",
            "description": "Association delete candidate",
            "source_type_id": agent_type["id"],
            "target_type_id": worker_pool_id,
            "direction": "directed",
            "multiplicity_source": "1",
            "multiplicity_target": "0..n",
            "semantics_json": "{\"default_edge_type\":\"CommunicationLink\"}",
        },
    )
    assert create_association.status_code == 201
    association_id = create_association.get_json()["association_definition"]["id"]

    delete_response = seeded_client.delete(f"/api/admin/metamodel/associations/{association_id}")

    assert delete_response.status_code == 200
    assert delete_response.get_json()["deleted"] is True
    remaining = seeded_client.get(f"/api/admin/metamodel/versions/{version_id}/associations").get_json()["items"]
    assert all(item["id"] != association_id for item in remaining)


def test_admin_rejects_delete_association_definition_for_published_version(seeded_client) -> None:
    login(seeded_client)

    associations = seeded_client.get("/api/admin/metamodel/versions/1/associations").get_json()["items"]
    published_association = next(item for item in associations if item["code"] == "monitors")

    response = seeded_client.delete(f"/api/admin/metamodel/associations/{published_association['id']}")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "invalid_state"
