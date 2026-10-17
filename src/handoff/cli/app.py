"""`handoff`: parse the subcommand and hand over to its module. No logic of its own."""

from __future__ import annotations

import argparse

from handoff.cli import (
    ask,
    demo,
    doctor,
    init_cmd,
    insights_cmd,
    install_cmd,
    knowledge_cmd,
    log_cmd,
    send,
    status,
    watch,
)

COMMANDS = (
    init_cmd,
    install_cmd,
    status,
    log_cmd,
    send,
    ask,
    insights_cmd,
    watch,
    demo,
    knowledge_cmd,
    doctor,
)


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand; returns its exit code."""
    parser = argparse.ArgumentParser(
        prog="handoff", description="Let parallel Claude Code sessions share intent."
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="<command>")
    for command in COMMANDS:
        command.add_parser(commands)
    args = parser.parse_args(argv)
    result: int = args.run(args)
    return result
