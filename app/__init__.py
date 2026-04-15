from pathlib import Path

from flask import Flask

from . import (
    admin_api,
    admin_metamodel_api,
    agent_api,
    auth,
    db,
    editor_api,
    ingest_worker,
    metamodel_api,
    view_versions_api,
    view_version_editor_api,
    views_api,
    web,
)


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    default_db_path = Path(app.instance_path) / "swacan.sqlite3"
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=str(default_db_path),
        TESTING=False,
        AGENT_TOKENS={"agent_local": "dev-agent-token"},
        DEBUG_PAYLOAD_LOGGING=False,
        AGENT_HEARTBEAT_WARNING_SECONDS=15,
        AGENT_HEARTBEAT_DOWN_SECONDS=30,
        RAW_EVENT_RETENTION_DAYS=7,
        DEBUG_PAYLOAD_RETENTION_HOURS=24,
        INGEST_INBOX_RETENTION_DAYS=7,
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    auth.init_app(app)
    ingest_worker.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(web.bp)
    app.register_blueprint(metamodel_api.bp)
    app.register_blueprint(admin_metamodel_api.bp)
    app.register_blueprint(views_api.bp)
    app.register_blueprint(view_versions_api.bp)
    app.register_blueprint(view_version_editor_api.bp)
    app.register_blueprint(editor_api.bp)
    app.register_blueprint(agent_api.bp)
    app.register_blueprint(admin_api.bp)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
