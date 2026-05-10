from __future__ import annotations

import sqlite3
from pathlib import Path
import re

import click
from flask import current_app, g
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
        SELECT id, state_type, metric_key, description, rule_key, display_name, status, cond_mode
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
        normalized_cond_mode = row["cond_mode"] or "scalar"
        db_conn.execute(
            """
            UPDATE alert_rules
            SET rule_key = ?, display_name = ?, status = ?, cond_mode = ?
            WHERE id = ?
            """,
            (normalized_rule_key, normalized_display_name, normalized_status, normalized_cond_mode, row["id"]),
        )

    db_conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_alert_rules_rule_key ON alert_rules(rule_key)"
    )
    db_conn.commit()


def ensure_runtime_schema(db_conn: sqlite3.Connection) -> None:
    ensure_alert_rule_lifecycle_schema(db_conn)
