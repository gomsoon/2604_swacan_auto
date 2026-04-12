from __future__ import annotations

import socket
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class HostCpuSample:
    idle_ticks: int
    total_ticks: int


@dataclass(frozen=True)
class HostSnapshot:
    hostname: str
    boot_id: str
    uptime_seconds: float
    loadavg_1: float
    loadavg_5: float
    loadavg_15: float
    cpu_usage: float
    memory_total: int
    memory_available: int
    memory_used: int
    sampled_at: str

    def to_payload(self) -> dict[str, object]:
        return {
            "hostname": self.hostname,
            "boot_id": self.boot_id,
            "uptime": round(self.uptime_seconds, 3),
            "loadavg_1": self.loadavg_1,
            "loadavg_5": self.loadavg_5,
            "loadavg_15": self.loadavg_15,
            "cpu_usage": round(self.cpu_usage, 3),
            "memory_total": self.memory_total,
            "memory_available": self.memory_available,
            "memory_used": self.memory_used,
            "sampled_at": self.sampled_at,
        }


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _parse_meminfo(proc_root: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in (proc_root / "meminfo").read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.strip().split()
        amount = int(parts[0]) if parts else 0
        unit = parts[1] if len(parts) > 1 else ""
        if unit == "kB":
            amount *= 1024
        result[key.strip()] = amount
    return result


def _read_cpu_sample(proc_root: Path) -> HostCpuSample:
    cpu_line = (proc_root / "stat").read_text(encoding="utf-8", errors="replace").splitlines()[0]
    fields = [int(value) for value in cpu_line.split()[1:]]
    idle_ticks = fields[3] + (fields[4] if len(fields) > 4 else 0)
    total_ticks = sum(fields)
    return HostCpuSample(idle_ticks=idle_ticks, total_ticks=total_ticks)


def _calculate_cpu_usage(
    current_sample: HostCpuSample,
    previous_sample: HostCpuSample | None,
) -> float:
    if previous_sample is None:
        return 0.0
    idle_delta = current_sample.idle_ticks - previous_sample.idle_ticks
    total_delta = current_sample.total_ticks - previous_sample.total_ticks
    if total_delta <= 0:
        return 0.0
    return max(0.0, min(100.0, (1.0 - (idle_delta / total_delta)) * 100.0))


class HostSnapshotCollector:
    def __init__(self, *, proc_root: str | Path = "/proc") -> None:
        self.proc_root = Path(proc_root)

    def collect(
        self,
        *,
        occurred_at: datetime,
        previous_cpu_sample: HostCpuSample | None = None,
    ) -> tuple[HostSnapshot, HostCpuSample]:
        current_cpu_sample = _read_cpu_sample(self.proc_root)
        meminfo = _parse_meminfo(self.proc_root)
        loadavg_parts = (self.proc_root / "loadavg").read_text(encoding="utf-8", errors="replace").split()
        uptime_seconds = float((self.proc_root / "uptime").read_text(encoding="utf-8", errors="replace").split()[0])
        boot_id = _read_text(self.proc_root / "sys" / "kernel" / "random" / "boot_id")

        memory_total = meminfo.get("MemTotal", 0)
        memory_available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        memory_used = max(0, memory_total - memory_available)

        snapshot = HostSnapshot(
            hostname=socket.gethostname(),
            boot_id=boot_id,
            uptime_seconds=uptime_seconds,
            loadavg_1=float(loadavg_parts[0]),
            loadavg_5=float(loadavg_parts[1]),
            loadavg_15=float(loadavg_parts[2]),
            cpu_usage=_calculate_cpu_usage(current_cpu_sample, previous_cpu_sample),
            memory_total=memory_total,
            memory_available=memory_available,
            memory_used=memory_used,
            sampled_at=occurred_at.isoformat(timespec="milliseconds"),
        )
        return snapshot, current_cpu_sample
