"""`handoff completion bash|zsh`: a tab-completion script for the command names."""

from __future__ import annotations

import argparse
from typing import Any

_ZSH = """#compdef handoff
_handoff() {{
  local -a commands
  commands=({names})
  _describe 'command' commands
}}
compdef _handoff handoff
"""
_BASH = """_handoff() {{
  local cur="${{COMP_WORDS[COMP_CWORD]}}"
  if [ "$COMP_CWORD" -eq 1 ]; then
    COMPREPLY=( $(compgen -W "{names}" -- "$cur") )
  fi
}}
complete -F _handoff handoff
"""


def script(shell: str, names: list[str]) -> str:
    """The completion script for `shell` ('bash' or 'zsh')."""
    template = _ZSH if shell == "zsh" else _BASH
    return template.format(names=" ".join(names))


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("completion", help="tab completion for bash or zsh")
    p.add_argument("shell", choices=("bash", "zsh"), help='e.g. eval "$(handoff completion zsh)"')
    p.set_defaults(run=run, command_names=lambda: list(commands.choices))


def run(args: argparse.Namespace) -> int:
    """Print the script; add it to your shell profile to keep it."""
    print(script(args.shell, args.command_names()), end="")
    return 0
