from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .collector import CpuSample
from .host_collector import HostCpuSample
from .payloads import OutboxItem


@dataclass(frozen=True)
class StoredOutboxRow:
    seq: int
    payload_type: str
    target_id: str
    occurred_at: str
    payload_json: str
    retry_count: int
    acked_at: str | None


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


class AgentStorage:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS outbox (
                    seq INTEGER PRIMARY KEY,
                    payload_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    acked_at TEXT NULL,
                    created_at TEXT NOT NULL,
                    last_attempt_at TEXT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS target_cache (
                    target_id TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    process_ticks INTEGER NOT NULL,
                    system_ticks INTEGER NOT NULL,
                    sampled_at TEXT NOT NULL,
                    PRIMARY KEY (target_id, pid)
                );

                CREATE INDEX IF NOT EXISTS idx_outbox_ack_seq ON outbox (acked_at, seq);
                """
            )

    def _get_meta(self, key: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM agent_meta WHERE key = ?",
                (key,),
            ).fetchone()
        return None if row is None else str(row["value"])

    def _set_meta(self, key: str, value: str) -> None:
        now_iso = _now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_meta (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now_iso),
            )
            connection.commit()

    def last_seq(self) -> int:
        value = self._get_meta("last_seq")
        return int(value) if value is not None else 0

    def last_ack_seq(self) -> int:
        value = self._get_meta("last_ack_seq")
        return int(value) if value is not None else 0

    def next_seq(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM agent_meta WHERE key = 'last_seq'"
            ).fetchone()
            current = int(row["value"]) if row is not None else 0
            next_value = current + 1
            connection.execute(
                """
                INSERT INTO agent_meta (key, value, updated_at)
                VALUES ('last_seq', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (str(next_value), _now_iso()),
            )
            connection.commit()
        return next_value

    def enqueue_item(self, item: OutboxItem) -> int:
        seq = self.next_seq()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO outbox (
                    seq, payload_type, target_id, occurred_at, payload_json,
                    retry_count, acked_at, created_at, last_attempt_at
                ) VALUES (?, ?, ?, ?, ?, 0, NULL, ?, NULL)
                """,
                (
                    seq,
                    item.payload_type,
                    item.target_id,
                    item.occurred_at,
                    item.to_json(),
                    _now_iso(),
                ),
            )
            connection.commit()
        return seq

    def list_outbox(self, *, include_acked: bool = True) -> list[StoredOutboxRow]:
        query = """
            SELECT seq, payload_type, target_id, occurred_at, payload_json, retry_count, acked_at
            FROM outbox
        """
        if not include_acked:
            query += " WHERE acked_at IS NULL"
        query += " ORDER BY seq"

        with self.connect() as connection:
            rows = connection.execute(query).fetchall()
        return [
            StoredOutboxRow(
                seq=int(row["seq"]),
                payload_type=str(row["payload_type"]),
                target_id=str(row["target_id"]),
                occurred_at=str(row["occurred_at"]),
                payload_json=str(row["payload_json"]),
                retry_count=int(row["retry_count"]),
                acked_at=None if row["acked_at"] is None else str(row["acked_at"]),
            )
            for row in rows
        ]

    def list_pending_outbox(self, *, limit: int) -> list[StoredOutboxRow]:
        query = """
            SELECT seq, payload_type, target_id, occurred_at, payload_json, retry_count, acked_at
            FROM outbox
            WHERE acked_at IS NULL
            ORDER BY seq
            LIMIT ?
        """
        with self.connect() as connection:
            rows = connection.execute(query, (limit,)).fetchall()
        return [
            StoredOutboxRow(
                seq=int(row["seq"]),
                payload_type=str(row["payload_type"]),
                target_id=str(row["target_id"]),
                occurred_at=str(row["occurred_at"]),
                payload_json=str(row["payload_json"]),
                retry_count=int(row["retry_count"]),
                acked_at=None if row["acked_at"] is None else str(row["acked_at"]),
            )
            for row in rows
        ]

    def pending_count(self) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM outbox WHERE acked_at IS NULL"
            ).fetchone()
        return 0 if row is None else int(row["count"])

    def mark_acked(self, ack_seq: int, *, acked_at: str | None = None) -> None:
        acked_value = acked_at or _now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE outbox
                SET acked_at = ?
                WHERE seq <= ? AND acked_at IS NULL
                """,
                (acked_value, ack_seq),
            )
            connection.execute(
                """
                INSERT INTO agent_meta (key, value, updated_at)
                VALUES ('last_ack_seq', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (str(ack_seq), acked_value),
            )
            connection.commit()

    def mark_attempted(self, seq_values: list[int], *, attempted_at: str | None = None) -> None:
        if not seq_values:
            return
        attempt_value = attempted_at or _now_iso()
        placeholders = ", ".join("?" for _ in seq_values)
        with self.connect() as connection:
            connection.execute(
                f"""
                UPDATE outbox
                SET retry_count = retry_count + 1,
                    last_attempt_at = ?
                WHERE seq IN ({placeholders}) AND acked_at IS NULL
                """,
                (attempt_value, *seq_values),
            )
            connection.commit()

    def load_host_cpu_sample(self) -> HostCpuSample | None:
        idle_value = self._get_meta("host_idle_ticks")
        total_value = self._get_meta("host_total_ticks")
        if idle_value is None or total_value is None:
            return None
        return HostCpuSample(idle_ticks=int(idle_value), total_ticks=int(total_value))

    def save_host_cpu_sample(self, sample: HostCpuSample) -> None:
        self._set_meta("host_idle_ticks", str(sample.idle_ticks))
        self._set_meta("host_total_ticks", str(sample.total_ticks))

    def load_process_cpu_sample(self, *, target_id: str, pid: int) -> CpuSample | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT process_ticks, system_ticks
                FROM target_cache
                WHERE target_id = ? AND pid = ?
                """,
                (target_id, pid),
            ).fetchone()
        if row is None:
            return None
        return CpuSample(process_ticks=int(row["process_ticks"]), system_ticks=int(row["system_ticks"]))

    def save_process_cpu_sample(self, *, target_id: str, pid: int, sample: CpuSample, sampled_at: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO target_cache (target_id, pid, process_ticks, system_ticks, sampled_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(target_id, pid) DO UPDATE SET
                    process_ticks = excluded.process_ticks,
                    system_ticks = excluded.system_ticks,
                    sampled_at = excluded.sampled_at
                """,
                (target_id, pid, sample.process_ticks, sample.system_ticks, sampled_at),
            )
            connection.commit()
