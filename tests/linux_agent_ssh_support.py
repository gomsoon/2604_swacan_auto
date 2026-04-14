from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import uuid4

import paramiko


class LinuxAgentSshConfigError(ValueError):
    pass


@dataclass(frozen=True)
class LinuxAgentSshConfig:
    host: str
    user: str
    port: int
    password: str
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
            "LINUX_AGENT_SSH_PASSWORD": env.get("LINUX_AGENT_SSH_PASSWORD", ""),
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
            password=required["LINUX_AGENT_SSH_PASSWORD"],
            remote_work_base_dir=env.get(
                "LINUX_AGENT_REMOTE_WORK_BASE_DIR",
                "/tmp/swacan_agent_tests",
            ).strip()
            or "/tmp/swacan_agent_tests",
            remote_python=env.get("LINUX_AGENT_REMOTE_PYTHON", "auto").strip() or "auto",
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
        runner: Runner | None = None,
    ) -> None:
        self.config = config
        self.runner = runner
        self.local_agent_dir = Path(__file__).resolve().parent.parent / "agent"
        self._resolved_remote_python: str | None = None

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
        if self.runner is not None:
            return self.runner(self.build_ssh_command(remote_command), check=check)
        with self._connect_client() as client:
            stdin, stdout, stderr = client.exec_command(remote_command)
            exit_status = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode("utf-8", errors="replace")
            stderr_text = stderr.read().decode("utf-8", errors="replace")
        result = subprocess.CompletedProcess(
            self.build_ssh_command(remote_command),
            exit_status,
            stdout=stdout_text,
            stderr=stderr_text,
        )
        if check and exit_status != 0:
            raise subprocess.CalledProcessError(exit_status, result.args, output=stdout_text, stderr=stderr_text)
        return result

    def run_scp_to(self, local_path: Path, remote_path: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        if self.runner is not None:
            return self.runner(self.build_scp_to_command(local_path, remote_path), check=check)
        with self._connect_client() as client:
            with client.open_sftp() as sftp:
                self._ensure_remote_parent_dir(client, remote_path)
                sftp.put(str(local_path), remote_path)
        return subprocess.CompletedProcess(self.build_scp_to_command(local_path, remote_path), 0, stdout="", stderr="")

    def run_scp_from(
        self,
        remote_path: str,
        local_path: Path,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if self.runner is not None:
            return self.runner(self.build_scp_from_command(remote_path, local_path), check=check)
        try:
            with self._connect_client() as client:
                with client.open_sftp() as sftp:
                    sftp.get(remote_path, str(local_path))
        except Exception as exc:
            result = subprocess.CompletedProcess(
                self.build_scp_from_command(remote_path, local_path),
                1,
                stdout="",
                stderr=str(exc),
            )
            if check:
                raise
            return result
        return subprocess.CompletedProcess(self.build_scp_from_command(remote_path, local_path), 0, stdout="", stderr="")

    def _connect_client(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.user,
            password=self.config.password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
        return client

    def _ensure_remote_parent_dir(self, client: paramiko.SSHClient, remote_path: str) -> None:
        parent_dir = str(Path(remote_path).parent).replace("\\", "/")
        client.exec_command(f"mkdir -p {_quote(parent_dir)}")

    def resolve_remote_python(self) -> str:
        if self._resolved_remote_python is not None:
            return self._resolved_remote_python

        configured = self.config.remote_python.strip()
        if configured and configured.lower() != "auto":
            self._resolved_remote_python = configured
            return configured

        candidates = [
            "/usr/bin/python3.12",
            "/usr/bin/python3.11",
            "python3.12",
            "python3.11",
            "python3.10",
            "python3.9",
            "python3.8",
        ]
        for candidate in candidates:
            result = self.run_ssh(
                f"command -v {_quote(candidate)} >/dev/null 2>&1 && echo {_quote(candidate)}",
                check=False,
            )
            resolved = result.stdout.strip()
            if resolved:
                self._resolved_remote_python = resolved
                return resolved

        raise LinuxAgentSshConfigError(
            "supported remote python not found; set LINUX_AGENT_REMOTE_PYTHON to python 3.11+"
        )

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
        heartbeat_seconds: int = 2,
        snapshot_seconds: int = 2,
        flush_seconds: int = 2,
        retry_backoff_seconds: int = 5,
        backend_endpoint: str | None = None,
    ) -> str:
        return "\n".join(
            [
                "[agent]",
                f'agent_id = "{agent_id}"',
                f'token = "{token}"',
                "",
                "[backend]",
                f'endpoint = "{backend_endpoint or self.config.backend_endpoint}"',
                "",
                "[storage]",
                f'database_path = "{run.storage_path}"',
                "keep_acked_rows = 50",
                "cleanup_batch_size = 25",
                "pending_warning_rows = 100",
                "",
                "[intervals]",
                f"heartbeat_seconds = {heartbeat_seconds}",
                f"snapshot_seconds = {snapshot_seconds}",
                f"flush_seconds = {flush_seconds}",
                f"retry_backoff_seconds = {retry_backoff_seconds}",
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
        self.upload_agent_source(run)
        self.upload_text(run.config_path, config_text, suffix=".toml")

    def upload_agent_source(self, run: LinuxAgentRemoteRun) -> None:
        remote_agent_dir = f"{run.remote_dir}/agent"
        self.ensure_remote_dir(run)
        if self.runner is not None:
            self.run_ssh(f"mkdir -p {_quote(remote_agent_dir)}")
            return
        with self._connect_client() as client:
            with client.open_sftp() as sftp:
                self._mkdir_p_sftp(sftp, remote_agent_dir)
                for local_path in sorted(self.local_agent_dir.rglob("*")):
                    if "__pycache__" in local_path.parts:
                        continue
                    relative = local_path.relative_to(self.local_agent_dir).as_posix()
                    remote_path = f"{remote_agent_dir}/{relative}" if relative else remote_agent_dir
                    if local_path.is_dir():
                        self._mkdir_p_sftp(sftp, remote_path)
                    else:
                        self._mkdir_p_sftp(sftp, str(Path(remote_path).parent).replace("\\", "/"))
                        sftp.put(str(local_path), remote_path)

    def _mkdir_p_sftp(self, sftp: paramiko.SFTPClient, remote_dir: str) -> None:
        parts = [part for part in remote_dir.split("/") if part]
        current = ""
        if remote_dir.startswith("/"):
            current = "/"
        for part in parts:
            current = f"{current.rstrip('/')}/{part}" if current else part
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)

    def start_agent(self, run: LinuxAgentRemoteRun, *, cycles: int | None = None) -> None:
        cycle_arg = f" --cycles {cycles}" if cycles is not None else ""
        remote_python = self.resolve_remote_python()
        remote_command = (
            f"mkdir -p {_quote(run.remote_dir)} && "
            f"cd {_quote(run.remote_dir)} && "
            f"nohup {_quote(remote_python)} -m agent --config {_quote(run.config_path)}"
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
