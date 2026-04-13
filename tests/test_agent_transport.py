from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agent.config import AgentConfig, AgentIntervals, AgentTarget
from agent.payloads import OutboxItem
from agent.storage import AgentStorage
from agent.transport import AgentTransport, build_batch_payload


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


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class RecordingOpener:
    def __init__(self, response_payload: dict[str, object]) -> None:
        self.response_payload = response_payload
        self.requests: list[tuple[str, dict[str, str], dict[str, object], int]] = []

    def __call__(self, req, timeout: int):
        payload = json.loads(req.data.decode("utf-8"))
        headers = {key.lower(): value for key, value in req.header_items()}
        self.requests.append((req.full_url, headers, payload, timeout))
        return FakeResponse(self.response_payload)


def enqueue_sample_items(storage: AgentStorage) -> None:
    storage.enqueue_item(
        OutboxItem(
            payload_type="agent_state",
            target_id="agent_local",
            occurred_at="2026-04-13T10:50:00.000+09:00",
            payload={"status": "up"},
        )
    )
    storage.enqueue_item(
        OutboxItem(
            payload_type="host_snapshot",
            target_id="agent_local:host",
            occurred_at="2026-04-13T10:50:01.000+09:00",
            payload={"cpu_usage": 12.5},
        )
    )
    storage.enqueue_item(
        OutboxItem(
            payload_type="process_snapshot",
            target_id="app_main",
            occurred_at="2026-04-13T10:50:02.000+09:00",
            payload={"pid": 1234, "state": "running"},
        )
    )


def test_build_batch_payload_from_pending_rows(tmp_path) -> None:
    storage = AgentStorage(tmp_path / "agent.sqlite3")
    storage.initialize()
    enqueue_sample_items(storage)

    rows = storage.list_pending_outbox(limit=2)
    payload = build_batch_payload(
        agent_id="agent_local",
        boot_id="boot-001",
        rows=rows,
        sent_at=datetime(2026, 4, 13, 1, 50, 5, tzinfo=timezone.utc),
    )

    assert payload is not None
    assert payload.seq_start == 1
    assert payload.seq_end == 2
    assert [item["payload_type"] for item in payload.items] == ["agent_state", "host_snapshot"]
    assert payload.items[1]["target_id"] == "agent_local:host"


def test_transport_sends_batch_and_marks_items_acked(tmp_path) -> None:
    config = sample_config(tmp_path)
    storage = AgentStorage(config.storage_path)
    storage.initialize()
    enqueue_sample_items(storage)
    opener = RecordingOpener(
        {
            "ack_seq": 2,
            "accepted_count": 2,
            "server_time": "2026-04-13T10:50:10.000+09:00",
        }
    )
    transport = AgentTransport(
        config,
        storage,
        boot_id="boot-001",
        batch_size=2,
        timeout_seconds=7,
        opener=opener,
    )

    result = transport.send_pending(sent_at=datetime(2026, 4, 13, 1, 50, 5, tzinfo=timezone.utc))
    pending_rows = storage.list_outbox(include_acked=False)

    assert result.sent_count == 2
    assert result.ack_seq == 2
    assert result.accepted_count == 2
    assert storage.last_ack_seq() == 2
    assert [row.seq for row in pending_rows] == [3]

    url, headers, payload, timeout = opener.requests[0]
    assert url == "https://backend.example.com/api/agents/ingest"
    assert headers["x-agent-id"] == "agent_local"
    assert headers["x-agent-token"] == "dev-agent-token"
    assert timeout == 7
    assert payload["seq_start"] == 1
    assert payload["seq_end"] == 2
    assert len(payload["items"]) == 2
