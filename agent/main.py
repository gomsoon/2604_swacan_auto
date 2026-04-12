from __future__ import annotations

import argparse
from collections.abc import Sequence

from .config import AgentConfigError, load_config
from .runner import LoggingRunnerServices, AgentRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Linux monitoring agent skeleton runner")
    parser.add_argument("--config", required=True, help="agent TOML config path")
    parser.add_argument("--once", action="store_true", help="run a single scheduler cycle and exit")
    parser.add_argument("--cycles", type=int, default=None, help="run a fixed number of cycles and exit")
    parser.add_argument("--dump-config", action="store_true", help="print a sanitized config summary and exit")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except AgentConfigError as exc:
        parser.exit(2, f"config error: {exc}\n")

    if args.dump_config:
        print(
            f"agent_id={config.agent_id} endpoint={config.backend_endpoint} "
            f"targets={len(config.targets)} debug_mode={config.debug_mode}"
        )
        return 0

    services = LoggingRunnerServices()
    runner = AgentRunner(config, services)

    if args.once:
        runner.run_cycle()
    else:
        max_cycles = args.cycles if args.cycles is not None else 1
        runner.run_forever(max_cycles=max_cycles)

    for action_name, occurred_at in services.actions:
        print(f"{occurred_at} {action_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
