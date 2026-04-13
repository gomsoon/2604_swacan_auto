from __future__ import annotations

import argparse
from collections.abc import Sequence

from .config import AgentConfigError, load_config
from .runner import AgentRunner
from .services import AgentRuntimeServices
from .storage import AgentStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Linux monitoring agent skeleton runner")
    parser.add_argument("--config", required=True, help="agent TOML config path")
    parser.add_argument("--once", action="store_true", help="run a single scheduler cycle and exit")
    parser.add_argument("--cycles", type=int, default=None, help="run a fixed number of cycles and exit")
    parser.add_argument("--dump-config", action="store_true", help="print a sanitized config summary and exit")
    return parser


def build_runtime_services(config):
    storage = AgentStorage(config.storage_path)
    storage.initialize()
    return AgentRuntimeServices(config, storage)


def print_service_summary(services) -> None:
    actions = getattr(services, "actions", None)
    if isinstance(actions, list):
        for action_name, occurred_at in actions:
            print(f"{occurred_at} {action_name}")
        return

    last_cycle = getattr(services, "last_cycle", None)
    if last_cycle is None:
        return

    print(
        "heartbeat_seq={heartbeat_seq} host_snapshot_seq={host_snapshot_seq} "
        "process_snapshot_count={process_count} flush_sent_count={flush_sent_count} "
        "flush_ack_seq={flush_ack_seq} purged_acked_count={purged_acked_count} "
        "backend_status={backend_status} flush_error={flush_error}".format(
            heartbeat_seq=last_cycle.heartbeat_seq,
            host_snapshot_seq=last_cycle.host_snapshot_seq,
            process_count=len(last_cycle.process_snapshot_seqs),
            flush_sent_count=last_cycle.flush_sent_count,
            flush_ack_seq=last_cycle.flush_ack_seq,
            purged_acked_count=last_cycle.purged_acked_count,
            backend_status=getattr(services, "backend_connection_status", "unknown"),
            flush_error=last_cycle.flush_error or "-",
        )
    )


def main(argv: Sequence[str] | None = None, *, services_factory=build_runtime_services) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except AgentConfigError as exc:
        parser.exit(2, f"config error: {exc}\n")

    if args.dump_config:
        print(
            f"agent_id={config.agent_id} endpoint={config.backend_endpoint} "
            f"targets={len(config.targets)} debug_mode={config.debug_mode} "
            f"storage_path={config.storage_path} keep_acked_rows={config.storage.keep_acked_rows}"
        )
        return 0

    services = services_factory(config)
    runner = AgentRunner(config, services)

    if args.once:
        runner.run_cycle()
    else:
        max_cycles = args.cycles if args.cycles is not None else 1
        runner.run_forever(max_cycles=max_cycles)

    print_service_summary(services)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
