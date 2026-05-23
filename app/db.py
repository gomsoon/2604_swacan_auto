from __future__ import annotations

import sqlite3
from pathlib import Path
import re

import click
from flask import current_app, g

from .alert_identity import derive_alert_identity
from flask.cli import with_appcontext


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
        ensure_runtime_schema(g.db)

    return g.db


def close_db(_error: Exception | None = None) -> None:
    db_conn = g.pop("db", None)

    if db_conn is not None:
        db_conn.close()


def read_sql_file(filename: str) -> str:
    sql_path = get_project_root() / "db" / filename
    return sql_path.read_text(encoding="utf-8")


def init_db(include_seed: bool = False) -> None:
    db_conn = get_db()
    db_conn.executescript(read_sql_file("schema.sql"))
    ensure_runtime_schema(db_conn)

    if include_seed:
        db_conn.executescript(read_sql_file("seed.sql"))

    db_conn.commit()


@click.command("init-db")
@click.option("--seed", "include_seed", is_flag=True, help="Load seed.sql after schema.sql.")
@with_appcontext
def init_db_command(include_seed: bool) -> None:
    init_db(include_seed=include_seed)
    click.echo("Initialized the database.")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


RULE_KEY_ALLOWED_PATTERN = re.compile(r"^[a-z0-9._-]+$")


def slugify_rule_key_part(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized


def suggest_threshold_rule_key(state_type: str, metric_key: str, display_name: str, *, rule_id: int | None = None) -> str:
    slug = slugify_rule_key_part(display_name) or (f"legacy-{rule_id}" if rule_id is not None else "rule")
    return f"threshold.{state_type}.{metric_key}.{slug}"


def suggest_event_rule_key(state_type: str, signal_key: str, display_name: str, *, rule_id: int | None = None) -> str:
    slug = slugify_rule_key_part(display_name) or (f"legacy-{rule_id}" if rule_id is not None else "rule")
    return f"event.{state_type}.{signal_key}.{slug}"


def suggest_alert_rule_display_name(description: str | None, state_type: str, metric_key: str, *, rule_id: int | None = None) -> str:
    description_value = (description or "").strip()
    if description_value:
        return description_value

    state_label = state_type.replace("_", " ").strip().title()
    metric_label = metric_key.replace("_", " ").strip().title()
    suffix = f" {rule_id}" if rule_id is not None else ""
    return f"Legacy {state_label} {metric_label} Threshold{suffix}".strip()


def _table_exists(db_conn: sqlite3.Connection, table_name: str) -> bool:
    row = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(db_conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = db_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row[1]) for row in rows}


def ensure_alert_rule_lifecycle_schema(db_conn: sqlite3.Connection) -> None:
    if not _table_exists(db_conn, "alert_rules"):
        return

    columns = _table_columns(db_conn, "alert_rules")
    if "rule_key" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN rule_key TEXT")
    if "display_name" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN display_name TEXT")
    if "status" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN status TEXT")
    if "signal_type" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN signal_type TEXT")
    if "signal_key" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN signal_key TEXT")
    if "cond_mode" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN cond_mode TEXT")
    if "warning_logical_op" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN warning_logical_op TEXT")
    if "warning_cl1_comp" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN warning_cl1_comp TEXT")
    if "warning_cl1_val" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN warning_cl1_val REAL")
    if "warning_cl2_comp" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN warning_cl2_comp TEXT")
    if "warning_cl2_val" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN warning_cl2_val REAL")
    if "critical_logical_op" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN critical_logical_op TEXT")
    if "critical_cl1_comp" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN critical_cl1_comp TEXT")
    if "critical_cl1_val" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN critical_cl1_val REAL")
    if "critical_cl2_comp" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN critical_cl2_comp TEXT")
    if "critical_cl2_val" not in columns:
        db_conn.execute("ALTER TABLE alert_rules ADD COLUMN critical_cl2_val REAL")

    rows = db_conn.execute(
        """
        SELECT id, state_type, metric_key, description, rule_key, display_name, status, signal_type, signal_key, cond_mode
        FROM alert_rules
        ORDER BY id ASC
        """
    ).fetchall()
    for row in rows:
        rule_key = row["rule_key"]
        display_name = row["display_name"]
        status = row["status"]

        normalized_display_name = display_name or suggest_alert_rule_display_name(
            row["description"], row["state_type"], row["metric_key"], rule_id=row["id"]
        )
        normalized_rule_key = rule_key or suggest_threshold_rule_key(
            row["state_type"], row["metric_key"], normalized_display_name, rule_id=row["id"]
        )
        if not RULE_KEY_ALLOWED_PATTERN.fullmatch(normalized_rule_key):
            normalized_rule_key = f"threshold.{row['state_type']}.{row['metric_key']}.legacy-{row['id']}"
        normalized_status = status or "published"
        normalized_signal_type = row["signal_type"] or "latest_state_metric"
        normalized_cond_mode = row["cond_mode"] or "scalar"
        db_conn.execute(
            """
            UPDATE alert_rules
            SET rule_key = ?, display_name = ?, status = ?, signal_type = ?, cond_mode = ?
            WHERE id = ?
            """,
            (
                normalized_rule_key,
                normalized_display_name,
                normalized_status,
                normalized_signal_type,
                normalized_cond_mode,
                row["id"],
            ),
        )

    db_conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_alert_rules_rule_key ON alert_rules(rule_key)"
    )
    db_conn.commit()


