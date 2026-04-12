from pathlib import Path

from flask import Flask

from . import auth, db, views_api


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    default_db_path = Path(app.instance_path) / "swacan.sqlite3"
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=str(default_db_path),
        TESTING=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    auth.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(views_api.bp)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
