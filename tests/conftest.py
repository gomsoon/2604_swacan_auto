from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app import create_app
from app.db import init_db


ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "test_artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def _build_app(db_name: str, include_seed: bool):
    db_path = ARTIFACTS_DIR / db_name
    if db_path.exists():
        db_path.unlink()

    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(db_path),
        }
    )

    with app.app_context():
        init_db(include_seed=include_seed)

    return app, db_path


@pytest.fixture()
def app():
    app, db_path = _build_app(f"test_{uuid4().hex}.sqlite3", include_seed=False)
    try:
        yield app
    finally:
        if db_path.exists():
            db_path.unlink()


@pytest.fixture()
def seeded_app():
    app, db_path = _build_app(f"seeded_{uuid4().hex}.sqlite3", include_seed=True)
    try:
        yield app
    finally:
        if db_path.exists():
            db_path.unlink()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seeded_client(seeded_app):
    return seeded_app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def seeded_runner(seeded_app):
    return seeded_app.test_cli_runner()