def ensure_alert_history_archive_schema(db_conn: sqlite3.Connection) -> None:
    if not _table_exists(db_conn, "alert_history_archive"):
        return

    columns = _table_columns(db_conn, "alert_history_archive")
    if "source_rule_key" not in columns:
        db_conn.execute("ALTER TABLE alert_history_archive ADD COLUMN source_rule_key TEXT")
    if "source_rule_display_name_snapshot" not in columns:
        db_conn.execute("ALTER TABLE alert_history_archive ADD COLUMN source_rule_display_name_snapshot TEXT")

    if _table_exists(db_conn, "alert_rules"):
        db_conn.execute(
            """
            UPDATE alert_history_archive
            SET source_rule_key = COALESCE(
                    source_rule_key,
                    (SELECT rule_key FROM alert_rules WHERE id = alert_history_archive.source_rule_id)
                ),
                source_rule_display_name_snapshot = COALESCE(
                    source_rule_display_name_snapshot,
                    (SELECT display_name FROM alert_rules WHERE id = alert_history_archive.source_rule_id)
                )
            WHERE source_rule_id IS NOT NULL
              AND (
                    source_rule_key IS NULL
                 OR source_rule_display_name_snapshot IS NULL
              )
            """
        )
    db_conn.commit()


def ensure_alert_identity_schema(db_conn: sqlite3.Connection) -> None:
    has_alert_rules = _table_exists(db_conn, "alert_rules")
    if _table_exists(db_conn, "alert_instances"):
        columns = _table_columns(db_conn, "alert_instances")
        if "identity_kind" not in columns:
            db_conn.execute(
                "ALTER TABLE alert_instances ADD COLUMN identity_kind TEXT NOT NULL DEFAULT 'rule'"
            )
        if "identity_key" not in columns:
            db_conn.execute("ALTER TABLE alert_instances ADD COLUMN identity_key TEXT")
        if {"monitored_object_id", "identity_kind", "identity_key", "status"} <= _table_columns(
            db_conn, "alert_instances"
        ):
            db_conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_instances_identity_status "
                "ON alert_instances(monitored_object_id, identity_kind, identity_key, status)"
            )

        if has_alert_rules:
            rows = db_conn.execute(
                """
                SELECT alerts.id, alerts.monitored_object_id, alerts.alert_code, alerts.source_rule_id,
                       alerts.identity_kind, alerts.identity_key,
                       rules.signal_type, rules.state_type, rules.metric_key, rules.comparison
                FROM alert_instances AS alerts
                LEFT JOIN alert_rules AS rules ON rules.id = alerts.source_rule_id
                """
            ).fetchall()
        else:
            rows = db_conn.execute(
                """
                SELECT alerts.id, alerts.monitored_object_id, alerts.alert_code, alerts.source_rule_id,
                       alerts.identity_kind, alerts.identity_key,
                       NULL AS signal_type, NULL AS state_type, NULL AS metric_key, NULL AS comparison
                FROM alert_instances AS alerts
                """
            ).fetchall()
        for row in rows:
            identity_kind, identity_key = derive_alert_identity(
                monitored_object_id=row["monitored_object_id"],
                alert_code=row["alert_code"],
                source_rule_id=row["source_rule_id"],
                signal_type=row["signal_type"],
                state_type=row["state_type"],
                metric_key=row["metric_key"],
                comparison=row["comparison"],
            )
            if row["identity_kind"] != identity_kind or row["identity_key"] != identity_key:
                db_conn.execute(
                    """
                    UPDATE alert_instances
                    SET identity_kind = ?, identity_key = ?
                    WHERE id = ?
                    """,
                    (identity_kind, identity_key, row["id"]),
                )

    if _table_exists(db_conn, "alert_history_archive"):
        columns = _table_columns(db_conn, "alert_history_archive")
        if "identity_kind" not in columns:
            db_conn.execute("ALTER TABLE alert_history_archive ADD COLUMN identity_kind TEXT")
        if "identity_key" not in columns:
            db_conn.execute("ALTER TABLE alert_history_archive ADD COLUMN identity_key TEXT")

        if has_alert_rules:
            rows = db_conn.execute(
                """
                SELECT archive.id, archive.monitored_object_id, archive.alert_code, archive.source_rule_id,
                       archive.identity_kind, archive.identity_key,
                       rules.signal_type, rules.state_type, rules.metric_key, rules.comparison
                FROM alert_history_archive AS archive
                LEFT JOIN alert_rules AS rules ON rules.id = archive.source_rule_id
                """
            ).fetchall()
        else:
            rows = db_conn.execute(
                """
                SELECT archive.id, archive.monitored_object_id, archive.alert_code, archive.source_rule_id,
                       archive.identity_kind, archive.identity_key,
                       NULL AS signal_type, NULL AS state_type, NULL AS metric_key, NULL AS comparison
                FROM alert_history_archive AS archive
                """
            ).fetchall()
        for row in rows:
            identity_kind, identity_key = derive_alert_identity(
                monitored_object_id=row["monitored_object_id"],
                alert_code=row["alert_code"],
                source_rule_id=row["source_rule_id"],
                signal_type=row["signal_type"],
                state_type=row["state_type"],
                metric_key=row["metric_key"],
                comparison=row["comparison"],
            )
            if row["identity_kind"] != identity_kind or row["identity_key"] != identity_key:
                db_conn.execute(
                    """
                    UPDATE alert_history_archive
                    SET identity_kind = ?, identity_key = ?
                    WHERE id = ?
                    """,
                    (identity_kind, identity_key, row["id"]),
                )

    db_conn.commit()


