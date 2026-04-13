from __future__ import annotations

import json

from agent.collector import CpuSample
from agent.host_collector import HostCpuSample
from agent.payloads import OutboxItem
from agent.storage import AgentStorage


def test_storage_initializes_outbox_schema(tmp_path) -> None:
    db_path = tmp_path / "agent.sqlite3"
    storage = AgentStorage(db_path)

    storage.initialize()

    assert db_path.exists()
    assert storage.list_outbox() == []


def test_storage_enqueues_items_and_marks_ack(tmp_path) -> None:
    db_path = tmp_path / "agent.sqlite3"
    storage = AgentStorage(db_path)
    storage.initialize()

    first_seq = storage.enqueue_item(
        OutboxItem(
            payload_type="agent_state",
            target_id="agent_local",
            occurred_at="2026-04-13T10:40:00.000+09:00",
            payload={"status": "up"},
        )
    )
    second_seq = storage.enqueue_item(
        OutboxItem(
            payload_type="process_snapshot",
            target_id="app_main",
            occurred_at="2026-04-13T10:40:01.000+09:00",
            payload={"pid": 1234, "state": "running"},
        )
    )

    rows = storage.list_outbox(include_acked=False)

    assert first_seq == 1
    assert second_seq == 2
    assert storage.last_seq() == 2
    assert storage.pending_count() == 2
    assert json.loads(rows[0].payload_json)["payload_type"] == "agent_state"

    storage.mark_acked(1, acked_at="2026-04-13T10:40:05.000+09:00")

    pending_rows = storage.list_outbox(include_acked=False)

    assert storage.last_ack_seq() == 1
    assert [row.seq for row in pending_rows] == [2]


def test_storage_persists_cpu_samples(tmp_path) -> None:
    db_path = tmp_path / "agent.sqlite3"
    storage = AgentStorage(db_path)
    storage.initialize()

    storage.save_host_cpu_sample(HostCpuSample(idle_ticks=100, total_ticks=200))
    storage.save_process_cpu_sample(
        target_id="app_main",
        pid=1234,
        sample=CpuSample(process_ticks=50, system_ticks=1000),
        sampled_at="2026-04-13T10:40:00.000+09:00",
    )

    host_sample = storage.load_host_cpu_sample()
    process_sample = storage.load_process_cpu_sample(target_id="app_main", pid=1234)

    assert host_sample == HostCpuSample(idle_ticks=100, total_ticks=200)
    assert process_sample == CpuSample(process_ticks=50, system_ticks=1000)


def test_storage_lists_pending_outbox_with_limit_and_marks_attempted(tmp_path) -> None:
    db_path = tmp_path / "agent.sqlite3"
    storage = AgentStorage(db_path)
    storage.initialize()

    for offset in range(3):
        storage.enqueue_item(
            OutboxItem(
                payload_type="process_snapshot",
                target_id=f"app_{offset}",
                occurred_at=f"2026-04-13T10:40:0{offset}.000+09:00",
                payload={"pid": 1000 + offset, "state": "running"},
            )
        )

    pending_rows = storage.list_pending_outbox(limit=2)
    storage.mark_attempted([row.seq for row in pending_rows], attempted_at="2026-04-13T10:40:10.000+09:00")
    all_rows = storage.list_outbox(include_acked=False)

    assert [row.seq for row in pending_rows] == [1, 2]
    assert [row.retry_count for row in all_rows] == [1, 1, 0]
