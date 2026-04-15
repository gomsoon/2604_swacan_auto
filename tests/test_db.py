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
        view_version_row = db_conn.execute(
            """
            SELECT id, view_id, status, version_code
            FROM view_versions
            WHERE id = 1001
            """
        ).fetchone()
        version_node_rows = db_conn.execute(
            """
            SELECT id, element_key, node_type
            FROM view_version_nodes
            WHERE view_version_id = 1001
            ORDER BY id
            """
        ).fetchall()
        version_edge_row = db_conn.execute(
            """
            SELECT edge_type, association_code, source_node_id, target_node_id
            FROM view_version_edges
            WHERE id = 1201
            """
        ).fetchone()
        node_rows = db_conn.execute(
            "SELECT id, node_type, display_name FROM view_nodes ORDER BY id"
        ).fetchall()
        edge_row = db_conn.execute(
            "SELECT edge_type, source_node_id, target_node_id FROM view_edges WHERE id = 201"
        ).fetchone()

    assert user_row["username"] == "admin"
    assert user_row["role"] == "admin"
    assert view_version_row["view_id"] == 1
    assert view_version_row["status"] == "active"
    assert view_version_row["version_code"] == "v1-active"
    assert [row["element_key"] for row in version_node_rows] == [
        "server_host_a",
        "process_app_main",
        "agent_local_main",
    ]
    assert version_edge_row["edge_type"] == "CommunicationLink"
    assert version_edge_row["association_code"] == "communicates_with"
    assert version_edge_row["source_node_id"] == 1102
    assert version_edge_row["target_node_id"] == 1103
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
                (SELECT COUNT(*) FROM view_versions) AS versions_count,
                (SELECT COUNT(*) FROM view_version_nodes) AS version_nodes_count,
                (SELECT COUNT(*) FROM view_version_edges) AS version_edges_count,
                (SELECT COUNT(*) FROM view_nodes) AS nodes_count,
                (SELECT COUNT(*) FROM view_edges) AS edges_count
            """
        ).fetchone()

    assert counts["users_count"] >= 1
    assert counts["versions_count"] >= 1
    assert counts["version_nodes_count"] >= 3
    assert counts["version_edges_count"] >= 1
    assert counts["nodes_count"] >= 3
    assert counts["edges_count"] >= 1
