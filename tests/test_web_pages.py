from __future__ import annotations

from werkzeug.security import generate_password_hash

from app.db import get_db


def login(client, username: str = "admin", password: str = "admin123!") -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


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
                "2026-04-13T09:00:00.000+09:00",
                "2026-04-13T09:00:00.000+09:00",
            ),
        )
        db_conn.commit()


def test_root_redirects_to_login_for_anonymous_user(seeded_client) -> None:
    response = seeded_client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_page_renders(seeded_client) -> None:
    response = seeded_client.get("/login")

    assert response.status_code == 200
    assert "로그인".encode("utf-8") in response.data


def test_views_page_redirects_when_not_logged_in(seeded_client) -> None:
    response = seeded_client.get("/views", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_views_page_renders_after_login(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/views")

    assert response.status_code == 200
    assert "뷰 목록".encode("utf-8") in response.data
    assert "admin".encode("utf-8") in response.data


def test_editor_page_renders_after_login(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/views/1/edit")

    assert response.status_code == 200
    assert "Demo View".encode("utf-8") in response.data
    assert "SVG".encode("utf-8") in response.data


def test_monitor_page_renders_after_login(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/views/1/monitor")

    assert response.status_code == 200
    assert "모니터링".encode("utf-8") in response.data


def test_admin_page_renders_for_admin(seeded_client) -> None:
    login(seeded_client)

    response = seeded_client.get("/admin")

    assert response.status_code == 200
    assert "기본 관리자 화면".encode("utf-8") in response.data
    assert "시스템 요약".encode("utf-8") in response.data


def test_admin_page_forbidden_for_non_admin(seeded_app, seeded_client) -> None:
    seed_regular_user(seeded_app)
    login(seeded_client, username="viewer", password="viewer123!")

    response = seeded_client.get("/admin")

    assert response.status_code == 403
