from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.config import AgentConfig, AgentIntervals, AgentTarget
from agent.main import main
from agent.runner import AgentRunner


def sample_config() -> AgentConfig:
    return AgentConfig(
        config_path=Path("agent.toml"),
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

    def emit_heartbeat(self, occurred_at: datetime) -> None:
        self.actions.append(("heartbeat", occurred_at.isoformat(timespec="milliseconds")))

    def collect_snapshots(self, occurred_at: datetime) -> None:
        self.actions.append(("snapshot", occurred_at.isoformat(timespec="milliseconds")))

    def flush_outbox(self, occurred_at: datetime) -> None:
        self.actions.append(("flush", occurred_at.isoformat(timespec="milliseconds")))


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

    exit_code = main(["--config", str(config_path), "--once"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "heartbeat" in output
    assert "snapshot" in output
    assert "flush" in output
