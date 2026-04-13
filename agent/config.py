from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


class AgentConfigError(ValueError):
    pass


SelectorMode = Literal["single", "multi"]


@dataclass(frozen=True)
class AgentIntervals:
    heartbeat_seconds: int
    snapshot_seconds: int
    flush_seconds: int
    retry_backoff_seconds: int


@dataclass(frozen=True)
class AgentTarget:
    target_id: str
    mode: SelectorMode
    process_name: str | None
    command_line_regex: str | None
    executable_path: str | None
    pid: int | None


@dataclass(frozen=True)
class AgentConfig:
    config_path: Path
    storage_path: Path
    agent_id: str
    backend_endpoint: str
    token: str
    debug_mode: bool
    intervals: AgentIntervals
    targets: tuple[AgentTarget, ...]


def _require_section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    if not isinstance(value, dict):
        raise AgentConfigError(f"'{name}' section is required")
    return value


def _require_text(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AgentConfigError(f"'{key}' must be a non-empty string")
    return os.path.expandvars(value.strip())


def _require_positive_int(section: dict[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or value <= 0:
        raise AgentConfigError(f"'{key}' must be a positive integer")
    return value


def _load_intervals(section: dict[str, Any]) -> AgentIntervals:
    return AgentIntervals(
        heartbeat_seconds=_require_positive_int(section, "heartbeat_seconds"),
        snapshot_seconds=_require_positive_int(section, "snapshot_seconds"),
        flush_seconds=_require_positive_int(section, "flush_seconds"),
        retry_backoff_seconds=_require_positive_int(section, "retry_backoff_seconds"),
    )


def _load_target(raw_target: Any) -> AgentTarget:
    if not isinstance(raw_target, dict):
        raise AgentConfigError("each target must be an object")

    target_id = raw_target.get("target_id")
    if not isinstance(target_id, str) or not target_id.strip():
        raise AgentConfigError("'target_id' must be a non-empty string")

    raw_mode = raw_target.get("mode", "single")
    if raw_mode not in {"single", "multi"}:
        raise AgentConfigError("'mode' must be 'single' or 'multi'")

    process_name = raw_target.get("process_name")
    command_line_regex = raw_target.get("command_line_regex")
    executable_path = raw_target.get("executable_path")
    pid = raw_target.get("pid")

    if process_name is not None and (not isinstance(process_name, str) or not process_name.strip()):
        raise AgentConfigError("'process_name' must be a non-empty string when provided")
    if command_line_regex is not None and (
        not isinstance(command_line_regex, str) or not command_line_regex.strip()
    ):
        raise AgentConfigError("'command_line_regex' must be a non-empty string when provided")
    if executable_path is not None and (
        not isinstance(executable_path, str) or not executable_path.strip()
    ):
        raise AgentConfigError("'executable_path' must be a non-empty string when provided")
    if pid is not None and (not isinstance(pid, int) or pid <= 0):
        raise AgentConfigError("'pid' must be a positive integer when provided")

    if all(value is None for value in (process_name, command_line_regex, executable_path, pid)):
        raise AgentConfigError("at least one selector must be configured for each target")

    return AgentTarget(
        target_id=target_id.strip(),
        mode=raw_mode,
        process_name=process_name.strip() if isinstance(process_name, str) else None,
        command_line_regex=command_line_regex.strip() if isinstance(command_line_regex, str) else None,
        executable_path=executable_path.strip() if isinstance(executable_path, str) else None,
        pid=pid,
    )


def _resolve_storage_path(raw: dict[str, Any], config_path: Path) -> Path:
    storage_section = raw.get("storage", {})
    if storage_section is not None and not isinstance(storage_section, dict):
        raise AgentConfigError("'storage' section must be an object when provided")

    database_path = None if not isinstance(storage_section, dict) else storage_section.get("database_path")
    if database_path is None:
        return config_path.with_suffix(".agent.sqlite3")
    if not isinstance(database_path, str) or not database_path.strip():
        raise AgentConfigError("'storage.database_path' must be a non-empty string when provided")

    expanded = Path(os.path.expandvars(database_path.strip())).expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (config_path.parent / expanded).resolve()


def load_config(config_path: str | Path) -> AgentConfig:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise AgentConfigError(f"config file was not found: {path}")

    with path.open("rb") as file_obj:
        raw = tomllib.load(file_obj)

    agent_section = _require_section(raw, "agent")
    backend_section = _require_section(raw, "backend")
    intervals_section = _require_section(raw, "intervals")
    raw_targets = raw.get("targets")

    if not isinstance(raw_targets, list) or not raw_targets:
        raise AgentConfigError("'targets' must contain at least one target")

    targets = tuple(_load_target(raw_target) for raw_target in raw_targets)
    intervals = _load_intervals(intervals_section)

    debug_mode = agent_section.get("debug_mode", False)
    if not isinstance(debug_mode, bool):
        raise AgentConfigError("'debug_mode' must be a boolean")

    return AgentConfig(
        config_path=path,
        storage_path=_resolve_storage_path(raw, path),
        agent_id=_require_text(agent_section, "agent_id"),
        backend_endpoint=_require_text(backend_section, "endpoint"),
        token=_require_text(agent_section, "token"),
        debug_mode=debug_mode,
        intervals=intervals,
        targets=targets,
    )
