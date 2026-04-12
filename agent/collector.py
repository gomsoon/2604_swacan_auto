from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .selector import ProcessMatch


PROC_STATE_MAP = {
    "R": "running",
    "S": "sleeping",
    "D": "waiting",
    "Z": "zombie",
    "T": "stopped",
    "t": "stopped",
    "I": "idle",
}


@dataclass(frozen=True)
class CpuSample:
    process_ticks: int
    system_ticks: int


@dataclass(frozen=True)
class ProcessSnapshot:
    target_id: str
    pid: int
    ppid: int
    name: str
    exe_path: str
    cmdline: str
    status: str
    state: str
    os_state: str
    start_time: str
    uptime_seconds: float
    cpu_usage: float
    memory_rss: int
    memory_vms: int
    thread_count: int
    fd_count: int
    io_read_bytes: int
    io_write_bytes: int
    sampled_at: str

    def to_payload(self) -> dict[str, object]:
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "name": self.name,
            "exe_path": self.exe_path,
            "cmdline": self.cmdline,
            "status": self.status,
            "state": self.state,
            "os_state": self.os_state,
            "start_time": self.start_time,
            "uptime": round(self.uptime_seconds, 3),
            "cpu_usage": round(self.cpu_usage, 3),
            "memory_rss": self.memory_rss,
            "memory_vms": self.memory_vms,
            "thread_count": self.thread_count,
            "fd_count": self.fd_count,
            "io_read_bytes": self.io_read_bytes,
            "io_write_bytes": self.io_write_bytes,
            "sampled_at": self.sampled_at,
        }


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _read_proc_stat_fields(path: Path) -> list[str]:
    raw = _read_text(path)
    end_name = raw.rfind(")")
    if end_name == -1:
        raise ValueError("invalid /proc stat format")
    prefix = raw[: end_name + 1]
    suffix = raw[end_name + 2 :]
    pid_text, _name_text = prefix.split(" ", 1)
    return [pid_text] + suffix.split()


def _read_status_map(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def _parse_kb_field(status_map: dict[str, str], key: str) -> int:
    value = status_map.get(key, "0 kB").split()[0]
    return int(value) * 1024


def _parse_io_map(path: Path) -> dict[str, int]:
    io_map: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        io_map[key.strip()] = int(value.strip())
    return io_map


def _read_system_cpu_ticks(proc_root: Path) -> int:
    cpu_line = (proc_root / "stat").read_text(encoding="utf-8", errors="replace").splitlines()[0]
    parts = cpu_line.split()[1:]
    return sum(int(part) for part in parts)


def _read_uptime_seconds(proc_root: Path) -> float:
    return float((proc_root / "uptime").read_text(encoding="utf-8", errors="replace").split()[0])


class ProcessSnapshotCollector:
    def __init__(
        self,
        *,
        proc_root: str | Path = "/proc",
        clock_ticks: int = 100,
    ) -> None:
        self.proc_root = Path(proc_root)
        self.clock_ticks = clock_ticks

    def collect(
        self,
        process: ProcessMatch,
        *,
        occurred_at: datetime,
        previous_cpu_sample: CpuSample | None = None,
    ) -> tuple[ProcessSnapshot, CpuSample]:
        pid_dir = self.proc_root / str(process.pid)
        stat_fields = _read_proc_stat_fields(pid_dir / "stat")
        status_map = _read_status_map(pid_dir / "status")
        io_map = _parse_io_map(pid_dir / "io")

        ppid = int(stat_fields[2])
        proc_state_code = stat_fields[1]
        utime = int(stat_fields[12])
        stime = int(stat_fields[13])
        process_ticks = utime + stime
        start_ticks = int(stat_fields[20])
        system_ticks = _read_system_cpu_ticks(self.proc_root)
        uptime_seconds = max(0.0, _read_uptime_seconds(self.proc_root) - (start_ticks / self.clock_ticks))
        cpu_sample = CpuSample(process_ticks=process_ticks, system_ticks=system_ticks)

        cpu_usage = 0.0
        if previous_cpu_sample is not None:
            process_delta = process_ticks - previous_cpu_sample.process_ticks
            system_delta = system_ticks - previous_cpu_sample.system_ticks
            if process_delta > 0 and system_delta > 0:
                cpu_usage = (process_delta / system_delta) * 100.0

        state_name = PROC_STATE_MAP.get(proc_state_code, "unknown")
        start_time = occurred_at.isoformat(timespec="milliseconds")
        if uptime_seconds >= 0:
            start_datetime = occurred_at.timestamp() - uptime_seconds
            start_time = datetime.fromtimestamp(
                start_datetime, tz=occurred_at.tzinfo
            ).isoformat(timespec="milliseconds")

        snapshot = ProcessSnapshot(
            target_id=process.target_id,
            pid=process.pid,
            ppid=ppid,
            name=process.name,
            exe_path=process.exe_path,
            cmdline=process.cmdline,
            status="up",
            state=state_name,
            os_state=proc_state_code,
            start_time=start_time,
            uptime_seconds=uptime_seconds,
            cpu_usage=cpu_usage,
            memory_rss=_parse_kb_field(status_map, "VmRSS"),
            memory_vms=_parse_kb_field(status_map, "VmSize"),
            thread_count=int(status_map.get("Threads", "0")),
            fd_count=len(list((pid_dir / "fd").iterdir())) if (pid_dir / "fd").exists() else 0,
            io_read_bytes=io_map.get("read_bytes", 0),
            io_write_bytes=io_map.get("write_bytes", 0),
            sampled_at=occurred_at.isoformat(timespec="milliseconds"),
        )
        return snapshot, cpu_sample
