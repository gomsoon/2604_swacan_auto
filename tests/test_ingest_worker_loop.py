from __future__ import annotations

from app.ingest_worker import IngestWorkerLoop


def test_ingest_worker_loop_idles_when_no_work() -> None:
    worker = IngestWorkerLoop(
        limit=10,
        idle_sleep_seconds=1.5,
        error_backoff_seconds=4.0,
        processor=lambda limit: {
            "processed_batches": 0,
            "failed_batches": 0,
            "processed_items": 0,
        },
    )

    result = worker.run_cycle()

    assert result.processed_batches == 0
    assert result.failed_batches == 0
    assert result.processed_items == 0
    assert result.sleep_seconds == 1.5
    assert result.had_error is False


def test_ingest_worker_loop_does_not_sleep_when_work_processed() -> None:
    worker = IngestWorkerLoop(
        limit=10,
        idle_sleep_seconds=1.5,
        error_backoff_seconds=4.0,
        processor=lambda limit: {
            "processed_batches": 1,
            "failed_batches": 0,
            "processed_items": 4,
        },
    )

    result = worker.run_cycle()

    assert result.processed_batches == 1
    assert result.processed_items == 4
    assert result.sleep_seconds == 0.0
    assert result.had_error is False


def test_ingest_worker_loop_uses_error_backoff_on_exception() -> None:
    def failing_processor(*, limit: int):
        raise RuntimeError(f"temporary db issue for limit={limit}")

    worker = IngestWorkerLoop(
        limit=25,
        idle_sleep_seconds=1.5,
        error_backoff_seconds=4.0,
        processor=failing_processor,
    )

    result = worker.run_cycle()

    assert result.had_error is True
    assert result.sleep_seconds == 4.0
    assert result.error_message == "temporary db issue for limit=25"


def test_ingest_worker_loop_run_forever_aggregates_cycle_counts() -> None:
    calls = {"count": 0}

    def processor(*, limit: int):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"processed_batches": 1, "failed_batches": 0, "processed_items": 3}
        return {"processed_batches": 0, "failed_batches": 0, "processed_items": 0}

    sleeps: list[float] = []
    worker = IngestWorkerLoop(
        limit=10,
        idle_sleep_seconds=2.5,
        error_backoff_seconds=4.0,
        processor=processor,
    )

    summary = worker.run_forever(max_cycles=3, sleep_func=lambda seconds: sleeps.append(seconds))

    assert summary.cycles == 3
    assert summary.processed_batches == 1
    assert summary.failed_batches == 0
    assert summary.processed_items == 3
    assert sleeps == [2.5]


def test_ingest_worker_loop_runs_cleanup_on_interval() -> None:
    cleanup_calls: list[str] = []

    worker = IngestWorkerLoop(
        limit=10,
        idle_sleep_seconds=0.0,
        error_backoff_seconds=4.0,
        processor=lambda limit: {
            "processed_batches": 0,
            "failed_batches": 0,
            "processed_items": 0,
        },
        cleanup_every_cycles=2,
        cleanup_func=lambda: cleanup_calls.append("cleanup"),
    )

    summary = worker.run_forever(max_cycles=5, sleep_func=lambda seconds: None)

    assert summary.cycles == 5
    assert cleanup_calls == ["cleanup", "cleanup"]
