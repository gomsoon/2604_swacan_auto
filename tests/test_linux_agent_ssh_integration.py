from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.mark.linux_agent_ssh
def test_linux_agent_ssh_smoke(linux_agent_ssh_session, tmp_path: Path) -> None:
    run = linux_agent_ssh_session.create_run(run_id=f"ssh-smoke-{uuid4().hex[:8]}")
    config_text = linux_agent_ssh_session.render_agent_config(
        run,
        agent_id="agent_ssh_smoke",
        target_id="ssh_smoke_target",
        process_name="sleep",
    )

    try:
        linux_agent_ssh_session.prepare_agent_run(run, config_text=config_text)
        linux_agent_ssh_session.start_agent(run, cycles=20)
        time.sleep(2.0)
    finally:
        linux_agent_ssh_session.stop_agent(run)

    artifacts = linux_agent_ssh_session.collect_artifacts(run, tmp_path / "artifacts")
    linux_agent_ssh_session.cleanup_remote(run)

    assert (tmp_path / "artifacts" / "agent.toml") in artifacts
