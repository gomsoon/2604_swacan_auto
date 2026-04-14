from __future__ import annotations

import socket
import threading
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from werkzeug.serving import make_server

from app import create_app
from app.db import init_db
from linux_agent_ssh_support import (
    LinuxAgentSshConfig,
    LinuxAgentSshConfigError,
    LinuxAgentSshSession,
)


ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "test_artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


class LiveServerThread(threading.Thread):
    def __init__(self, app, host: str, port: int):
        super().__init__(daemon=True)
        self._server = make_server(host, port, app, threaded=True)

    def run(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()


def _build_app(db_name: str, include_seed: bool, extra_config: dict | None = None):
    db_path = ARTIFACTS_DIR / db_name
    if db_path.exists():
        db_path.unlink()

    app_config = {
        "TESTING": True,
        "DATABASE": str(db_path),
    }
    if extra_config:
        app_config.update(extra_config)

    app = create_app(
        app_config
    )

    with app.app_context():
        init_db(include_seed=include_seed)

    return app, db_path


def _find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _detect_local_ip_for_remote(remote_host: str) -> str:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        sock.connect((remote_host, 1))
        return str(sock.getsockname()[0])


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


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture()
def browser_context(browser: Browser) -> BrowserContext:
    context = browser.new_context(locale="ko-KR", timezone_id="Asia/Seoul")
    try:
        yield context
    finally:
        context.close()


@pytest.fixture()
def page(browser_context: BrowserContext) -> Page:
    return browser_context.new_page()


@pytest.fixture()
def live_server(seeded_app):
    host = "127.0.0.1"
    port = _find_free_port()
    server_thread = LiveServerThread(seeded_app, host, port)
    server_thread.start()
    try:
        yield f"http://{host}:{port}", seeded_app
    finally:
        server_thread.shutdown()
        server_thread.join(timeout=5)


@pytest.fixture()
def network_live_server():
    @contextmanager
    def _start(remote_host: str, *, app_config: dict | None = None):
        app, db_path = _build_app(
            f"network_seeded_{uuid4().hex}.sqlite3",
            include_seed=True,
            extra_config=app_config,
        )
        host = "0.0.0.0"
        port = _find_free_port()
        server_thread = LiveServerThread(app, host, port)
        server_thread.start()
        endpoint_host = _detect_local_ip_for_remote(remote_host)

        try:
            yield f"http://{endpoint_host}:{port}", app, db_path
        finally:
            server_thread.shutdown()
            server_thread.join(timeout=5)
            if db_path.exists():
                db_path.unlink()

    return _start


@pytest.fixture()
def linux_agent_ssh_session():
    try:
        config = LinuxAgentSshConfig.from_env()
    except LinuxAgentSshConfigError as exc:
        pytest.skip(f"linux agent ssh test env not configured: {exc}")
    return LinuxAgentSshSession(config)
