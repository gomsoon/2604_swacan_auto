from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4


class LinuxAgentSshConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LinuxAgentSshConfig:
    host: str
    user: str
    port: int
    remote_repo_dir: str
    remote_work_base_dir: str
    remote_python: str
    backend_endpoint: str
    ssh_bin: str = "ssh"
    scp_bin: str = "scp"

    @property
    def ssh_target(self) -> str:
        return f"{self.user}@{self.host}"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> LinuxAgentSshConfig:
        env = os.environ if environ is None else environ
        required = {
            "LINUX_AGENT_SSH_HOST": env.get("LINUX_AGENT_SSH_HOST", "").strip(),
            "LINUX_AGENT_SSH_USER": env.get("LINUX_AGENT_SSH_USER", "").strip(),
            "LINUX_AGENT_REMOTE_REPO_DIR": env.get("LINUX_AGENT_REMOTE_REPO_DIR", "").strip(),
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise LinuxAgentSshConfigError(
                "missing required env: " + ", ".join(missing)
            )

        port_text = env.get("LINUX_AGENT_SSH_PORT", "22").strip()
        if not port_text.isdigit():
            raise LinuxAgentSshConfigError("LINUX_AGENT_SSH_PORT must be an integer")

        return cls(
            host=required["LINUX_AGENT_SSH_HOST"],
            user=required["LINUX_AGENT_SSH_USER"],
            port=int(port_text),
            remote_repo_dir=required["LINUX_AGENT_REMOTE_REPO_DIR"],
            remote_work_base_dir=env.get(
                "LINUX_AGENT_REMOTE_WORK_BASE_DIR",
                "/tmp/swacan_agent_tests",
            ).strip()
            or "/tmp/swacan_agent_tests",
            remote_python=env.get("LINUX_AGENT_REMOTE_PYTHON", "python3").strip() or "python3",
            backend_endpoint=env.get(
                "LINUX_AGENT_TEST_BACKEND_ENDPOINT",
                "http://127.0.0.1:9/api/agents/ingest",
            ).strip()
            or "http://127.0.0.1:9/api/agents/ingest",
        )


@dataclass(frozen=True)
class LinuxAgentRemoteRun:
    run_id: str
    remote_dir: str
    config_path: str
    storage_path: str
    stdout_path: str
    stderr_path: str
    pidfile_path: str


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _default_runner(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, capture_output=True, text=True)


def _quote(value: str) -> str:
    return shlex.quote(value)


class LinuxAgentSshSession:
    def __init__(
        self,
        config: LinuxAgentSshConfig,
        *,
        runner: Runner = _default_runner,
    ) -> None:
        self.config = config
        self.runner = runner

    def build_ssh_command(self, remote_command: str) -> list[str]:
        return [
            self.config.ssh_bin,
            "-p",
            str(self.config.port),
            "-o",
            "BatchMode=yes",
            self.config.ssh_target,
            remote_command,
        ]

    def build_scp_to_command(self, local_path: Path, remote_path: str) -> list[str]:
        return [
            self.config.scp_bin,
            "-P",
            str(self.config.port),
            "-o",
            "BatchMode=yes",
            str(local_path),
            f"{self.config.ssh_target}:{remote_path}",
        ]

    def build_scp_from_command(self, remote_path: str, local_path: Path) -> list[str]:
        return [
            self.config.scp_bin,
            "-P",
            str(self.config.port),
            "-o",
            "BatchMode=yes",
            f"{self.config.ssh_target}:{remote_path}",
            str(local_path),
        ]

    def run_ssh(self, remote_command: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.runner(self.build_ssh_command(remote_command), check=check)

    def run_scp_to(self, local_path: Path, remote_path: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self.runner(self.build_scp_to_command(local_path, remote_path), check=check)

    def run_scp_from(
        self,
        remote_path: str,
        local_path: Path,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return self.runner(self.build_scp_from_command(remote_path, local_path), check=check)

    def create_run(self, *, run_id: str | None = None) -> LinuxAgentRemoteRun:
        actual_run_id = run_id or f"linux-agent-{uuid4().hex[:12]}"
        remote_dir = f"{self.config.remote_work_base_dir.rstrip('/')}/{actual_run_id}"
        return LinuxAgentRemoteRun(
            run_id=actual_run_id,
            remote_dir=remote_dir,
            config_path=f"{remote_dir}/agent.toml",
            storage_path=f"{remote_dir}/agent.sqlite3",
            stdout_path=f"{remote_dir}/agent.stdout.log",
            stderr_path=f"{remote_dir}/agent.stderr.log",
            pidfile_path=f"{remote_dir}/agent.pid",
        )

    def render_agent_config(
        self,
        run: LinuxAgentRemoteRun,
        *,
        agent_id: str = "agent_ssh_test",
        token: str = "dev-agent-token",
        target_id: str = "dummy_target",
        process_name: str = "sleep",
    ) -> str:
        return "\n".join(
            [
                "[agent]",
                f'agent_id = "{agent_id}"',
                f'token = "{token}"',
                "",
                "[backend]",
                f'endpoint = "{self.config.backend_endpoint}"',
                "",
                "[storage]",
                f'database_path = "{run.storage_path}"',
                "keep_acked_rows = 50",
                "cleanup_batch_size = 25",
                "pending_warning_rows = 100",
                "",
                "[intervals]",
                "heartbeat_seconds = 5",
                "snapshot_seconds = 10",
                "flush_seconds = 30",
                "retry_backoff_seconds = 60",
                "",
                "[[targets]]",
                f'target_id = "{target_id}"',
                'mode = "multi"',
                f'process_name = "{process_name}"',
                "",
            ]
        ) + "\n"

    def ensure_remote_dir(self, run: LinuxAgentRemoteRun) -> None:
        self.run_ssh(f"mkdir -p {_quote(run.remote_dir)}")

    def upload_text(self, remote_path: str, content: str, *, suffix: str = ".txt") -> None:
        fd, temp_name = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            temp_path.write_text(content, encoding="utf-8")
            self.run_scp_to(temp_path, remote_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def prepare_agent_run(self, run: LinuxAgentRemoteRun, *, config_text: str) -> None:
        self.ensure_remote_dir(run)
        self.upload_text(run.config_path, config_text, suffix=".toml")

    def start_agent(self, run: LinuxAgentRemoteRun, *, cycles: int | None = None) -> None:
        cycle_arg = f" --cycles {cycles}" if cycles is not None else ""
        remote_command = (
            f"mkdir -p {_quote(run.remote_dir)} && "
            f"cd {_quote(self.config.remote_repo_dir)} && "
            f"nohup {_quote(self.config.remote_python)} -m agent --config {_quote(run.config_path)}"
            f"{cycle_arg} > {_quote(run.stdout_path)} 2> {_quote(run.stderr_path)} < /dev/null "
            f"& echo $! > {_quote(run.pidfile_path)}"
        )
        self.run_ssh(remote_command)

    def stop_agent(self, run: LinuxAgentRemoteRun) -> None:
        remote_command = (
            f"if [ -f {_quote(run.pidfile_path)} ]; then "
            f"pid=$(cat {_quote(run.pidfile_path)}); "
            "kill \"$pid\" 2>/dev/null || true; "
            "fi"
        )
        self.run_ssh(remote_command, check=False)

    def collect_artifacts(self, run: LinuxAgentRemoteRun, local_dir: Path) -> list[Path]:
        local_dir.mkdir(parents=True, exist_ok=True)
        collected: list[Path] = []
        for remote_path, local_name in [
            (run.config_path, "agent.toml"),
            (run.stdout_path, "agent.stdout.log"),
            (run.stderr_path, "agent.stderr.log"),
            (run.storage_path, "agent.sqlite3"),
        ]:
            local_path = local_dir / local_name
            result = self.run_scp_from(remote_path, local_path, check=False)
            if result.returncode == 0:
                collected.append(local_path)
        return collected

    def cleanup_remote(self, run: LinuxAgentRemoteRun) -> None:
        self.run_ssh(f"rm -rf {_quote(run.remote_dir)}", check=False)
