from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

import pytest

from app.db import get_db
from app.ingest_worker import process_pending_ingest


@pytest.mark.linux_agent_ssh
def test_linux_agent_ssh_smoke(linux_agent_ssh_session, network_live_server, tmp_path: Path) -> None:
    run = linux_agent_ssh_session.create_run(run_id=f"ssh-smoke-{uuid4().hex[:8]}")

    with network_live_server(
        linux_agent_ssh_session.config.host,
        app_config={
            "AGENT_TOKENS": {
                "agent_local": "dev-agent-token",
                "agent_ssh_smoke": "dev-agent-token",
            }
        },
    ) as (endpoint, app, _db_path):
        config_text = linux_agent_ssh_session.render_agent_config(
            run,
            agent_id="agent_ssh_smoke",
            target_id="ssh_smoke_target",
            process_name="sleep",
            heartbeat_seconds=1,
            snapshot_seconds=1,
            flush_seconds=1,
            retry_backoff_seconds=2,
            backend_endpoint=f"{endpoint}/api/agents/ingest",
        )

        remote_sleep = linux_agent_ssh_session.run_ssh(
            "nohup sleep 30 >/dev/null 2>&1 & echo $!",
        )
        remote_sleep_pid = remote_sleep.stdout.strip()
        artifacts: list[Path] = []
        result = {"processed_batches": 0}
        latest_rows = []

        try:
            linux_agent_ssh_session.prepare_agent_run(run, config_text=config_text)
            linux_agent_ssh_session.start_agent(run, cycles=6)
            time.sleep(8.0)
            artifacts = linux_agent_ssh_session.collect_artifacts(run, tmp_path / "artifacts")

            with app.app_context():
                result = process_pending_ingest(limit=100)
                db_conn = get_db()
                latest_rows = db_conn.execute(
                    "SELECT target_id, state_type, status FROM latest_states ORDER BY id"
                ).fetchall()
        finally:
            linux_agent_ssh_session.stop_agent(run)
            if remote_sleep_pid:
                linux_agent_ssh_session.run_ssh(f"kill {remote_sleep_pid} 2>/dev/null || true", check=False)
            linux_agent_ssh_session.cleanup_remote(run)

    assert (tmp_path / "artifacts" / "agent.toml") in artifacts
    assert result["processed_batches"] >= 1
    assert ("agent_ssh_smoke", "agent", "up") in [
        (row["target_id"], row["state_type"], row["status"]) for row in latest_rows
    ]
    assert ("agent_ssh_smoke:host", "host", "up") in [
        (row["target_id"], row["state_type"], row["status"]) for row in latest_rows
    ]
    assert any(row["target_id"] == "ssh_smoke_target" for row in latest_rows)
