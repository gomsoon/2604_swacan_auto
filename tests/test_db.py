from __future__ import annotations

import sqlite3

from app.db import (
    ensure_alert_rule_lifecycle_schema,
    ensure_alert_history_archive_schema,
    get_db,
    slugify_rule_key_part,
    suggest_alert_rule_display_name,
    suggest_event_rule_key,
    suggest_threshold_rule_key,
)


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
        monitored_object_rows = db_conn.execute(
            """
            SELECT id, object_key, runtime_binding_key
            FROM monitored_objects
            ORDER BY id
            """
        ).fetchall()
        node_binding_rows = db_conn.execute(
            """
            SELECT view_version_node_id, monitored_object_id, binding_role
            FROM node_bindings
            ORDER BY id
            """
        ).fetchall()
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
    assert version_edge_row["association_code"] == "monitors"
    assert version_edge_row["source_node_id"] == 1103
    assert version_edge_row["target_node_id"] == 1102
    assert [row["object_key"] for row in monitored_object_rows] == [
        "host.host-a",
        "process.app-main",
        "agent.local-main",
        "host.agent-local",
    ]
    assert [row["runtime_binding_key"] for row in monitored_object_rows] == [
        None,
        "app_main",
        "agent_local",
        "agent_local:host",
    ]
    assert [(row["view_version_node_id"], row["monitored_object_id"], row["binding_role"]) for row in node_binding_rows] == [
        (1101, 1301, "primary"),
        (1102, 1302, "primary"),
        (1103, 1303, "primary"),
    ]
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
                (SELECT COUNT(*) FROM monitored_objects) AS monitored_objects_count,
                (SELECT COUNT(*) FROM node_bindings) AS node_bindings_count,
                (SELECT COUNT(*) FROM view_nodes) AS nodes_count,
                (SELECT COUNT(*) FROM view_edges) AS edges_count
            """
        ).fetchone()

    assert counts["users_count"] >= 1
    assert counts["versions_count"] >= 1
    assert counts["version_nodes_count"] >= 3
    assert counts["version_edges_count"] >= 1
    assert counts["monitored_objects_count"] >= 4
    assert counts["node_bindings_count"] >= 3
    assert counts["nodes_count"] >= 3
    assert counts["edges_count"] >= 1


def test_rule_key_helpers_normalize_values() -> None:
    assert slugify_rule_key_part(" Process CPU High ") == "process-cpu-high"
    assert slugify_rule_key_part("CPU__High!!!") == "cpu-high"
    assert suggest_threshold_rule_key("process", "cpu_usage", "Process CPU High") == (
        "threshold.process.cpu_usage.process-cpu-high"
    )
    assert suggest_threshold_rule_key("process", "cpu_usage", "", rule_id=7) == (
        "threshold.process.cpu_usage.legacy-7"
    )
    assert suggest_event_rule_key("process", "process_restarted", "Process Restart Burst") == (
        "event.process.process_restarted.process-restart-burst"
    )
    assert suggest_alert_rule_display_name(" Explicit Name ", "process", "cpu_usage") == "Explicit Name"
    assert suggest_alert_rule_display_name(None, "process_group", "cpu_usage", rule_id=7) == (
        "Legacy Process Group Cpu Usage Threshold 7"
    )


def test_ensure_alert_rule_lifecycle_schema_returns_when_table_is_missing() -> None:
    db_conn = sqlite3.connect(":memory:")

    ensure_alert_rule_lifecycle_schema(db_conn)

    row = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'idx_alert_rules_rule_key'"
    ).fetchone()
    assert row is None


def test_ensure_alert_rule_lifecycle_schema_adds_columns_and_backfills_existing_rows() -> None:
    db_conn = sqlite3.connect(":memory:")
    db_conn.row_factory = sqlite3.Row
    db_conn.execute(
        """
        CREATE TABLE alert_rules (
            id INTEGER PRIMARY KEY,
            state_type TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            description TEXT
        )
        """
    )
    db_conn.execute(
        """
        INSERT INTO alert_rules (id, state_type, metric_key, description)
        VALUES (1, 'process', 'cpu_usage', 'Process CPU High')
        """
    )

    ensure_alert_rule_lifecycle_schema(db_conn)

    columns = {row["name"] for row in db_conn.execute("PRAGMA table_info(alert_rules)").fetchall()}
    row = db_conn.execute(
        """
        SELECT rule_key, display_name, status, signal_type, signal_key, cond_mode,
               warning_logical_op, warning_cl1_comp, warning_cl1_val,
               warning_cl2_comp, warning_cl2_val,
               critical_logical_op, critical_cl1_comp, critical_cl1_val,
               critical_cl2_comp, critical_cl2_val
        FROM alert_rules
        WHERE id = 1
        """
    ).fetchone()

    assert {
        "rule_key",
        "display_name",
        "status",
        "signal_type",
        "signal_key",
        "cond_mode",
        "warning_logical_op",
        "warning_cl1_comp",
        "warning_cl1_val",
        "warning_cl2_comp",
        "warning_cl2_val",
        "critical_logical_op",
        "critical_cl1_comp",
        "critical_cl1_val",
        "critical_cl2_comp",
        "critical_cl2_val",
    } <= columns
    assert row["rule_key"] == "threshold.process.cpu_usage.process-cpu-high"
    assert row["display_name"] == "Process CPU High"
    assert row["status"] == "published"
    assert row["signal_type"] == "latest_state_metric"
    assert row["signal_key"] is None
    assert row["cond_mode"] == "scalar"
    assert row["warning_logical_op"] is None
    assert row["warning_cl1_comp"] is None
    assert row["warning_cl1_val"] is None
    assert row["warning_cl2_comp"] is None
    assert row["warning_cl2_val"] is None
    assert row["critical_logical_op"] is None
    assert row["critical_cl1_comp"] is None
    assert row["critical_cl1_val"] is None
    assert row["critical_cl2_comp"] is None
    assert row["critical_cl2_val"] is None


def test_ensure_alert_rule_lifecycle_schema_rewrites_invalid_rule_key_to_legacy_key() -> None:
    db_conn = sqlite3.connect(":memory:")
    db_conn.row_factory = sqlite3.Row
    db_conn.execute(
        """
            CREATE TABLE alert_rules (
                id INTEGER PRIMARY KEY,
                state_type TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                description TEXT,
                rule_key TEXT,
                display_name TEXT,
                status TEXT,
                signal_type TEXT,
                cond_mode TEXT
            )
        """
    )
    db_conn.execute(
        """
        INSERT INTO alert_rules (id, state_type, metric_key, description, rule_key, display_name, status)
        VALUES (2, 'agent', 'outbox_queue_depth', NULL, 'INVALID KEY', NULL, NULL)
        """
    )

    ensure_alert_rule_lifecycle_schema(db_conn)

    row = db_conn.execute(
        "SELECT rule_key, display_name, status, signal_type, cond_mode FROM alert_rules WHERE id = 2"
    ).fetchone()

    assert row["rule_key"] == "threshold.agent.outbox_queue_depth.legacy-2"
    assert row["display_name"] == "Legacy Agent Outbox Queue Depth Threshold 2"
    assert row["status"] == "published"
    assert row["signal_type"] == "latest_state_metric"
    assert row["cond_mode"] == "scalar"


def test_ensure_alert_history_archive_schema_adds_snapshot_columns_and_backfills() -> None:
    db_conn = sqlite3.connect(":memory:")
    db_conn.row_factory = sqlite3.Row
    db_conn.execute(
        """
        CREATE TABLE alert_rules (
            id INTEGER PRIMARY KEY,
            rule_key TEXT,
            display_name TEXT
        )
        """
    )
    db_conn.execute(
        """
        CREATE TABLE alert_history_archive (
            id INTEGER PRIMARY KEY,
            source_rule_id INTEGER,
            resolution_source TEXT,
            resolution_reason TEXT
        )
        """
    )
    db_conn.execute(
        "INSERT INTO alert_rules (id, rule_key, display_name) VALUES (1501, 'threshold.process.cpu_usage.process-cpu-high', 'Process CPU High')"
    )
    db_conn.execute(
        "INSERT INTO alert_history_archive (id, source_rule_id, resolution_source, resolution_reason) VALUES (1, 1501, 'manual_operator', 'resolved')"
    )

    ensure_alert_history_archive_schema(db_conn)

    columns = {row["name"] for row in db_conn.execute("PRAGMA table_info(alert_history_archive)").fetchall()}
    row = db_conn.execute(
        "SELECT source_rule_key, source_rule_display_name_snapshot FROM alert_history_archive WHERE id = 1"
    ).fetchone()

    assert {"source_rule_key", "source_rule_display_name_snapshot"} <= columns
    assert row["source_rule_key"] == "threshold.process.cpu_usage.process-cpu-high"
    assert row["source_rule_display_name_snapshot"] == "Process CPU High"
