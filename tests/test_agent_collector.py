from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent.collector import CpuSample, ProcessSnapshotCollector
from agent.selector import ProcessMatch


def make_proc_snapshot_fixture(
    proc_root: Path,
    *,
    pid: int,
    comm: str = "python",
    cmdline: str = "python app.py",
    exe_path: str = "/usr/bin/python",
    proc_state: str = "S",
    ppid: int = 1,
    utime: int = 100,
    stime: int = 50,
    start_ticks: int = 1000,
    vm_rss_kb: int = 20480,
    vm_size_kb: int = 40960,
    threads: int = 4,
    read_bytes: int = 1000,
    write_bytes: int = 2000,
    system_ticks: int = 10000,
    uptime_seconds: float = 120.0,
) -> None:
    proc_root.mkdir(parents=True, exist_ok=True)
    (proc_root / "stat").write_text(f"cpu  {system_ticks} 0 0 0 0 0 0 0 0 0\n", encoding="utf-8")
    (proc_root / "uptime").write_text(f"{uptime_seconds} 0.0\n", encoding="utf-8")

    pid_dir = proc_root / str(pid)
    (pid_dir / "fd").mkdir(parents=True, exist_ok=True)
    (pid_dir / "fd" / "0").write_text("", encoding="utf-8")
    (pid_dir / "fd" / "1").write_text("", encoding="utf-8")
    (pid_dir / "comm").write_text(comm + "\n", encoding="utf-8")
    (pid_dir / "cmdline").write_bytes(b"\x00".join(part.encode("utf-8") for part in cmdline.split(" ")))
    (pid_dir / "exe").write_text(exe_path + "\n", encoding="utf-8")
    (pid_dir / "status").write_text(
        "\n".join(
            [
                "Name:\tpython",
                f"VmRSS:\t{vm_rss_kb} kB",
                f"VmSize:\t{vm_size_kb} kB",
                f"Threads:\t{threads}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (pid_dir / "io").write_text(
        "\n".join(
            [
                f"read_bytes: {read_bytes}",
                f"write_bytes: {write_bytes}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    stat_suffix_fields = [
        proc_state,  # state
        str(ppid),  # ppid
        "0",  # pgrp
        "0",  # session
        "0",  # tty_nr
        "0",  # tpgid
        "0",  # flags
        "0",  # minflt
        "0",  # cminflt
        "0",  # majflt
        "0",  # cmajflt
        str(utime),  # utime
        str(stime),  # stime
        "0",  # cutime
        "0",  # cstime
        "0",  # priority
        "0",  # nice
        str(threads),  # num_threads
        "0",  # itrealvalue
        str(start_ticks),  # starttime
        str(vm_size_kb * 1024),  # vsize
        str(vm_rss_kb),  # rss in pages-like placeholder for tests
    ]
    (pid_dir / "stat").write_text(
        f"{pid} ({comm}) " + " ".join(stat_suffix_fields) + "\n",
        encoding="utf-8",
    )


def test_collector_reads_procfs_snapshot(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    make_proc_snapshot_fixture(proc_root, pid=1234)
    collector = ProcessSnapshotCollector(proc_root=proc_root, clock_ticks=100)
    match = ProcessMatch(
        target_id="app_main",
        pid=1234,
        name="python",
        cmdline="python app.py",
        exe_path="/usr/bin/python",
    )

    snapshot, cpu_sample = collector.collect(
        match,
        occurred_at=datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc),
    )

    assert snapshot.target_id == "app_main"
    assert snapshot.pid == 1234
    assert snapshot.status == "up"
    assert snapshot.state == "sleeping"
    assert snapshot.memory_rss == 20480 * 1024
    assert snapshot.memory_vms == 40960 * 1024
    assert snapshot.fd_count == 2
    assert snapshot.io_read_bytes == 1000
    assert snapshot.io_write_bytes == 2000
    assert snapshot.cpu_usage == 0.0
    assert cpu_sample == CpuSample(process_ticks=150, system_ticks=10000)


def test_collector_computes_cpu_usage_from_previous_sample(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    make_proc_snapshot_fixture(proc_root, pid=1234, utime=100, stime=50, system_ticks=10000)
    collector = ProcessSnapshotCollector(proc_root=proc_root, clock_ticks=100)
    match = ProcessMatch(
        target_id="app_main",
        pid=1234,
        name="python",
        cmdline="python app.py",
        exe_path="/usr/bin/python",
    )

    occurred_at = datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc)
    _first_snapshot, first_sample = collector.collect(match, occurred_at=occurred_at)

    make_proc_snapshot_fixture(proc_root, pid=1234, utime=130, stime=70, system_ticks=10200)
    second_snapshot, second_sample = collector.collect(
        match,
        occurred_at=occurred_at + timedelta(seconds=2),
        previous_cpu_sample=first_sample,
    )

    assert round(second_snapshot.cpu_usage, 3) == 25.0
    assert second_sample == CpuSample(process_ticks=200, system_ticks=10200)
