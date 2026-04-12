from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import AgentTarget


@dataclass(frozen=True)
class ProcessMatch:
    target_id: str
    pid: int
    name: str
    cmdline: str
    exe_path: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _read_cmdline(path: Path) -> str:
    raw = path.read_bytes()
    if not raw:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()


def _read_exe_path(path: Path) -> str:
    try:
        if path.is_symlink():
            return str(path.resolve(strict=True))
        if path.exists() and path.is_file():
            return _read_text(path)
    except OSError:
        return ""
    return ""


class ProcfsSelector:
    def __init__(self, *, proc_root: str | Path = "/proc") -> None:
        self.proc_root = Path(proc_root)

    def iter_pid_dirs(self) -> Iterable[Path]:
        if not self.proc_root.exists():
            return ()
        return sorted(
            (path for path in self.proc_root.iterdir() if path.is_dir() and path.name.isdigit()),
            key=lambda path: int(path.name),
        )

    def read_process(self, pid_dir: Path) -> ProcessMatch | None:
        try:
            pid = int(pid_dir.name)
            name = _read_text(pid_dir / "comm")
            cmdline = _read_cmdline(pid_dir / "cmdline")
            exe_path = _read_exe_path(pid_dir / "exe")
        except (FileNotFoundError, PermissionError, ValueError):
            return None

        return ProcessMatch(
            target_id="",
            pid=pid,
            name=name,
            cmdline=cmdline,
            exe_path=exe_path,
        )

    def matches_target(self, process: ProcessMatch, target: AgentTarget) -> bool:
        if target.pid is not None and process.pid != target.pid:
            return False
        if target.process_name is not None and process.name != target.process_name:
            return False
        if target.executable_path is not None and process.exe_path != target.executable_path:
            return False
        if target.command_line_regex is not None and not re.search(target.command_line_regex, process.cmdline):
            return False
        return True

    def discover(self, target: AgentTarget) -> list[ProcessMatch]:
        matches: list[ProcessMatch] = []
        for pid_dir in self.iter_pid_dirs():
            process = self.read_process(pid_dir)
            if process is None:
                continue
            if not self.matches_target(process, target):
                continue
            matches.append(
                ProcessMatch(
                    target_id=target.target_id,
                    pid=process.pid,
                    name=process.name,
                    cmdline=process.cmdline,
                    exe_path=process.exe_path,
                )
            )

        if target.mode == "single":
            return matches[:1]
        return matches
