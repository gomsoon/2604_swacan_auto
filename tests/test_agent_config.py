from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from agent.config import AgentConfigError, load_config


def write_config(tmp_path: Path, body: str) -> Path:
    config_path = tmp_path / "agent.toml"
    config_path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
    return config_path


def test_load_config_reads_valid_toml(tmp_path) -> None:
    config_path = write_config(
        tmp_path,
        """
        [agent]
        agent_id = "agent_local"
        token = "dev-agent-token"
        debug_mode = true

        [backend]
        endpoint = "https://backend.example.com/api/agents/ingest"

        [intervals]
        heartbeat_seconds = 5
        snapshot_seconds = 10
        flush_seconds = 2
        retry_backoff_seconds = 15

        [[targets]]
        target_id = "app_main"
        mode = "single"
        process_name = "python"

        [[targets]]
        target_id = "worker_pool"
        mode = "multi"
        command_line_regex = "worker"
        """,
    )

    config = load_config(config_path)

    assert config.agent_id == "agent_local"
    assert config.backend_endpoint == "https://backend.example.com/api/agents/ingest"
    assert config.debug_mode is True
    assert config.storage_path.name == "agent.agent.sqlite3"
    assert config.storage.keep_acked_rows == 500
    assert config.storage.cleanup_batch_size == 250
    assert config.storage.pending_warning_rows == 1000
    assert config.intervals.heartbeat_seconds == 5
    assert len(config.targets) == 2
    assert config.targets[0].process_name == "python"
    assert config.targets[1].mode == "multi"


def test_load_config_rejects_target_without_selector(tmp_path) -> None:
    config_path = write_config(
        tmp_path,
        """
        [agent]
        agent_id = "agent_local"
        token = "dev-agent-token"

        [backend]
        endpoint = "https://backend.example.com/api/agents/ingest"

        [intervals]
        heartbeat_seconds = 5
        snapshot_seconds = 5
        flush_seconds = 2
        retry_backoff_seconds = 10

        [[targets]]
        target_id = "app_main"
        """,
    )

    with pytest.raises(AgentConfigError, match="at least one selector"):
        load_config(config_path)


def test_load_config_rejects_invalid_intervals(tmp_path) -> None:
    config_path = write_config(
        tmp_path,
        """
        [agent]
        agent_id = "agent_local"
        token = "dev-agent-token"

        [backend]
        endpoint = "https://backend.example.com/api/agents/ingest"

        [intervals]
        heartbeat_seconds = 0
        snapshot_seconds = 5
        flush_seconds = 2
        retry_backoff_seconds = 10

        [[targets]]
        target_id = "app_main"
        process_name = "python"
        """,
    )

    with pytest.raises(AgentConfigError, match="heartbeat_seconds"):
        load_config(config_path)


def test_load_config_resolves_relative_storage_path(tmp_path) -> None:
    config_path = write_config(
        tmp_path,
        """
        [agent]
        agent_id = "agent_local"
        token = "dev-agent-token"

        [backend]
        endpoint = "https://backend.example.com/api/agents/ingest"

        [storage]
        database_path = "runtime/agent-outbox.sqlite3"

        [intervals]
        heartbeat_seconds = 5
        snapshot_seconds = 5
        flush_seconds = 2
        retry_backoff_seconds = 10

        [[targets]]
        target_id = "app_main"
        process_name = "python"
        """,
    )

    config = load_config(config_path)

    assert config.storage_path == (config_path.parent / "runtime" / "agent-outbox.sqlite3").resolve()


def test_load_config_reads_storage_policy_values(tmp_path) -> None:
    config_path = write_config(
        tmp_path,
        """
        [agent]
        agent_id = "agent_local"
        token = "dev-agent-token"

        [backend]
        endpoint = "https://backend.example.com/api/agents/ingest"

        [storage]
        database_path = "runtime/agent-outbox.sqlite3"
        keep_acked_rows = 50
        cleanup_batch_size = 20
        pending_warning_rows = 75

        [intervals]
        heartbeat_seconds = 5
        snapshot_seconds = 5
        flush_seconds = 2
        retry_backoff_seconds = 10

        [[targets]]
        target_id = "app_main"
        process_name = "python"
        """,
    )

    config = load_config(config_path)

    assert config.storage.keep_acked_rows == 50
    assert config.storage.cleanup_batch_size == 20
    assert config.storage.pending_warning_rows == 75
