from __future__ import annotations

from app.db import get_db


def test_health_endpoint(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_init_db_loads_seed_data(seeded_app) -> None:
    with seeded_app.app_context():
        db_conn = get_db()

        user_row = db_conn.execute(
            "SELECT username, role FROM users WHERE id = 1"
        ).fetchone()
        node_rows = db_conn.execute(
            "SELECT id, node_type, display_name FROM view_nodes ORDER BY id"
        ).fetchall()
        edge_row = db_conn.execute(
            "SELECT edge_type, source_node_id, target_node_id FROM view_edges WHERE id = 201"
        ).fetchone()

    assert user_row["username"] == "admin"
    assert user_row["role"] == "admin"
    assert [row["node_type"] for row in node_rows] == [
        "PhysicalServer",
        "SoftwareProcess",
        "MonitoringAgent",
    ]
    assert edge_row["edge_type"] == "CommunicationLink"
    assert edge_row["source_node_id"] == 102
    assert edge_row["target_node_id"] == 103


def test_init_db_cli_command(runner, app) -> None:
    result = runner.invoke(args=["init-db", "--seed"])

    assert result.exit_code == 0
    assert "Initialized the database." in result.output

    with app.app_context():
        db_conn = get_db()
        counts = db_conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM users) AS users_count,
                (SELECT COUNT(*) FROM view_nodes) AS nodes_count,
                (SELECT COUNT(*) FROM view_edges) AS edges_count
            """
        ).fetchone()

    assert counts["users_count"] >= 1
    assert counts["nodes_count"] >= 3
    assert counts["edges_count"] >= 1
