from __future__ import annotations

import subprocess
from pathlib import Path

from linux_agent_ssh_support import (
    LinuxAgentRemoteRun,
    LinuxAgentSshConfig,
    LinuxAgentSshConfigError,
    LinuxAgentSshSession,
)


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], bool]] = []

    def __call__(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        self.calls.append((args, check))

        command_text = " ".join(args)
        if "agent.stderr.log" in command_text:
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="missing")

        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


def test_linux_agent_ssh_config_reads_defaults_from_env() -> None:
    config = LinuxAgentSshConfig.from_env(
        {
            "LINUX_AGENT_SSH_HOST": "192.0.2.10",
            "LINUX_AGENT_SSH_USER": "tester",
            "LINUX_AGENT_REMOTE_REPO_DIR": "/opt/swacan",
        }
    )

    assert config.host == "192.0.2.10"
    assert config.user == "tester"
    assert config.port == 22
    assert config.remote_work_base_dir == "/tmp/swacan_agent_tests"
    assert config.remote_python == "python3"
    assert config.backend_endpoint == "http://127.0.0.1:9/api/agents/ingest"


def test_linux_agent_ssh_config_requires_mandatory_env_values() -> None:
    try:
        LinuxAgentSshConfig.from_env({})
    except LinuxAgentSshConfigError as exc:
        assert "LINUX_AGENT_SSH_HOST" in str(exc)
        return

    raise AssertionError("expected LinuxAgentSshConfigError")


def test_linux_agent_ssh_session_prepare_start_stop_and_collect(tmp_path: Path) -> None:
    config = LinuxAgentSshConfig(
        host="192.0.2.10",
        user="tester",
        port=22,
        remote_repo_dir="/opt/swacan",
        remote_work_base_dir="/tmp/swacan_agent_tests",
        remote_python="python3",
        backend_endpoint="http://127.0.0.1:9/api/agents/ingest",
    )
    runner = FakeRunner()
    session = LinuxAgentSshSession(config, runner=runner)
    run = session.create_run(run_id="ssh-run-001")
    config_text = session.render_agent_config(run, process_name="httpd", target_id="apache_group")

    session.prepare_agent_run(run, config_text=config_text)
    session.start_agent(run, cycles=20)
    session.stop_agent(run)
    artifacts = session.collect_artifacts(run, tmp_path / "artifacts")
    session.cleanup_remote(run)

    assert run == LinuxAgentRemoteRun(
        run_id="ssh-run-001",
        remote_dir="/tmp/swacan_agent_tests/ssh-run-001",
        config_path="/tmp/swacan_agent_tests/ssh-run-001/agent.toml",
        storage_path="/tmp/swacan_agent_tests/ssh-run-001/agent.sqlite3",
        stdout_path="/tmp/swacan_agent_tests/ssh-run-001/agent.stdout.log",
        stderr_path="/tmp/swacan_agent_tests/ssh-run-001/agent.stderr.log",
        pidfile_path="/tmp/swacan_agent_tests/ssh-run-001/agent.pid",
    )
    assert "process_name = \"httpd\"" in config_text
    assert "target_id = \"apache_group\"" in config_text
    assert any("mkdir -p" in " ".join(call[0]) for call in runner.calls)
    assert any("nohup" in " ".join(call[0]) for call in runner.calls)
    assert any("kill" in " ".join(call[0]) for call in runner.calls)
    assert any("rm -rf" in " ".join(call[0]) for call in runner.calls)
    assert (tmp_path / "artifacts" / "agent.toml") in artifacts
