from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

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
