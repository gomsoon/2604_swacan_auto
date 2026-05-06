from __future__ import annotations

from pathlib import Path

from agent.config import AgentTarget
from agent.selector import ProcfsSelector, _read_cmdline, _read_exe_path


def make_process(
    proc_root: Path,
    *,
    pid: int,
    name: str,
    cmdline: str,
    exe_path: str,
) -> None:
    pid_dir = proc_root / str(pid)
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / "comm").write_text(name + "\n", encoding="utf-8")
    (pid_dir / "cmdline").write_bytes(b"\x00".join(part.encode("utf-8") for part in cmdline.split(" ")))
    (pid_dir / "exe").write_text(exe_path + "\n", encoding="utf-8")


def test_selector_matches_process_name_in_single_mode(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    make_process(proc_root, pid=111, name="python", cmdline="python app.py", exe_path="/usr/bin/python")
    make_process(proc_root, pid=222, name="python", cmdline="python worker.py", exe_path="/usr/bin/python")

    selector = ProcfsSelector(proc_root=proc_root)
    target = AgentTarget(
        target_id="app_main",
        mode="single",
        process_name="python",
        command_line_regex=None,
        executable_path=None,
        pid=None,
    )

    matches = selector.discover(target)

    assert [match.pid for match in matches] == [111]
    assert matches[0].target_id == "app_main"


def test_selector_matches_command_line_regex_in_multi_mode(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    make_process(proc_root, pid=111, name="python", cmdline="python app.py", exe_path="/usr/bin/python")
    make_process(proc_root, pid=222, name="python", cmdline="python worker.py --role worker", exe_path="/usr/bin/python")
    make_process(proc_root, pid=333, name="python", cmdline="python worker.py --role worker", exe_path="/opt/worker/python")

    selector = ProcfsSelector(proc_root=proc_root)
    target = AgentTarget(
        target_id="worker_pool",
        mode="multi",
        process_name="python",
        command_line_regex="worker",
        executable_path=None,
        pid=None,
    )

    matches = selector.discover(target)

    assert [match.pid for match in matches] == [222, 333]


def test_selector_can_match_exact_pid(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    make_process(proc_root, pid=111, name="python", cmdline="python app.py", exe_path="/usr/bin/python")

    selector = ProcfsSelector(proc_root=proc_root)
    target = AgentTarget(
        target_id="app_main",
        mode="single",
        process_name=None,
        command_line_regex=None,
        executable_path=None,
        pid=111,
    )

    matches = selector.discover(target)

    assert len(matches) == 1
    assert matches[0].pid == 111


def test_selector_can_discover_multiple_targets_in_single_scan(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    make_process(proc_root, pid=111, name="python", cmdline="python app.py", exe_path="/usr/bin/python")
    make_process(proc_root, pid=222, name="python", cmdline="python worker.py --role worker", exe_path="/usr/bin/python")
    make_process(proc_root, pid=333, name="nginx", cmdline="nginx: master process", exe_path="/usr/sbin/nginx")

    selector = ProcfsSelector(proc_root=proc_root)
    targets = [
        AgentTarget(
            target_id="app_main",
            mode="single",
            process_name="python",
            command_line_regex="app.py",
            executable_path=None,
            pid=None,
        ),
        AgentTarget(
            target_id="worker_pool",
            mode="multi",
            process_name="python",
            command_line_regex="worker",
            executable_path=None,
            pid=None,
        ),
        AgentTarget(
            target_id="nginx_master",
            mode="single",
            process_name="nginx",
            command_line_regex=None,
            executable_path=None,
            pid=None,
        ),
    ]

    matches = selector.discover_targets(targets)

    assert [match.pid for match in matches["app_main"]] == [111]
    assert [match.pid for match in matches["worker_pool"]] == [222]
    assert [match.pid for match in matches["nginx_master"]] == [333]


def test_selector_process_name_only_match_does_not_require_cmdline_or_exe(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    pid_dir = proc_root / "111"
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / "comm").write_text("python\n", encoding="utf-8")

    selector = ProcfsSelector(proc_root=proc_root)
    target = AgentTarget(
        target_id="app_main",
        mode="single",
        process_name="python",
        command_line_regex=None,
        executable_path=None,
        pid=None,
    )

    matches = selector.discover(target)

    assert len(matches) == 1
    assert matches[0].pid == 111
    assert matches[0].cmdline == ""
    assert matches[0].exe_path == ""


def test_selector_iter_pid_dirs_returns_empty_when_proc_root_is_missing(tmp_path) -> None:
    selector = ProcfsSelector(proc_root=tmp_path / "missing-proc")

    assert list(selector.iter_pid_dirs()) == []


def test_selector_read_process_base_returns_none_when_comm_file_is_missing(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    pid_dir = proc_root / "111"
    pid_dir.mkdir(parents=True)

    selector = ProcfsSelector(proc_root=proc_root)

    assert selector.read_process_base(pid_dir) is None


def test_read_cmdline_returns_empty_string_for_empty_bytes(tmp_path) -> None:
    cmdline_path = tmp_path / "cmdline"
    cmdline_path.write_bytes(b"")

    assert _read_cmdline(cmdline_path) == ""


def test_read_exe_path_reads_plain_text_fallback_file(tmp_path) -> None:
    exe_path = tmp_path / "exe"
    exe_path.write_text("/usr/bin/python\n", encoding="utf-8")

    assert _read_exe_path(exe_path) == "/usr/bin/python"


def test_read_exe_path_returns_empty_string_on_oserror(tmp_path, monkeypatch) -> None:
    exe_path = tmp_path / "exe"
    exe_path.write_text("/usr/bin/python\n", encoding="utf-8")

    def raise_oserror(_self) -> bool:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "is_symlink", raise_oserror)

    assert _read_exe_path(exe_path) == ""


def test_selector_filters_by_executable_path(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    make_process(proc_root, pid=111, name="python", cmdline="python app.py", exe_path="/usr/bin/python")
    make_process(proc_root, pid=222, name="python", cmdline="python app.py", exe_path="/opt/python")

    selector = ProcfsSelector(proc_root=proc_root)
    target = AgentTarget(
        target_id="app_main",
        mode="multi",
        process_name="python",
        command_line_regex=None,
        executable_path="/opt/python",
        pid=None,
    )

    matches = selector.discover(target)

    assert [match.pid for match in matches] == [222]


def test_selector_skips_process_when_cmdline_is_required_but_missing(tmp_path) -> None:
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    pid_dir = proc_root / "111"
    pid_dir.mkdir(parents=True)
    (pid_dir / "comm").write_text("python\n", encoding="utf-8")

    selector = ProcfsSelector(proc_root=proc_root)
    target = AgentTarget(
        target_id="worker_pool",
        mode="multi",
        process_name="python",
        command_line_regex="worker",
        executable_path=None,
        pid=None,
    )

    matches = selector.discover(target)

    assert matches == []
