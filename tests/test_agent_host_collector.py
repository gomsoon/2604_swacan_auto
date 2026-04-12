from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agent.host_collector import HostCpuSample, HostSnapshotCollector


def make_host_proc_fixture(
    proc_root: Path,
    *,
    cpu_fields: list[int],
    loadavg: tuple[float, float, float],
    uptime_seconds: float,
    mem_total_kb: int,
    mem_available_kb: int,
    boot_id: str = "boot-test-001",
) -> None:
    proc_root.mkdir(parents=True, exist_ok=True)
    (proc_root / "sys" / "kernel" / "random").mkdir(parents=True, exist_ok=True)
    (proc_root / "stat").write_text(
        "cpu  " + " ".join(str(value) for value in cpu_fields) + "\n",
        encoding="utf-8",
    )
    (proc_root / "loadavg").write_text(
        f"{loadavg[0]:.2f} {loadavg[1]:.2f} {loadavg[2]:.2f} 1/200 9999\n",
        encoding="utf-8",
    )
    (proc_root / "uptime").write_text(f"{uptime_seconds} 0.0\n", encoding="utf-8")
    (proc_root / "meminfo").write_text(
        "\n".join(
            [
                f"MemTotal:       {mem_total_kb} kB",
                f"MemAvailable:   {mem_available_kb} kB",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (proc_root / "sys" / "kernel" / "random" / "boot_id").write_text(boot_id + "\n", encoding="utf-8")


def test_host_collector_reads_stat_loadavg_meminfo(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    make_host_proc_fixture(
        proc_root,
        cpu_fields=[100, 20, 30, 400, 10, 0, 0, 0, 0, 0],
        loadavg=(0.15, 0.25, 0.35),
        uptime_seconds=321.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 3,
    )

    collector = HostSnapshotCollector(proc_root=proc_root)
    snapshot, cpu_sample = collector.collect(
        occurred_at=datetime(2026, 4, 13, 10, 30, 0, tzinfo=timezone.utc)
    )

    assert snapshot.boot_id == "boot-test-001"
    assert snapshot.uptime_seconds == 321.5
    assert snapshot.loadavg_1 == 0.15
    assert snapshot.loadavg_5 == 0.25
    assert snapshot.loadavg_15 == 0.35
    assert snapshot.memory_total == 1024 * 8 * 1024
    assert snapshot.memory_available == 1024 * 3 * 1024
    assert snapshot.memory_used == 1024 * 5 * 1024
    assert snapshot.cpu_usage == 0.0
    assert cpu_sample == HostCpuSample(idle_ticks=410, total_ticks=560)


def test_host_collector_computes_cpu_usage_from_previous_sample(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    collector = HostSnapshotCollector(proc_root=proc_root)
    make_host_proc_fixture(
        proc_root,
        cpu_fields=[100, 20, 30, 400, 10, 0, 0, 0, 0, 0],
        loadavg=(0.15, 0.25, 0.35),
        uptime_seconds=321.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 3,
    )
    _first_snapshot, first_sample = collector.collect(
        occurred_at=datetime(2026, 4, 13, 10, 30, 0, tzinfo=timezone.utc)
    )

    make_host_proc_fixture(
        proc_root,
        cpu_fields=[130, 30, 40, 420, 10, 0, 0, 0, 0, 0],
        loadavg=(0.20, 0.30, 0.40),
        uptime_seconds=326.5,
        mem_total_kb=1024 * 8,
        mem_available_kb=1024 * 2,
    )
    second_snapshot, second_sample = collector.collect(
        occurred_at=datetime(2026, 4, 13, 10, 30, 5, tzinfo=timezone.utc),
        previous_cpu_sample=first_sample,
    )

    assert round(second_snapshot.cpu_usage, 3) == 71.429
    assert second_sample == HostCpuSample(idle_ticks=430, total_ticks=630)
