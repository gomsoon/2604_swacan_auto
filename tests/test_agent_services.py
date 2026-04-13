from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agent.collector import ProcessSnapshotCollector
from agent.config import AgentConfig, AgentIntervals, AgentTarget
from agent.host_collector import HostSnapshotCollector
from agent.selector import ProcfsSelector
from agent.services import AgentRuntimeServices
from agent.storage import AgentStorage
from tests.test_agent_collector import make_proc_snapshot_fixture
from tests.test_agent_host_collector import make_host_proc_fixture
from tests.test_agent_selector import make_process


def sample_config(tmp_path: Path) -> AgentConfig:
    return AgentConfig(
        config_path=tmp_path / "agent.toml",
        storage_path=tmp_path / "agent.sqlite3",
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
        "process_snapshot",
    ]
    assert rows[0].target_id == "agent_local"
    assert rows[1].target_id == "agent_local:host"
    assert rows[2].target_id == "app_main"
    assert storage.pending_count() == 3
