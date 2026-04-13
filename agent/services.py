from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

from .collector import ProcessSnapshotCollector
from .config import AgentConfig
from .host_collector import HostSnapshotCollector
from .payloads import OutboxItem
from .selector import ProcfsSelector
from .storage import AgentStorage


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


@dataclass
class CollectedCycleSummary:
    heartbeat_seq: int | None = None
    host_snapshot_seq: int | None = None
    process_snapshot_seqs: list[int] = field(default_factory=list)


class AgentRuntimeServices:
    def __init__(
        self,
        config: AgentConfig,
        storage: AgentStorage,
        *,
        selector: ProcfsSelector | None = None,
        process_collector: ProcessSnapshotCollector | None = None,
        host_collector: HostSnapshotCollector | None = None,
        agent_version: str = "0.1.0-dev",
        backend_connection_status: str = "idle",
        pid_provider=os.getpid,
    ) -> None:
        self.config = config
        self.storage = storage
        self.selector = selector or ProcfsSelector()
        self.process_collector = process_collector or ProcessSnapshotCollector()
        self.host_collector = host_collector or HostSnapshotCollector()
        self.agent_version = agent_version
        self.backend_connection_status = backend_connection_status
        self.pid_provider = pid_provider
        self.started_at = datetime.now().astimezone().replace(microsecond=0)
        self.last_cycle = CollectedCycleSummary()

    def emit_heartbeat(self, occurred_at: datetime) -> None:
        boot_id = self.host_collector.collect(occurred_at=occurred_at)[0].boot_id
        item = OutboxItem(
            payload_type="agent_state",
            target_id=self.config.agent_id,
            occurred_at=_iso(occurred_at),
            payload={
                "agent_id": self.config.agent_id,
                "agent_pid": self.pid_provider(),
                "agent_version": self.agent_version,
                "start_time": _iso(self.started_at),
                "heartbeat_time": _iso(occurred_at),
                "backend_connection_status": self.backend_connection_status,
                "outbox_queue_depth": self.storage.pending_count(),
                "last_sent_seq": self.storage.last_seq(),
                "last_ack_seq": self.storage.last_ack_seq(),
                "monitored_target_count": len(self.config.targets),
                "host_boot_id": boot_id,
            },
        )
        self.last_cycle.heartbeat_seq = self.storage.enqueue_item(item)

    def collect_snapshots(self, occurred_at: datetime) -> None:
        host_previous = self.storage.load_host_cpu_sample()
        host_snapshot, host_sample = self.host_collector.collect(
            occurred_at=occurred_at,
            previous_cpu_sample=host_previous,
        )
        self.storage.save_host_cpu_sample(host_sample)
        self.last_cycle.host_snapshot_seq = self.storage.enqueue_item(
            OutboxItem(
                payload_type="host_snapshot",
                target_id=f"{self.config.agent_id}:host",
                occurred_at=_iso(occurred_at),
                payload=host_snapshot.to_payload(),
            )
        )

        process_sequences: list[int] = []
        for target in self.config.targets:
            matches = self.selector.discover(target)
            for match in matches:
                previous_cpu = self.storage.load_process_cpu_sample(target_id=target.target_id, pid=match.pid)
                snapshot, cpu_sample = self.process_collector.collect(
                    match,
                    occurred_at=occurred_at,
                    previous_cpu_sample=previous_cpu,
                )
                self.storage.save_process_cpu_sample(
                    target_id=target.target_id,
                    pid=match.pid,
                    sample=cpu_sample,
                    sampled_at=_iso(occurred_at),
                )
                seq = self.storage.enqueue_item(
                    OutboxItem(
                        payload_type="process_snapshot",
                        target_id=target.target_id,
                        occurred_at=_iso(occurred_at),
                        payload=snapshot.to_payload(),
                    )
                )
                process_sequences.append(seq)

        self.last_cycle.process_snapshot_seqs = process_sequences

    def flush_outbox(self, occurred_at: datetime) -> None:
        _ = occurred_at
        return None
