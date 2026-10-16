# handoff: project rules

A shared FalkorDB graph that lets parallel Claude Code sessions read each other's
intent, message each other, and get stand-in answers. Hackathon entry for Graph
Hacks (WeMakeDevs × FalkorDB), deadline 18 October 2026, 11:59 PM IST.

- Design: `docs/superpowers/specs/2026-10-07-session-handoff-graph-design.md`
- Plan: `docs/superpowers/plans/2026-10-17-session-handoff-graph.md`
- Decision notebook: https://claude.ai/artifact/QwBH9hbLczwpurmB1WX7oY

## Commands

| Command | What it does |
|---|---|
| `make db-up` / `make db-down` | Start or stop FalkorDB in Docker (ports 6379 and 3000). |
| `make fmt` | Format and auto-fix lint. |
| `make check` | Format check, lint, type check, tests. Must pass before every commit. |
| `make test` | Tests only. Needs `make db-up`. |

Always run Python through `uv run`. Never `pip install` into the system Python.

## How we work: phases

Work happens in the phases listed in the plan. A phase is never started before
the previous one has passed its gate.

1. Create the branch `phase/<n>-<short-name>` from `main`.
2. Do the phase's tasks in order. Each task is test first: write the failing
   test, see it fail, write the code, see it pass.
3. One commit per task, after `make check` passes.
4. **Gate**, all required:
   - `make check` passes on the branch.
   - The phase's "show it working" step in the plan has been run and its output
     looked at.
   - The branch is merged into `main` with `git merge --no-ff`, and `main` is
     tagged `phase-<n>`.
   - The decision notebook gets any new decisions and a change-log row.
5. Only then start the next phase.

A bug found in an earlier phase's code is fixed on the current phase's branch,
with a test that reproduces it, in its own commit.

## Code standards

**Layout.** Source in `src/handoff/`, tests in `tests/` mirroring the source
layout. One responsibility per module. If a module passes about 250 lines, split
it.

| Package | Owns | Must not |
|---|---|---|
| `handoff.graph` | Every Cypher query, the schema, the record types | Read the environment, print, call models |
| `handoff.hooks` | The Claude Code hook protocol: stdin JSON in, exit code and stdout/stderr out | Contain Cypher |
| `handoff.mcp` | The MCP server and its tool functions | Contain Cypher |
| `handoff.standin` | The stand-in model call | Write Cypher directly |

**Python.** Python 3.12 or later. Type hints on every function, checked with
mypy in strict mode. Records crossing module boundaries are frozen dataclasses,
never loose dicts. `from __future__ import annotations` at the top of each
module.

**Style.** `ruff format`, line length 100. Names say what a thing is
(`pending_messages`, not `get_data`). Comments explain why, not what. A docstring
on every public function, one line unless it needs more.

**Cypher.** Values always go in as query parameters (`$name`), never through
string formatting. Writes that can be repeated use `MERGE` on a stable id.
Ids come from Claude Code where it gives one: `session_id` for sessions,
`prompt_id` for requests, `tool_use_id` for edits. Otherwise `handoff.ids.new_id()`.
Times are integer milliseconds since the epoch from `handoff.ids.now_ms()`.

**Errors.**
- Hooks fail open. The hook entry point catches every exception, logs it to
  `~/.handoff/logs/hooks.log`, and exits 0, so a broken hook never blocks a
  session. This is the only place a broad `except Exception` is allowed.
- Everywhere else, let exceptions rise. No bare `except:`. Catch only what you
  can handle, and say why in a comment.

**Output.** Hooks write to stdout only what Claude Code's protocol expects.
Diagnostics go through `logging`, never `print`. Text shown to Claude is written
as plain statements of fact, not commands.

**Secrets.** Never commit `.env` or keys. The project needs no API key: the
stand-in runs Claude Code headless on the person's own login. Text from prompts
and diffs passes through `handoff.redact` before it is written to the graph.

**Docker.** This machine runs Docker through Colima. If `docker ps` fails, run
`colima start`.

## Tests

- pytest. Graph tests run against the real FalkorDB from `make db-up`, each test
  on its own throwaway graph from the `graph` fixture. No mocking the database.
- The stand-in model is the one thing replaced by a fake in tests.
- Test names state the behaviour: `test_replayed_edit_is_not_duplicated`.
- Every bug fix starts with a test that fails because of the bug.

## Commits

Conventional Commits: `feat(graph): add why_file query`, `fix(hooks): ...`,
`test: ...`, `docs: ...`, `chore: ...`. Scope is the package. One task per commit.
End every commit message with:

```
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## Hackathon rules that bind the code

- All submission code is written during the event window.
- FalkorDB is the primary database and central to the product.
- The entrant must be able to explain every part, so keep the code plain.
