from __future__ import annotations

import runpy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import agent.main as agent_main
from agent.config import AgentConfig, AgentIntervals, AgentStoragePolicy, AgentTarget
from agent.runner import AgentRunner


def sample_config() -> AgentConfig:
    return AgentConfig(
        config_path=Path("agent.toml"),
        storage_path=Path("agent.agent.sqlite3"),
        storage=AgentStoragePolicy(
            keep_acked_rows=500,
            cleanup_batch_size=250,
            pending_warning_rows=1000,
        ),
        agent_id="agent_local",
        backend_endpoint="https://backend.example.com/api/agents/ingest",
        token="dev-agent-token",
        debug_mode=False,
        intervals=AgentIntervals(
            heartbeat_seconds=5,
            snapshot_seconds=10,
            flush_seconds=2,
            retry_backoff_seconds=15,
        ),
        targets=(
            AgentTarget(
                target_id="app_main",
                mode="single",
                process_name="python",
                command_line_regex=None,
                executable_path=None,
                pid=None,
            ),
        ),
    )


@dataclass
class SpyServices:
    actions: list[tuple[str, str]] = field(default_factory=list)
    flush_outcomes: list[str | None] = field(default_factory=list)
    last_cycle: object = field(default_factory=lambda: SimpleNamespace(flush_error=None))

    def emit_heartbeat(self, occurred_at: datetime) -> None:
        self.actions.append(("heartbeat", occurred_at.isoformat(timespec="milliseconds")))

    def collect_snapshots(self, occurred_at: datetime) -> None:
        self.actions.append(("snapshot", occurred_at.isoformat(timespec="milliseconds")))

    def flush_outbox(self, occurred_at: datetime) -> None:
        self.actions.append(("flush", occurred_at.isoformat(timespec="milliseconds")))
        flush_error = self.flush_outcomes.pop(0) if self.flush_outcomes else None
        self.last_cycle = SimpleNamespace(flush_error=flush_error)


class FakeClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


def test_runner_first_cycle_runs_all_due_tasks() -> None:
    started_at = datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc)
    services = SpyServices()
    runner = AgentRunner(sample_config(), services, clock=FakeClock(started_at))

    result = runner.run_cycle(now=started_at)

    assert result.ran_heartbeat is True
    assert result.ran_snapshot is True
    assert result.ran_flush is True
    assert result.sleep_seconds == 2.0
    assert [name for name, _occurred_at in services.actions] == ["heartbeat", "snapshot", "flush"]


def test_runner_respects_next_due_times() -> None:
    started_at = datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc)
    services = SpyServices()
    runner = AgentRunner(sample_config(), services, clock=FakeClock(started_at))

    runner.run_cycle(now=started_at)
    result = runner.run_cycle(now=started_at + timedelta(seconds=1))

    assert result.ran_heartbeat is False
    assert result.ran_snapshot is False
    assert result.ran_flush is False
    assert result.sleep_seconds == 1.0
    assert [name for name, _occurred_at in services.actions] == ["heartbeat", "snapshot", "flush"]


def test_runner_forever_uses_scheduler_intervals() -> None:
    started_at = datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc)
    fake_clock = FakeClock(started_at)
    services = SpyServices()
    runner = AgentRunner(sample_config(), services, clock=fake_clock)

    def fake_sleep(seconds: float) -> None:
        fake_clock.advance(seconds)

    cycles = runner.run_forever(max_cycles=3, sleep_func=fake_sleep)

    assert cycles == 3
    assert [name for name, _occurred_at in services.actions] == [
        "heartbeat",
        "snapshot",
        "flush",
        "flush",
        "flush",
    ]


def test_runner_applies_retry_backoff_after_flush_failure() -> None:
    started_at = datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc)
    services = SpyServices(flush_outcomes=["temporary backend failure"])
    runner = AgentRunner(sample_config(), services, clock=FakeClock(started_at))

    result = runner.run_cycle(now=started_at)

    assert result.ran_flush is True
    assert result.sleep_seconds == 5.0
    assert runner.schedule.next_flush_at == started_at + timedelta(seconds=15)


def test_runner_returns_to_normal_flush_interval_after_backoff_success() -> None:
    started_at = datetime(2026, 4, 13, 9, 0, 0, tzinfo=timezone.utc)
    services = SpyServices(flush_outcomes=["temporary backend failure", None])
    runner = AgentRunner(sample_config(), services, clock=FakeClock(started_at))

    first_result = runner.run_cycle(now=started_at)
    second_at = started_at + timedelta(seconds=15)
    second_result = runner.run_cycle(now=second_at)

    assert first_result.sleep_seconds == 5.0
    assert second_result.ran_flush is True
    assert runner.schedule.next_flush_at == second_at + timedelta(seconds=2)


