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


@dataclass(frozen=True)
class _BaseProcess:
    pid: int
    name: str


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

    def read_process_base(self, pid_dir: Path) -> _BaseProcess | None:
        try:
            pid = int(pid_dir.name)
            name = _read_text(pid_dir / "comm")
        except (FileNotFoundError, PermissionError, ValueError):
            return None

        return _BaseProcess(
            pid=pid,
            name=name,
        )

    def _build_match(
        self,
        *,
        target_id: str,
        pid: int,
        name: str,
        pid_dir: Path,
        need_cmdline: bool,
        need_exe: bool,
    ) -> ProcessMatch | None:
        try:
            cmdline = _read_cmdline(pid_dir / "cmdline") if need_cmdline else ""
            exe_path = _read_exe_path(pid_dir / "exe") if need_exe else ""
        except (FileNotFoundError, PermissionError, ValueError):
            return None

        return ProcessMatch(
            target_id=target_id,
            pid=pid,
            name=name,
            cmdline=cmdline,
            exe_path=exe_path,
        )

    def _matches_target(self, process: ProcessMatch, target: AgentTarget) -> bool:
        if target.pid is not None and process.pid != target.pid:
            return False
        if target.process_name is not None and process.name != target.process_name:
            return False
        if target.executable_path is not None and process.exe_path != target.executable_path:
            return False
        if target.command_line_regex is not None and not re.search(target.command_line_regex, process.cmdline):
            return False
        return True

    def discover_targets(self, targets: Iterable[AgentTarget]) -> dict[str, list[ProcessMatch]]:
        target_list = list(targets)
        matches_by_target: dict[str, list[ProcessMatch]] = {
            target.target_id: [] for target in target_list
        }
        if not target_list:
            return matches_by_target

        for pid_dir in self.iter_pid_dirs():
            base = self.read_process_base(pid_dir)
            if base is None:
                continue

            candidate_targets = [
                target
                for target in target_list
                if (target.pid is None or target.pid == base.pid)
                and (target.process_name is None or target.process_name == base.name)
            ]
            if not candidate_targets:
                continue

            need_exe = any(target.executable_path is not None for target in candidate_targets)
            preliminary_match = self._build_match(
                target_id="",
                pid=base.pid,
                name=base.name,
                pid_dir=pid_dir,
                need_cmdline=False,
                need_exe=need_exe,
            )
            if preliminary_match is None:
                continue

            candidate_targets = [
                target
                for target in candidate_targets
                if target.executable_path is None or target.executable_path == preliminary_match.exe_path
            ]
            if not candidate_targets:
                continue

            need_cmdline = any(target.command_line_regex is not None for target in candidate_targets)
            process_match = preliminary_match
            if need_cmdline:
                process_match = self._build_match(
                    target_id="",
                    pid=base.pid,
                    name=base.name,
                    pid_dir=pid_dir,
                    need_cmdline=True,
                    need_exe=need_exe,
                )
                if process_match is None:
                    continue

            for target in candidate_targets:
                if not self._matches_target(process_match, target):
                    continue
                target_matches = matches_by_target[target.target_id]
                if target.mode == "single" and target_matches:
                    continue
                target_matches.append(
                    ProcessMatch(
                        target_id=target.target_id,
                        pid=process_match.pid,
                        name=process_match.name,
                        cmdline=process_match.cmdline,
                        exe_path=process_match.exe_path,
                    )
                )

        return matches_by_target

    def discover(self, target: AgentTarget) -> list[ProcessMatch]:
        return self.discover_targets([target]).get(target.target_id, [])
