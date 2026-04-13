from __future__ import annotations

from pathlib import Path

from agent.config import AgentTarget
from agent.selector import ProcfsSelector


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
