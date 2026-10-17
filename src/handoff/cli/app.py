"""`handoff`: parse the subcommand and hand over to its module. No logic of its own."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from handoff.cli import (
    ask,
    completion,
    conventions_cmd,
    coordinator_cmd,
    dashboard_cmd,
    demo,
    doctor,
    home,
    init_cmd,
    insights_cmd,
    install_cmd,
    knowledge_cmd,
    log_cmd,
    memory_cmd,
    open_cmd,
    send,
    status,
    timeline_cmd,
    watch,
)
from handoff.cli.parser import HandoffParser

COMMANDS = (
    init_cmd,
    install_cmd,
    status,
    log_cmd,
    send,
    ask,
    insights_cmd,
    watch,
    dashboard_cmd,
    open_cmd,
    coordinator_cmd,
    demo,
    knowledge_cmd,
    memory_cmd,
    conventions_cmd,
    timeline_cmd,
    doctor,
    completion,
)


def _version() -> str:
    try:
        return version("handoff")
    except PackageNotFoundError:  # running from a source tree that was never installed
        return "0.1.0"


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand (or show the home screen); returns its exit code."""
    parser = HandoffParser(
        prog="handoff",
        description="Let parallel Claude Code sessions share intent.",
        epilog="quick start:  handoff init   then   handoff dashboard   (or just: handoff demo)",
    )
    parser.add_argument("--version", action="version", version=f"handoff {_version()}")
    commands = parser.add_subparsers(
        dest="command", metavar="<command>", parser_class=HandoffParser
    )
    for command in COMMANDS:
        command.add_parser(commands)
    args = parser.parse_args(argv)
    if args.command is None:
        return home.show()
    result: int = args.run(args)
    return result
