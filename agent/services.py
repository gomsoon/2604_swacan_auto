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
from .transport import AgentTransport


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


def _format_pid_list(pids: list[int]) -> str:
    return ", ".join(str(pid) for pid in sorted(set(pids))) if pids else "-"


@dataclass
class CollectedCycleSummary:
    heartbeat_seq: int | None = None
    host_snapshot_seq: int | None = None
    process_snapshot_seqs: list[int] = field(default_factory=list)
    process_event_seqs: list[int] = field(default_factory=list)
    flush_sent_count: int = 0
    flush_ack_seq: int | None = None
    flush_error: str | None = None
    purged_acked_count: int = 0


class AgentRuntimeServices:
    def __init__(
        self,
        config: AgentConfig,
        storage: AgentStorage,
        *,
        selector: ProcfsSelector | None = None,
        process_collector: ProcessSnapshotCollector | None = None,
        host_collector: HostSnapshotCollector | None = None,
        transport: AgentTransport | None = None,
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
        self.boot_id = self.host_collector.collect(occurred_at=self.started_at)[0].boot_id
        self.transport = transport or AgentTransport(config, storage, boot_id=self.boot_id)
        self.last_cycle = CollectedCycleSummary()

    def emit_heartbeat(self, occurred_at: datetime) -> None:
        pending_count = self.storage.pending_count()
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
                "outbox_queue_depth": pending_count,
                "outbox_pending_warning_rows": self.config.storage.pending_warning_rows,
                "outbox_warning_threshold_exceeded": pending_count >= self.config.storage.pending_warning_rows,
                "last_sent_seq": self.storage.last_seq(),
                "last_ack_seq": self.storage.last_ack_seq(),
                "monitored_target_count": len(self.config.targets),
                "host_boot_id": self.boot_id,
            },
        )
        self.last_cycle.heartbeat_seq = self.storage.enqueue_item(item)

    def _build_process_transition_item(
        self,
        *,
        target,
        occurred_at: datetime,
        previous_pids: list[int],
        current_pids: list[int],
    ) -> OutboxItem | None:
        previous_unique = sorted(set(previous_pids))
        current_unique = sorted(set(current_pids))
        if not previous_unique and not current_unique:
            return None

        message: str
        event_type: str
        severity: str
        if not previous_unique and current_unique:
            event_type = "process_started"
            severity = "normal"
            message = (
                f"target '{target.target_id}' started with pid(s): {_format_pid_list(current_unique)}"
            )
        elif previous_unique and not current_unique:
            event_type = "process_stopped"
            severity = "warning"
            message = (
                f"target '{target.target_id}' stopped; previous pid(s): {_format_pid_list(previous_unique)}"
            )
        elif previous_unique != current_unique:
            event_type = "process_restarted"
            severity = "warning"
            message = (
                f"target '{target.target_id}' changed pid(s) from "
                f"{_format_pid_list(previous_unique)} to {_format_pid_list(current_unique)}"
            )
        else:
            return None

        return OutboxItem(
            payload_type="process_event",
            target_id=target.target_id,
            occurred_at=_iso(occurred_at),
            payload={
                "event_type": event_type,
                "severity": severity,
                "message": message,
                "selector_mode": target.mode,
                "previous_pids": previous_unique,
                "current_pids": current_unique,
                "instance_count": len(current_unique),
            },
        )

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
        process_event_sequences: list[int] = []
        discovered_matches = self.selector.discover_targets(self.config.targets)
        for target in self.config.targets:
            matches = discovered_matches.get(target.target_id, [])
            current_pids = [match.pid for match in matches]
            previous_state = self.storage.load_target_runtime_state(target.target_id)
            previous_pids = list(previous_state.pid_set) if previous_state is not None else []

            event_item = self._build_process_transition_item(
                target=target,
                occurred_at=occurred_at,
                previous_pids=previous_pids,
                current_pids=current_pids,
            )
            if event_item is not None:
                process_event_sequences.append(self.storage.enqueue_item(event_item))

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

            self.storage.save_target_runtime_state(
                target_id=target.target_id,
                pids=current_pids,
                updated_at=_iso(occurred_at),
            )

        self.last_cycle.process_snapshot_seqs = process_sequences
        self.last_cycle.process_event_seqs = process_event_sequences

    def flush_outbox(self, occurred_at: datetime) -> None:
        try:
            result = self.transport.send_pending(sent_at=occurred_at)
        except Exception as exc:
            self.backend_connection_status = "error"
            self.last_cycle.flush_sent_count = 0
            self.last_cycle.flush_ack_seq = None
            self.last_cycle.flush_error = str(exc)
            self.last_cycle.purged_acked_count = 0
            return

        if result.sent_count > 0:
            self.backend_connection_status = "connected"

        purged_count = 0
        if result.ack_seq is not None:
            purged_count = self.storage.purge_acked_rows(
                keep_latest=self.config.storage.keep_acked_rows,
                delete_limit=self.config.storage.cleanup_batch_size,
            )

        self.last_cycle.flush_sent_count = result.sent_count
        self.last_cycle.flush_ack_seq = result.ack_seq
        self.last_cycle.flush_error = None
        self.last_cycle.purged_acked_count = purged_count