def ensure_alert_winner_transition_schema(db_conn: sqlite3.Connection) -> None:
    has_alert_rules = _table_exists(db_conn, "alert_rules")

    if _table_exists(db_conn, "alert_instances"):
        columns = _table_columns(db_conn, "alert_instances")
        if "opening_rule_id" not in columns:
            db_conn.execute("ALTER TABLE alert_instances ADD COLUMN opening_rule_id INTEGER")
        if "opening_rule_key" not in columns:
            db_conn.execute("ALTER TABLE alert_instances ADD COLUMN opening_rule_key TEXT")
        if "opening_rule_display_name_snapshot" not in columns:
            db_conn.execute(
                "ALTER TABLE alert_instances ADD COLUMN opening_rule_display_name_snapshot TEXT"
            )
        if "winner_transition_count" not in columns:
            db_conn.execute(
                "ALTER TABLE alert_instances ADD COLUMN winner_transition_count INTEGER NOT NULL DEFAULT 0"
            )
        if "last_winner_transition_at" not in columns:
            db_conn.execute("ALTER TABLE alert_instances ADD COLUMN last_winner_transition_at TEXT")

        db_conn.execute(
            """
            UPDATE alert_instances
            SET opening_rule_id = COALESCE(opening_rule_id, source_rule_id),
                winner_transition_count = COALESCE(winner_transition_count, 0)
            """
        )
        if has_alert_rules:
            db_conn.execute(
                """
                UPDATE alert_instances
                SET opening_rule_key = COALESCE(
                        opening_rule_key,
                        (SELECT rule_key FROM alert_rules WHERE id = alert_instances.source_rule_id)
                    ),
                    opening_rule_display_name_snapshot = COALESCE(
                        opening_rule_display_name_snapshot,
                        (SELECT display_name FROM alert_rules WHERE id = alert_instances.source_rule_id)
                    )
                WHERE source_rule_id IS NOT NULL
                  AND (
                        opening_rule_key IS NULL
                     OR opening_rule_display_name_snapshot IS NULL
                  )
                """
            )

        db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_winner_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_instance_id INTEGER NOT NULL,
                identity_kind TEXT NOT NULL,
                identity_key TEXT NOT NULL,
                monitored_object_id INTEGER NOT NULL,
                previous_rule_id INTEGER,
                previous_rule_key TEXT,
                previous_rule_display_name_snapshot TEXT,
                previous_severity TEXT,
                new_rule_id INTEGER,
                new_rule_key TEXT,
                new_rule_display_name_snapshot TEXT,
                new_severity TEXT,
                transition_reason TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata_json TEXT,
                FOREIGN KEY (alert_instance_id) REFERENCES alert_instances(id) ON DELETE CASCADE
            )
            """
        )
        db_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_winner_transitions_instance_time "
            "ON alert_winner_transitions(alert_instance_id, occurred_at)"
        )
        db_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_winner_transitions_identity_time "
            "ON alert_winner_transitions(monitored_object_id, identity_kind, identity_key, occurred_at)"
        )

    if _table_exists(db_conn, "alert_history_archive"):
        columns = _table_columns(db_conn, "alert_history_archive")
        if "opening_rule_id" not in columns:
            db_conn.execute("ALTER TABLE alert_history_archive ADD COLUMN opening_rule_id INTEGER")
        if "opening_rule_key" not in columns:
            db_conn.execute("ALTER TABLE alert_history_archive ADD COLUMN opening_rule_key TEXT")
        if "opening_rule_display_name_snapshot" not in columns:
            db_conn.execute(
                "ALTER TABLE alert_history_archive ADD COLUMN opening_rule_display_name_snapshot TEXT"
            )
        if "origin_alert_instance_id" not in columns:
            db_conn.execute("ALTER TABLE alert_history_archive ADD COLUMN origin_alert_instance_id INTEGER")
        if "winner_transition_count" not in columns:
            db_conn.execute(
                "ALTER TABLE alert_history_archive ADD COLUMN winner_transition_count INTEGER NOT NULL DEFAULT 0"
            )
        if "last_winner_transition_at" not in columns:
            db_conn.execute("ALTER TABLE alert_history_archive ADD COLUMN last_winner_transition_at TEXT")

        db_conn.execute(
            """
            UPDATE alert_history_archive
            SET opening_rule_id = COALESCE(opening_rule_id, source_rule_id),
                winner_transition_count = COALESCE(winner_transition_count, 0)
            """
        )
        if has_alert_rules:
            db_conn.execute(
                """
                UPDATE alert_history_archive
                SET opening_rule_key = COALESCE(
                        opening_rule_key,
                        source_rule_key,
                        (SELECT rule_key FROM alert_rules WHERE id = alert_history_archive.source_rule_id)
                    ),
                    opening_rule_display_name_snapshot = COALESCE(
                        opening_rule_display_name_snapshot,
                        source_rule_display_name_snapshot,
                        (SELECT display_name FROM alert_rules WHERE id = alert_history_archive.source_rule_id)
                    )
                WHERE source_rule_id IS NOT NULL
                  AND (
                        opening_rule_key IS NULL
                     OR opening_rule_display_name_snapshot IS NULL
                  )
                """
            )
        else:
            db_conn.execute(
                """
                UPDATE alert_history_archive
                SET opening_rule_key = COALESCE(opening_rule_key, source_rule_key),
                    opening_rule_display_name_snapshot = COALESCE(
                        opening_rule_display_name_snapshot,
                        source_rule_display_name_snapshot
                    )
                """
            )

    db_conn.commit()


def ensure_runtime_schema(db_conn: sqlite3.Connection) -> None:
    ensure_alert_rule_lifecycle_schema(db_conn)
    ensure_alert_history_archive_schema(db_conn)
    ensure_alert_identity_schema(db_conn)
    ensure_alert_winner_transition_schema(db_conn)
