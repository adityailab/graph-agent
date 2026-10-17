"""The `handoff` argument parser: a mistyped command gets a suggestion, not a wall of names."""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from typing import NoReturn

_CHOICE = re.compile(r"invalid choice: '([^']*)'")


class HandoffParser(argparse.ArgumentParser):
    """argparse with 'Did you mean ...?' for an unknown command."""

    def error(self, message: str) -> NoReturn:
        match = _CHOICE.search(message)
        names = [str(n) for a in self._actions for n in (a.choices or ())]
        if match and names:
            near = difflib.get_close_matches(match.group(1), names, n=1)
            hint = f" Did you mean '{near[0]}'?" if near else ""
            self.print_usage(sys.stderr)
            self.exit(
                2, f"handoff: unknown command '{match.group(1)}'.{hint} Run handoff for the list.\n"
            )
        super().error(message)
