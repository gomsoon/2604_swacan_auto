from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from time import sleep
from typing import Protocol

from .config import AgentConfig, AgentIntervals


class Clock(Protocol):
    def now(self) -> datetime:
        ...


class RunnerServices(Protocol):
    def emit_heartbeat(self, occurred_at: datetime) -> None:
        ...

    def collect_snapshots(self, occurred_at: datetime) -> None:
        ...

    def flush_outbox(self, occurred_at: datetime) -> None:
        ...


class SystemClock:
    def now(self) -> datetime:
        current = datetime.now().astimezone()
        return current.replace(microsecond=(current.microsecond // 1000) * 1000)


@dataclass(frozen=True)
class RunnerCycleResult:
    occurred_at: datetime
    ran_heartbeat: bool
    ran_snapshot: bool
    ran_flush: bool
    sleep_seconds: float


@dataclass
class RunnerSchedule:
    next_heartbeat_at: datetime
    next_snapshot_at: datetime
    next_flush_at: datetime

    @classmethod
    def create(cls, started_at: datetime) -> RunnerSchedule:
        return cls(
            next_heartbeat_at=started_at,
            next_snapshot_at=started_at,
            next_flush_at=started_at,
        )


def _advance_due_time(due_at: datetime, interval_seconds: int, now: datetime) -> datetime:
    next_due = due_at
    interval = timedelta(seconds=interval_seconds)
    while next_due <= now:
        next_due += interval
    return next_due


class AgentRunner:
    def __init__(
        self,
        config: AgentConfig,
        services: RunnerServices,
        *,
        clock: Clock | None = None,
    ) -> None:
        self.config = config
        self.services = services
        self.clock = clock or SystemClock()
        self.schedule = RunnerSchedule.create(self.clock.now())
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def _flush_failed(self) -> bool:
        last_cycle = getattr(self.services, "last_cycle", None)
        flush_error = getattr(last_cycle, "flush_error", None)
        return isinstance(flush_error, str) and bool(flush_error.strip())

    def run_cycle(self, *, now: datetime | None = None) -> RunnerCycleResult:
        occurred_at = now or self.clock.now()
        intervals = self.config.intervals

        ran_heartbeat = occurred_at >= self.schedule.next_heartbeat_at
        ran_snapshot = occurred_at >= self.schedule.next_snapshot_at
        ran_flush = occurred_at >= self.schedule.next_flush_at

        if ran_heartbeat:
            self.services.emit_heartbeat(occurred_at)
            self.schedule.next_heartbeat_at = _advance_due_time(
                self.schedule.next_heartbeat_at,
                intervals.heartbeat_seconds,
                occurred_at,
            )

        if ran_snapshot:
            self.services.collect_snapshots(occurred_at)
            self.schedule.next_snapshot_at = _advance_due_time(
                self.schedule.next_snapshot_at,
                intervals.snapshot_seconds,
                occurred_at,
            )

        if ran_flush:
            self.services.flush_outbox(occurred_at)
            if self._flush_failed():
                self.schedule.next_flush_at = occurred_at + timedelta(
                    seconds=intervals.retry_backoff_seconds
                )
            else:
                self.schedule.next_flush_at = _advance_due_time(
                    self.schedule.next_flush_at,
                    intervals.flush_seconds,
                    occurred_at,
                )

        return RunnerCycleResult(
            occurred_at=occurred_at,
            ran_heartbeat=ran_heartbeat,
            ran_snapshot=ran_snapshot,
            ran_flush=ran_flush,
            sleep_seconds=self.seconds_until_next_due(now=occurred_at),
        )

    def seconds_until_next_due(self, *, now: datetime | None = None) -> float:
        current = now or self.clock.now()
        next_due = min(
            self.schedule.next_heartbeat_at,
            self.schedule.next_snapshot_at,
            self.schedule.next_flush_at,
        )
        return max(0.0, (next_due - current).total_seconds())

    def run_forever(self, *, max_cycles: int | None = None, sleep_func=sleep) -> int:
        cycles = 0
        while not self._stop_requested:
            self.run_cycle()
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            delay = self.seconds_until_next_due()
            if delay > 0:
                sleep_func(delay)
        return cycles


class LoggingRunnerServices:
    def __init__(self) -> None:
        self.actions: list[tuple[str, str]] = []

    def emit_heartbeat(self, occurred_at: datetime) -> None:
        self.actions.append(("heartbeat", occurred_at.isoformat(timespec="milliseconds")))

    def collect_snapshots(self, occurred_at: datetime) -> None:
        self.actions.append(("snapshot", occurred_at.isoformat(timespec="milliseconds")))

    def flush_outbox(self, occurred_at: datetime) -> None:
        self.actions.append(("flush", occurred_at.isoformat(timespec="milliseconds")))


def build_default_runner(config: AgentConfig, *, clock: Clock | None = None) -> AgentRunner:
    return AgentRunner(config, LoggingRunnerServices(), clock=clock)
