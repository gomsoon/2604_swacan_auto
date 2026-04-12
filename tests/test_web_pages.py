from __future__ import annotations


def login(client) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123!"},
    )
    assert response.status_code == 200


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