def test_agent_main_once_runs_single_cycle(tmp_path, capsys) -> None:
    config_path = tmp_path / "agent.toml"
    config_path.write_text(
        "\n".join(
            [
                "[agent]",
                'agent_id = "agent_local"',
                'token = "dev-agent-token"',
                "",
                "[backend]",
                'endpoint = "https://backend.example.com/api/agents/ingest"',
                "",
                "[intervals]",
                "heartbeat_seconds = 5",
                "snapshot_seconds = 10",
                "flush_seconds = 2",
                "retry_backoff_seconds = 15",
                "",
                "[[targets]]",
                'target_id = "app_main"',
                'process_name = "python"',
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    class FakeRuntimeServices(SpyServices):
        pass

    exit_code = agent_main.main(
        ["--config", str(config_path), "--once"],
        services_factory=lambda _config: FakeRuntimeServices(),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "heartbeat" in output
    assert "snapshot" in output
    assert "flush" in output


def test_agent_main_dump_config_includes_storage_policy(tmp_path, capsys) -> None:
    config_path = tmp_path / "agent.toml"
    config_path.write_text(
        "\n".join(
            [
                "[agent]",
                'agent_id = "agent_local"',
                'token = "dev-agent-token"',
                "",
                "[backend]",
                'endpoint = "https://backend.example.com/api/agents/ingest"',
                "",
                "[storage]",
                'database_path = "runtime/agent.sqlite3"',
                "keep_acked_rows = 25",
                "",
                "[intervals]",
                "heartbeat_seconds = 5",
                "snapshot_seconds = 10",
                "flush_seconds = 2",
                "retry_backoff_seconds = 15",
                "",
                "[[targets]]",
                'target_id = "app_main"',
                'process_name = "python"',
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = agent_main.main(["--config", str(config_path), "--dump-config"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "storage_path=" in output
    assert "keep_acked_rows=25" in output


def test_build_runtime_services_initializes_storage(monkeypatch, tmp_path) -> None:
    initialized_paths: list[Path] = []
    received_runtime_config: list[AgentConfig] = []

    class FakeStorage:
        def __init__(self, storage_path: Path) -> None:
            self.storage_path = storage_path

        def initialize(self) -> None:
            initialized_paths.append(self.storage_path)

    class FakeRuntimeServices:
        def __init__(self, config: AgentConfig, storage: FakeStorage) -> None:
            received_runtime_config.append(config)
            self.storage = storage

    config = sample_config()
    config = AgentConfig(
        **{**config.__dict__, "storage_path": tmp_path / "agent.sqlite3"}
    )

    monkeypatch.setattr(agent_main, "AgentStorage", FakeStorage)
    monkeypatch.setattr(agent_main, "AgentRuntimeServices", FakeRuntimeServices)

    services = agent_main.build_runtime_services(config)

    assert initialized_paths == [config.storage_path]
    assert received_runtime_config == [config]
    assert services.storage.storage_path == config.storage_path


def test_print_service_summary_returns_without_output_when_last_cycle_is_missing(capsys) -> None:
    services = SimpleNamespace(actions=None, last_cycle=None)

    agent_main.print_service_summary(services)

    assert capsys.readouterr().out == ""


def test_print_service_summary_formats_last_cycle_fallback(capsys) -> None:
    last_cycle = SimpleNamespace(
        heartbeat_seq=10,
        host_snapshot_seq=20,
        process_snapshot_seqs=[100, 101],
        process_event_seqs=[201],
        flush_sent_count=3,
        flush_ack_seq=88,
        purged_acked_count=5,
        flush_error=None,
    )
    services = SimpleNamespace(actions=None, last_cycle=last_cycle, backend_connection_status="ok")

    agent_main.print_service_summary(services)
    output = capsys.readouterr().out

    assert "heartbeat_seq=10" in output
    assert "process_snapshot_count=2" in output
    assert "process_event_count=1" in output
    assert "backend_status=ok" in output
    assert "flush_error=-" in output


def test_agent_main_cycles_runs_runner_forever(tmp_path) -> None:
    config_path = tmp_path / "agent.toml"
    config_path.write_text(
        "\n".join(
            [
                "[agent]",
                'agent_id = "agent_local"',
                'token = "dev-agent-token"',
                "",
                "[backend]",
                'endpoint = "https://backend.example.com/api/agents/ingest"',
                "",
                "[intervals]",
                "heartbeat_seconds = 5",
                "snapshot_seconds = 10",
                "flush_seconds = 2",
                "retry_backoff_seconds = 15",
                "",
                "[[targets]]",
                'target_id = "app_main"',
                'process_name = "python"',
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    called: dict[str, object] = {}

    class FakeRunner:
        def __init__(self, config: AgentConfig, services: object) -> None:
            called["config"] = config
            called["services"] = services

        def run_cycle(self) -> None:
            raise AssertionError("run_cycle should not be called when --cycles is used")

        def run_forever(self, *, max_cycles: int) -> int:
            called["max_cycles"] = max_cycles
            return max_cycles

    fake_services = SimpleNamespace(actions=[("flush", "2026-04-13T09:00:00+00:00")])

    original_runner = agent_main.AgentRunner
    agent_main.AgentRunner = FakeRunner
    try:
        exit_code = agent_main.main(
            ["--config", str(config_path), "--cycles", "3"],
            services_factory=lambda _config: fake_services,
        )
    finally:
        agent_main.AgentRunner = original_runner

    assert exit_code == 0
    assert called["services"] is fake_services
    assert called["max_cycles"] == 3


def test_agent_main_exits_with_parser_error_on_invalid_config(tmp_path, capsys) -> None:
    config_path = tmp_path / "agent.toml"
    config_path.write_text(
        "\n".join(
            [
                "[agent]",
                'agent_id = "agent_local"',
                'token = "dev-agent-token"',
                "",
                "[backend]",
                'endpoint = "https://backend.example.com/api/agents/ingest"',
                "",
                "[intervals]",
                "heartbeat_seconds = 0",
                "snapshot_seconds = 10",
                "flush_seconds = 2",
                "retry_backoff_seconds = 15",
                "",
                "[[targets]]",
                'target_id = "app_main"',
                'process_name = "python"',
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as excinfo:
        agent_main.main(["--config", str(config_path)])

    assert excinfo.value.code == 2
    assert "config error:" in capsys.readouterr().err


def test_agent_dunder_main_delegates_to_main(monkeypatch) -> None:
    def fake_main() -> int:
        return 7

    monkeypatch.setattr(agent_main, "main", fake_main)

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("agent.__main__", run_name="__main__")

    assert excinfo.value.code == 7
