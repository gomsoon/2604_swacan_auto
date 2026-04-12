from __future__ import annotations

import sqlite3
from pathlib import Path

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
