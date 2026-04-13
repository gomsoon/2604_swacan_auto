from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib import request

from .config import AgentConfig
from .storage import AgentStorage, StoredOutboxRow


@dataclass(frozen=True)
class BatchPayload:
    agent_id: str
    boot_id: str
    seq_start: int
    seq_end: int
    sent_at: str
    items: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "agent_id": self.agent_id,
            "boot_id": self.boot_id,
            "seq_start": self.seq_start,
            "seq_end": self.seq_end,
            "sent_at": self.sent_at,
            "items": self.items,
        }


@dataclass(frozen=True)
class TransportResult:
    sent_count: int
    ack_seq: int | None
    accepted_count: int
    server_time: str | None


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


def build_batch_payload(
    *,
    agent_id: str,
    boot_id: str,
    rows: list[StoredOutboxRow],
    sent_at: datetime,
) -> BatchPayload | None:
    if not rows:
        return None

    items: list[dict[str, object]] = []
    for row in rows:
        row_payload = json.loads(row.payload_json)
        items.append(
            {
                "seq": row.seq,
                "payload_type": row.payload_type,
                "occurred_at": row.occurred_at,
                "target_id": row.target_id,
                "payload": row_payload["payload"],
            }
        )

    return BatchPayload(
        agent_id=agent_id,
        boot_id=boot_id,
        seq_start=rows[0].seq,
        seq_end=rows[-1].seq,
        sent_at=_iso(sent_at),
        items=items,
    )


class AgentTransport:
    def __init__(
        self,
        config: AgentConfig,
        storage: AgentStorage,
        *,
        boot_id: str,
        batch_size: int = 20,
        timeout_seconds: int = 10,
        opener=request.urlopen,
    ) -> None:
        self.config = config
        self.storage = storage
        self.boot_id = boot_id
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    def send_pending(self, *, sent_at: datetime) -> TransportResult:
        rows = self.storage.list_pending_outbox(limit=self.batch_size)
        if not rows:
            return TransportResult(sent_count=0, ack_seq=None, accepted_count=0, server_time=None)

        payload = build_batch_payload(
            agent_id=self.config.agent_id,
            boot_id=self.boot_id,
            rows=rows,
            sent_at=sent_at,
        )
        if payload is None:
            return TransportResult(sent_count=0, ack_seq=None, accepted_count=0, server_time=None)

        self.storage.mark_attempted([row.seq for row in rows], attempted_at=_iso(sent_at))

        request_payload = json.dumps(payload.to_dict(), ensure_ascii=False).encode("utf-8")
        req = request.Request(
            self.config.backend_endpoint,
            data=request_payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Agent-Id": self.config.agent_id,
                "X-Agent-Token": self.config.token,
            },
            method="POST",
        )

        with self.opener(req, timeout=self.timeout_seconds) as response:  # noqa: S310
            response_payload = json.loads(response.read().decode("utf-8"))

        ack_seq = int(response_payload["ack_seq"])
        self.storage.mark_acked(ack_seq, acked_at=response_payload.get("server_time"))
        return TransportResult(
            sent_count=len(rows),
            ack_seq=ack_seq,
            accepted_count=int(response_payload.get("accepted_count", len(rows))),
            server_time=response_payload.get("server_time"),
        )
