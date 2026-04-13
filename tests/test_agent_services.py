from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agent.collector import ProcessSnapshotCollector
from agent.config import AgentConfig, AgentIntervals, AgentStoragePolicy, AgentTarget
from agent.host_collector import HostSnapshotCollector
from agent.payloads import OutboxItem
from agent.selector import ProcfsSelector
from agent.services import AgentRuntimeServices
from agent.storage import AgentStorage
from agent.transport import TransportResult
from tests.test_agent_collector import make_proc_snapshot_fixture
from tests.test_agent_host_collector import make_host_proc_fixture
from tests.test_agent_selector import make_process


def sample_config(tmp_path: Path) -> AgentConfig:
    return AgentConfig(
        config_path=tmp_path / "agent.toml",
        storage_path=tmp_path / "agent.sqlite3",
        storage=AgentStoragePolicy(
            keep_acked_rows=2,
            cleanup_batch_size=10,
            pending_warning_rows=3,
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
                command_line_regex="app.py",
                executable_path=None,
                pid=None,
            ),
        ),
    )


def test_runtime_services_enqueue_heartbeat_and_snapshots(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    make_host_proc_fixture(
        proc_root,
        cpu_fields=[100, 20, 30, 400, 10, 0, 0, 0, 0, 0],
        loadavg=(0.15, 0.25, 0.35),
        uptime_seconds=321.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 3,
    )
    make_process(proc_root, pid=1234, name="python", cmdline="python app.py", exe_path="/usr/bin/python")
    make_proc_snapshot_fixture(proc_root, pid=1234)

    config = sample_config(tmp_path)
    storage = AgentStorage(config.storage_path)
    storage.initialize()
    services = AgentRuntimeServices(
        config,
        storage,
        selector=ProcfsSelector(proc_root=proc_root),
        process_collector=ProcessSnapshotCollector(proc_root=proc_root),
        host_collector=HostSnapshotCollector(proc_root=proc_root),
        pid_provider=lambda: 4321,
    )

    occurred_at = datetime(2026, 4, 13, 10, 45, 0, tzinfo=timezone.utc)
    services.emit_heartbeat(occurred_at)
    services.collect_snapshots(occurred_at)

    rows = storage.list_outbox(include_acked=False)

    assert [row.payload_type for row in rows] == [
        "agent_state",
        "host_snapshot",
        "process_event",
        "process_snapshot",
    ]
    assert rows[0].target_id == "agent_local"
    assert rows[1].target_id == "agent_local:host"
    assert rows[2].target_id == "app_main"
    assert rows[3].target_id == "app_main"
    assert storage.pending_count() == 4
    heartbeat_payload = rows[0].payload_json
    process_event_payload = rows[2].payload_json
    assert '"outbox_pending_warning_rows": 3' in heartbeat_payload
    assert '"outbox_warning_threshold_exceeded": false' in heartbeat_payload
    assert '"event_type": "process_started"' in process_event_payload
    assert services.last_cycle.process_event_seqs


def test_runtime_services_collect_snapshots_emits_process_stopped_event(tmp_path) -> None:
    proc_root = tmp_path / "proc_stopped"
    make_host_proc_fixture(
        proc_root,
        cpu_fields=[100, 20, 30, 400, 10, 0, 0, 0, 0, 0],
        loadavg=(0.15, 0.25, 0.35),
        uptime_seconds=321.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 3,
    )
    make_process(proc_root, pid=1234, name="python", cmdline="python app.py", exe_path="/usr/bin/python")
    make_proc_snapshot_fixture(proc_root, pid=1234)

    config = sample_config(tmp_path)
    storage = AgentStorage(config.storage_path)
    storage.initialize()
    services = AgentRuntimeServices(
        config,
        storage,
        selector=ProcfsSelector(proc_root=proc_root),
        process_collector=ProcessSnapshotCollector(proc_root=proc_root),
        host_collector=HostSnapshotCollector(proc_root=proc_root),
    )

    first_at = datetime(2026, 4, 13, 10, 45, 0, tzinfo=timezone.utc)
    services.collect_snapshots(first_at)

    for path in (proc_root / "1234").rglob("*"):
        if path.is_file():
            path.unlink()
    for path in sorted((proc_root / "1234").rglob("*"), reverse=True):
        if path.is_dir():
            path.rmdir()
    (proc_root / "1234").rmdir()

    second_at = datetime(2026, 4, 13, 10, 45, 5, tzinfo=timezone.utc)
    services.collect_snapshots(second_at)

    rows = storage.list_outbox(include_acked=False)
    payloads = [row.payload_json for row in rows if row.payload_type == "process_event"]

    assert any('"event_type": "process_started"' in payload for payload in payloads)
    assert any('"event_type": "process_stopped"' in payload for payload in payloads)


def test_runtime_services_collect_snapshots_emits_process_restarted_event(tmp_path) -> None:
    proc_root = tmp_path / "proc_restarted"
    make_host_proc_fixture(
        proc_root,
        cpu_fields=[100, 20, 30, 400, 10, 0, 0, 0, 0, 0],
        loadavg=(0.15, 0.25, 0.35),
        uptime_seconds=321.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 3,
    )
    make_process(proc_root, pid=1234, name="python", cmdline="python app.py", exe_path="/usr/bin/python")
    make_proc_snapshot_fixture(proc_root, pid=1234)

    config = sample_config(tmp_path)
    storage = AgentStorage(config.storage_path)
    storage.initialize()
    services = AgentRuntimeServices(
        config,
        storage,
        selector=ProcfsSelector(proc_root=proc_root),
        process_collector=ProcessSnapshotCollector(proc_root=proc_root),
        host_collector=HostSnapshotCollector(proc_root=proc_root),
    )

    first_at = datetime(2026, 4, 13, 10, 45, 0, tzinfo=timezone.utc)
    services.collect_snapshots(first_at)

    for path in (proc_root / "1234").rglob("*"):
        if path.is_file():
            path.unlink()
    for path in sorted((proc_root / "1234").rglob("*"), reverse=True):
        if path.is_dir():
            path.rmdir()
    (proc_root / "1234").rmdir()

    make_process(proc_root, pid=2234, name="python", cmdline="python app.py", exe_path="/usr/bin/python")
    make_proc_snapshot_fixture(proc_root, pid=2234)

    second_at = datetime(2026, 4, 13, 10, 45, 5, tzinfo=timezone.utc)
    services.collect_snapshots(second_at)

    rows = storage.list_outbox(include_acked=False)
    payloads = [row.payload_json for row in rows if row.payload_type == "process_event"]

    assert any('"event_type": "process_started"' in payload for payload in payloads)
    assert any('"event_type": "process_restarted"' in payload for payload in payloads)


class SuccessfulTransport:
    def __init__(self) -> None:
        self.sent_at: str | None = None

    def send_pending(self, *, sent_at):
        self.sent_at = sent_at.isoformat(timespec="milliseconds")
        return TransportResult(
            sent_count=3,
            ack_seq=3,
            accepted_count=3,
            server_time="2026-04-13T10:45:01.000+00:00",
        )


class FailingTransport:
    def send_pending(self, *, sent_at):
        raise RuntimeError("temporary backend failure")


def test_runtime_services_flush_outbox_updates_connection_status(tmp_path) -> None:
    config = sample_config(tmp_path)
    storage = AgentStorage(config.storage_path)
    storage.initialize()
    transport = SuccessfulTransport()
    proc_root = tmp_path / "proc_success"
    make_host_proc_fixture(
        proc_root,
        cpu_fields=[100, 20, 30, 400, 10, 0, 0, 0, 0, 0],
        loadavg=(0.15, 0.25, 0.35),
        uptime_seconds=321.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 3,
    )
    services = AgentRuntimeServices(
        config,
        storage,
        transport=transport,
        host_collector=HostSnapshotCollector(proc_root=proc_root),
    )

    occurred_at = datetime(2026, 4, 13, 10, 45, 0, tzinfo=timezone.utc)
    services.flush_outbox(occurred_at)

    assert transport.sent_at == "2026-04-13T10:45:00.000+00:00"
    assert services.backend_connection_status == "connected"
    assert services.last_cycle.flush_sent_count == 3
    assert services.last_cycle.flush_ack_seq == 3
    assert services.last_cycle.flush_error is None
    assert services.last_cycle.purged_acked_count == 0


def test_runtime_services_flush_outbox_handles_transport_failure(tmp_path) -> None:
    config = sample_config(tmp_path)
    storage = AgentStorage(config.storage_path)
    storage.initialize()
    proc_root = tmp_path / "proc_failure"
    make_host_proc_fixture(
        proc_root,
        cpu_fields=[100, 20, 30, 400, 10, 0, 0, 0, 0, 0],
        loadavg=(0.15, 0.25, 0.35),
        uptime_seconds=321.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 3,
    )
    services = AgentRuntimeServices(
        config,
        storage,
        transport=FailingTransport(),
        host_collector=HostSnapshotCollector(proc_root=proc_root),
    )

    occurred_at = datetime(2026, 4, 13, 10, 45, 0, tzinfo=timezone.utc)
    services.flush_outbox(occurred_at)

    assert services.backend_connection_status == "error"
    assert services.last_cycle.flush_sent_count == 0
    assert services.last_cycle.flush_ack_seq is None
    assert services.last_cycle.flush_error == "temporary backend failure"


def test_runtime_services_flush_outbox_purges_old_acked_rows(tmp_path) -> None:
    config = sample_config(tmp_path)
    storage = AgentStorage(config.storage_path)
    storage.initialize()
    for offset in range(5):
        storage.enqueue_item(
            OutboxItem(
                payload_type="process_snapshot",
                target_id=f"app_{offset}",
                occurred_at=f"2026-04-13T10:45:0{offset}.000+00:00",
                payload={"pid": 1200 + offset, "state": "running"},
            )
        )
    storage.mark_acked(5, acked_at="2026-04-13T10:45:10.000+00:00")

    proc_root = tmp_path / "proc_cleanup"
    make_host_proc_fixture(
        proc_root,
        cpu_fields=[100, 20, 30, 400, 10, 0, 0, 0, 0, 0],
        loadavg=(0.15, 0.25, 0.35),
        uptime_seconds=321.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 3,
    )
    services = AgentRuntimeServices(
        config,
        storage,
        transport=SuccessfulTransport(),
        host_collector=HostSnapshotCollector(proc_root=proc_root),
    )

    occurred_at = datetime(2026, 4, 13, 10, 45, 0, tzinfo=timezone.utc)
    services.flush_outbox(occurred_at)

    rows = storage.list_outbox()
    assert [row.seq for row in rows] == [4, 5]
    assert services.last_cycle.purged_acked_count == 3
