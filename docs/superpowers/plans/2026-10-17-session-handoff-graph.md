# Session Handoff Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A FalkorDB graph, fed by Claude Code hooks and read through an MCP server, that lets parallel Claude Code sessions read each other's intent, message each other (waking idle sessions), and get stand-in answers.

**Architecture:** Hooks record each session's prompts and edits into FalkorDB, keyed by Claude Code's own ids, and deliver messages. A per-session stdio MCP server gives the agent tools to record decisions and needs, read other sessions' history, send messages and ask questions. All Cypher lives in `handoff.graph`.

**Tech Stack:** Python 3.12+, uv, FalkorDB 4.x in Docker, `falkordb` 1.8 client, `mcp` 2.3 (Phase 3), headless Claude Code `claude -p` for the stand-in (Phase 5), `fastembed` 0.9 (Phase 6), pytest 9, mypy 2.4 strict, ruff 0.17.

**Spec:** `docs/superpowers/specs/2026-10-07-session-handoff-graph-design.md`. Project rules: `CLAUDE.md`.

## How this plan is written

The project is built in eight phases, each ending at a gate (see `CLAUDE.md`).
Phases 0 and 1 are written out step by step below. Phases 2 to 7 list their
tasks, interfaces, tests and gate; each one's step-by-step code is written at
the previous phase's gate, against the code and library versions that exist
then. Three of those phases depend on library APIs (`mcp`, `anthropic`,
`fastembed`) that must be checked against the installed versions first.

## Time budget

Deadline: 18 October 2026, 11:59 PM IST. Start: 17 October morning.

| Phase | Estimate | Target finish |
|---|---|---|
| 0 Skeleton | 1 h | Sat 10:00 |
| 1 Graph layer | 3 h | Sat 13:00 |
| 2 Capture hooks | 3 h | Sat 17:00 |
| 3 MCP server | 3 h | Sat 21:00 |
| 4 Finish check and live messages | 4 h | Sun 11:00 |
| 5 Stand-in | 3 h | Sun 14:00 |
| 6 Search by meaning | 2 h | Sun 16:00, dropped if late |
| 7 Ship | 4 h | Sun 21:00, leaving 3 h of slack |

If Phase 4 is not through its gate by Sunday 13:00, Phase 6 is dropped.

## Global Constraints

- Python `>=3.12`; run everything through `uv run`.
- FalkorDB is the primary database and central to the product.
- All Cypher in `src/handoff/graph/`; values only as `$parameters`.
- Ids: `session_id` → `Session.id`, `prompt_id` → `Request.id`, `tool_use_id` → `Edit.id`; otherwise `handoff.ids.new_id()`.
- Times: integer milliseconds from `handoff.ids.now_ms()`.
- Graph name `handoff` by default, set by `HANDOFF_GRAPH`.
- Role from `HANDOFF_ROLE`, else the folder name, else `"unknown"`.
- Hooks fail open: any error is logged to `~/.handoff/logs/hooks.log` and the hook exits 0. Exception: the waiter exits 2 on purpose to wake a session.
- File-edit hook matcher: `Edit|Write|NotebookEdit` (`MultiEdit` is not in the current tool list).
- Text shown to Claude is stated as fact, not as commands.
- Prompt and diff text pass through `handoff.redact.redact` before storage.
- Stored prompt text is capped at 20,000 characters; edit summaries at 40 lines or 4,000 characters.

## Review Focus

1. **Prompt text that looks like code or Cypher** (quotes, braces, `DETACH DELETE`, newlines) must be stored and returned exactly. Test: `test_request_text_round_trips_exactly` in Task 1.2.
2. **Non-ASCII prompts** (Hindi, emoji) must round-trip. Same test as 1.
3. **A request with no decisions or needs** must come back with empty tuples, not a row of nulls. Test: `test_handoff_request_without_decisions_has_empty_tuples` in Task 1.4.
4. **An edit before any prompt** (a resumed session where `prompt_id` is absent) must not crash the hook; the edit attaches to the session's latest request or is skipped. Test: `test_edit_without_prompt_id_attaches_to_latest_request` in Phase 2, Task 2.3.
5. **Two sessions with the same role** (a second frontend terminal): a message to that role reaches both, once each. Test: `test_role_message_reaches_each_session_once` in Phase 4, Task 4.2.

---

## File structure

```
pyproject.toml              project, dependencies, ruff, mypy, pytest settings
Makefile                    fmt, check, test, db-up, db-down
docker-compose.yml          FalkorDB with browser
.gitignore
CLAUDE.md                   project rules
src/handoff/
  __init__.py               version
  ids.py                    new_id(), now_ms()
  config.py                 Config, resolve_role()
  redact.py                 (P2) redact()
  spool.py                  (P2) local replay file
  format.py                 (P1) render_handoff(), select_requests()
  embed.py                  (P6) local embeddings
  install.py                (P7) handoff install
  graph/
    __init__.py
    connection.py           connect()
    schema.py               ensure_schema()
    records.py              frozen dataclasses for results
    sessions.py             upsert_session, active_session, active_sessions
    requests.py             add_request, latest_request_id, (P4) request_needs_decision
    edits.py                add_edit, why_file
    decisions.py            normalise_topic, add_decision, (P6) similar_decisions
    needs.py                add_need, resolve_need
    history.py              handoff_requests
    messages.py             (P4) add_message, claim_pending_messages
  hooks/                    (P2, P4)
    __init__.py
    cli.py                  handoff-hook entry point
    events.py               one handler per hook event
    edits.py                edit summary builder
    waiter.py               (P4) asyncRewake message waiter
  mcp/                      (P3, P4, P5)
    __init__.py
    tools.py                tool logic as plain functions
    server.py               MCP wrapper, handoff-mcp entry point
  standin/                  (P5)
    __init__.py
    context.py              gather what the stand-in may use
    answer.py               model call and answer validation
tests/                      mirrors src/handoff
  conftest.py               config and graph fixtures
```

---

## Phase 0: Skeleton

Branch: `phase/0-skeleton`. Before starting: `docker ps` must work. On this machine Docker runs through Colima (`colima start`).

### Task 0.1: Project skeleton and tooling

**Files:**
- Create: `pyproject.toml`, `Makefile`, `docker-compose.yml`, `.gitignore`, `src/handoff/__init__.py`, `tests/test_smoke.py`

**Interfaces:**
- Produces: `handoff.__version__: str`; commands `make fmt`, `make check`, `make test`, `make db-up`, `make db-down`.

- [ ] **Step 1: Commit the docs on `main`, then branch**

```bash
git add CLAUDE.md docs/
git commit -m "docs: add design, plan and project rules

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git switch -c phase/0-skeleton
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "handoff"
version = "0.1.0"
description = "A shared FalkorDB context graph for parallel Claude Code sessions"
requires-python = ">=3.12"
dependencies = ["falkordb>=1.8,<2"]

[dependency-groups]
dev = ["pytest>=9.1", "mypy>=2.4", "ruff>=0.17"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/handoff"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF", "N", "S", "PT"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]

[tool.mypy]
strict = true
python_version = "3.12"
files = ["src", "tests"]

[[tool.mypy.overrides]]
module = ["falkordb.*", "redis.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
```

- [ ] **Step 3: Write `Makefile`** (recipe lines start with a tab)

```make
.PHONY: fmt check test db-up db-down

fmt:
	uv run ruff format .
	uv run ruff check --fix .

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest -q

test:
	uv run pytest -q

db-up:
	docker compose up -d --wait

db-down:
	docker compose down
```

- [ ] **Step 4: Write `docker-compose.yml`**

```yaml
services:
  falkordb:
    image: falkordb/falkordb:latest
    ports:
      - "6379:6379"
      - "3000:3000"
    volumes:
      - falkordb-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 2s
      timeout: 2s
      retries: 15

volumes:
  falkordb-data:
```

- [ ] **Step 5: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.mypy_cache/
.ruff_cache/
.pytest_cache/
dist/
.env
.DS_Store
```

- [ ] **Step 6: Write the failing smoke test** `tests/test_smoke.py`

```python
from __future__ import annotations

import handoff


def test_package_reports_its_version() -> None:
    assert handoff.__version__ == "0.1.0"
```

- [ ] **Step 7: Run it to see it fail**

Run: `uv sync && uv run pytest tests/test_smoke.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'handoff'` or missing `__version__`.

- [ ] **Step 8: Write `src/handoff/__init__.py`**

```python
"""A shared FalkorDB context graph for parallel Claude Code sessions."""

from __future__ import annotations

__version__ = "0.1.0"
```

- [ ] **Step 9: Run the full check**

Run: `uv sync && make check`
Expected: format check, lint, mypy and 1 test all pass.

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml uv.lock Makefile docker-compose.yml .gitignore src tests
git commit -m "chore: add project skeleton, tooling and FalkorDB compose file

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 0.2: Ids and configuration

**Files:**
- Create: `src/handoff/ids.py`, `src/handoff/config.py`, `tests/test_ids.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `handoff.ids.new_id() -> str` (32 hex characters)
  - `handoff.ids.now_ms() -> int`
  - `handoff.config.Config(host: str, port: int, graph_name: str, home: Path)`, frozen
  - `Config.from_env(env: Mapping[str, str] | None = None) -> Config`
  - `handoff.config.resolve_role(cwd: str, env: Mapping[str, str]) -> str`

- [ ] **Step 1: Write the failing tests**

`tests/test_ids.py`:

```python
from __future__ import annotations

from handoff.ids import new_id, now_ms


def test_new_ids_are_unique_hex() -> None:
    ids = {new_id() for _ in range(1000)}
    assert len(ids) == 1000
    assert all(len(i) == 32 and int(i, 16) >= 0 for i in ids)


def test_now_ms_is_epoch_milliseconds() -> None:
    assert 1_700_000_000_000 < now_ms() < 4_000_000_000_000
```

`tests/test_config.py`:

```python
from __future__ import annotations

from pathlib import Path

from handoff.config import Config, resolve_role


def test_config_reads_environment(tmp_path: Path) -> None:
    env = {
        "HANDOFF_DB_HOST": "db",
        "HANDOFF_DB_PORT": "6390",
        "HANDOFF_GRAPH": "g1",
        "HANDOFF_HOME": str(tmp_path),
    }
    assert Config.from_env(env) == Config(host="db", port=6390, graph_name="g1", home=tmp_path)


def test_config_defaults() -> None:
    config = Config.from_env({})
    assert (config.host, config.port, config.graph_name) == ("localhost", 6379, "handoff")
    assert config.home == Path.home() / ".handoff"


def test_role_prefers_environment() -> None:
    assert resolve_role("/work/frontend", {"HANDOFF_ROLE": "web"}) == "web"


def test_role_falls_back_to_folder_name() -> None:
    assert resolve_role("/work/backend", {}) == "backend"


def test_role_for_filesystem_root_is_unknown() -> None:
    assert resolve_role("/", {}) == "unknown"
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_ids.py tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/handoff/ids.py`**

```python
"""Ids and timestamps used across the graph."""

from __future__ import annotations

import time
import uuid


def new_id() -> str:
    """Return a new random id for nodes Claude Code does not name."""
    return uuid.uuid4().hex


def now_ms() -> int:
    """Return the current time in milliseconds since the epoch."""
    return time.time_ns() // 1_000_000
```

- [ ] **Step 4: Write `src/handoff/config.py`**

```python
"""Settings read from the environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    """Where the graph lives and where local files (replay file, locks, logs) go."""

    host: str
    port: int
    graph_name: str
    home: Path

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        """Build a config from environment variables, with local defaults."""
        source = os.environ if env is None else env
        return cls(
            host=source.get("HANDOFF_DB_HOST", "localhost"),
            port=int(source.get("HANDOFF_DB_PORT", "6379")),
            graph_name=source.get("HANDOFF_GRAPH", "handoff"),
            home=Path(source.get("HANDOFF_HOME", str(Path.home() / ".handoff"))),
        )


def resolve_role(cwd: str, env: Mapping[str, str]) -> str:
    """Return the session's role: HANDOFF_ROLE, else the folder name, else 'unknown'."""
    role = env.get("HANDOFF_ROLE", "").strip()
    if role:
        return role
    return Path(cwd).name or "unknown"
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `uv run pytest tests/test_ids.py tests/test_config.py -q`
Expected: 7 passed.

- [ ] **Step 6: Check and commit**

```bash
make fmt && make check
git add src/handoff/ids.py src/handoff/config.py tests/test_ids.py tests/test_config.py
git commit -m "feat: add ids, timestamps and environment config

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 0.3: Graph connection and test fixtures

**Files:**
- Create: `src/handoff/graph/__init__.py`, `src/handoff/graph/connection.py`, `tests/conftest.py`, `tests/graph/__init__.py`, `tests/graph/test_connection.py`

**Interfaces:**
- Consumes: `Config` (Task 0.2).
- Produces:
  - `handoff.graph.connection.connect(config: Config) -> Graph` (`falkordb.Graph`)
  - pytest fixtures `config: Config` (throwaway graph name, `home` under `tmp_path`) and `graph: Graph` (deleted after the test).

- [ ] **Step 1: Start FalkorDB**

Run: `make db-up`
Expected: the `falkordb` container reports healthy.

- [ ] **Step 2: Write the fixtures** `tests/conftest.py`

```python
from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from falkordb import Graph
from redis.exceptions import ResponseError

from handoff.config import Config
from handoff.graph.connection import connect


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        host="localhost",
        port=6379,
        graph_name=f"test_{uuid.uuid4().hex[:12]}",
        home=tmp_path / "home",
    )


@pytest.fixture
def graph(config: Config) -> Iterator[Graph]:
    g = connect(config)
    yield g
    try:
        g.delete()
    except ResponseError:
        # The test never wrote anything, so the graph was never created.
        pass
```

`tests/graph/__init__.py`: empty file.

- [ ] **Step 3: Write the failing test** `tests/graph/test_connection.py`

```python
from __future__ import annotations

from falkordb import Graph


def test_connected_graph_answers_a_query(graph: Graph) -> None:
    assert graph.query("RETURN 1").result_set == [[1]]
```

- [ ] **Step 4: Run it to see it fail**

Run: `uv run pytest tests/graph/test_connection.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handoff.graph'`.

- [ ] **Step 5: Write the connection module**

`src/handoff/graph/__init__.py`:

```python
"""Everything that talks to FalkorDB. All Cypher in the project lives in this package."""
```

`src/handoff/graph/connection.py`:

```python
"""Opening the graph."""

from __future__ import annotations

from falkordb import FalkorDB, Graph

from handoff.config import Config


def connect(config: Config) -> Graph:
    """Return a handle to the configured graph.

    Short timeouts keep hooks fast when the database is down; they fall back to
    the replay file instead of waiting.
    """
    db = FalkorDB(
        host=config.host,
        port=config.port,
        socket_connect_timeout=1,
        socket_timeout=5,
    )
    return db.select_graph(config.graph_name)
```

- [ ] **Step 6: Run the test to see it pass**

Run: `uv run pytest tests/graph/test_connection.py -q`
Expected: 1 passed.

- [ ] **Step 7: Check and commit**

```bash
make fmt && make check
git add src/handoff/graph tests/conftest.py tests/graph
git commit -m "feat(graph): add FalkorDB connection and per-test graph fixtures

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Phase 0 gate

- [ ] `make check` passes.
- [ ] Show it working: `make db-up`, open http://localhost:3000, connect to `localhost:6379`, and see the FalkorDB browser load.
- [ ] Merge and tag:

```bash
git switch main
git merge --no-ff phase/0-skeleton -m "Merge phase 0: skeleton"
git tag phase-0
```

- [ ] Notebook: change-log row "Phase 0 done".
- [ ] Write Phase 2's step-by-step tasks into this plan if any interface changed; otherwise continue.

---

## Phase 1: Graph layer

Branch: `phase/1-graph`.

**Module layout (ruling, 17 October, from Aditya's small-files rule in `CLAUDE.md`).**
The graph code is split by subject, not into one `writes.py` and one `reads.py`.
Where a task below says `writes.py` or `reads.py`, use this map; the function
names and signatures are unchanged. Tests mirror it (`tests/graph/test_<module>.py`),
and the `ready` fixture lives in `tests/graph/conftest.py`.

| Function | Module |
|---|---|
| `upsert_session`, `active_session`, `active_sessions` | `handoff.graph.sessions` |
| `add_request`, `latest_request_id` | `handoff.graph.requests` |
| `add_edit`, `why_file` | `handoff.graph.edits` |
| `normalise_topic`, `add_decision` | `handoff.graph.decisions` |
| `add_need`, `resolve_need` | `handoff.graph.needs` |
| `handoff_requests` | `handoff.graph.history` |

### Task 1.1: Schema

**Files:**
- Create: `src/handoff/graph/schema.py`, `tests/graph/test_schema.py`

**Interfaces:**
- Produces: `handoff.graph.schema.ensure_schema(graph: Graph) -> None`, safe to call any number of times; `INDEXED: tuple[tuple[str, str], ...]`.

- [ ] **Step 1: Write the failing tests** `tests/graph/test_schema.py`

```python
from __future__ import annotations

from falkordb import Graph

from handoff.graph.schema import INDEXED, ensure_schema


def _indexed_labels(graph: Graph) -> set[str]:
    return {str(row[0]) for row in graph.list_indices().result_set}


def test_schema_indexes_every_lookup_key(graph: Graph) -> None:
    ensure_schema(graph)
    assert {label for label, _ in INDEXED} <= _indexed_labels(graph)


def test_schema_can_be_applied_twice(graph: Graph) -> None:
    ensure_schema(graph)
    ensure_schema(graph)
    assert {label for label, _ in INDEXED} <= _indexed_labels(graph)
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/graph/test_schema.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3a: Declare `redis` as a direct dependency** (this module imports it): `uv add "redis>=5"`.

- [ ] **Step 3: Write `src/handoff/graph/schema.py`**

```python
"""Indexes for every property the code looks nodes up by."""

from __future__ import annotations

from falkordb import Graph
from redis.exceptions import ResponseError

INDEXED: tuple[tuple[str, str], ...] = (
    ("Session", "id"),
    ("Session", "role"),
    ("Request", "id"),
    ("Edit", "id"),
    ("File", "path"),
    ("Decision", "id"),
    ("Need", "id"),
    ("Topic", "name"),
    ("Message", "id"),
)


def ensure_schema(graph: Graph) -> None:
    """Create any missing range indexes. Existing ones are left alone."""
    for label, prop in INDEXED:
        try:
            graph.create_node_range_index(label, prop)
        except ResponseError as exc:
            # FalkorDB refuses to create an index that already exists.
            if "already indexed" not in str(exc).lower():
                raise
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/graph/test_schema.py -q`
Expected: 2 passed. If `test_schema_can_be_applied_twice` fails with a `ResponseError`, read its message and change the `"already indexed"` check to match FalkorDB's actual wording.

- [ ] **Step 5: Check and commit**

```bash
make fmt && make check
git add src/handoff/graph/schema.py tests/graph/test_schema.py
git commit -m "feat(graph): add idempotent schema setup

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 1.2: Recording sessions, requests and edits

**Files:**
- Create: `src/handoff/graph/writes.py`, `tests/graph/test_writes.py`

**Interfaces:**
- Consumes: `ensure_schema` (Task 1.1).
- Produces:
  - `upsert_session(graph, *, session_id: str, role: str, cwd: str, at: int) -> None`
  - `add_request(graph, *, session_id: str, request_id: str, text: str, at: int) -> int` returns the request's sequence number in its session; raises `LookupError` if the session does not exist; repeat calls with the same `request_id` return the same number and change nothing.
  - `add_edit(graph, *, request_id: str, edit_id: str, tool: str, path: str, summary: str, at: int) -> bool` returns `False` if the request does not exist; repeat calls change nothing.

- [ ] **Step 1: Write the failing tests** `tests/graph/test_writes.py`

```python
from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.schema import ensure_schema
from handoff.graph.writes import add_edit, add_request, upsert_session


@pytest.fixture
def ready(graph: Graph) -> Graph:
    ensure_schema(graph)
    upsert_session(graph, session_id="s1", role="frontend", cwd="/w", at=1000)
    return graph


def test_session_is_created_then_refreshed(graph: Graph) -> None:
    upsert_session(graph, session_id="s1", role="frontend", cwd="/w", at=1000)
    upsert_session(graph, session_id="s1", role="web", cwd="/w", at=2000)
    rows = graph.query(
        "MATCH (s:Session {id: 's1'}) RETURN s.role, s.started_at, s.last_seen_at"
    ).result_set
    assert rows == [["web", 1000, 2000]]


def test_requests_are_numbered_and_chained(ready: Graph) -> None:
    assert add_request(ready, session_id="s1", request_id="p1", text="one", at=1) == 1
    assert add_request(ready, session_id="s1", request_id="p2", text="two", at=2) == 2
    chain = ready.query("MATCH (a:Request)-[:NEXT]->(b:Request) RETURN a.id, b.id").result_set
    assert chain == [["p1", "p2"]]


def test_repeated_request_is_not_duplicated(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert add_request(ready, session_id="s1", request_id="p1", text="one", at=1) == 1
    assert ready.query("MATCH (r:Request) RETURN count(r)").result_set == [[1]]


def test_request_for_unknown_session_raises(ready: Graph) -> None:
    with pytest.raises(LookupError):
        add_request(ready, session_id="nope", request_id="p1", text="x", at=1)


def test_request_text_round_trips_exactly(ready: Graph) -> None:
    text = 'Fix "name"}) DETACH DELETE (n) // नमस्ते 🚀\nsecond line'
    add_request(ready, session_id="s1", request_id="p1", text=text, at=1)
    rows = ready.query("MATCH (r:Request {id: 'p1'}) RETURN r.text").result_set
    assert rows == [[text]]


def test_edit_links_request_to_file(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert add_edit(
        ready, request_id="p1", edit_id="t1", tool="Edit", path="src/a.ts", summary="-a\n+b", at=2
    )
    rows = ready.query(
        "MATCH (:Request {id: 'p1'})-[:CAUSED]->(e:Edit)-[:TOUCHED]->(f:File) "
        "RETURN e.tool, e.summary, f.path"
    ).result_set
    assert rows == [["Edit", "-a\n+b", "src/a.ts"]]


def test_replayed_edit_is_not_duplicated(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    for _ in range(2):
        add_edit(ready, request_id="p1", edit_id="t1", tool="Edit", path="a", summary="", at=2)
    assert ready.query("MATCH (e:Edit) RETURN count(e)").result_set == [[1]]
    assert ready.query("MATCH ()-[c:CAUSED]->() RETURN count(c)").result_set == [[1]]


def test_edit_for_unknown_request_is_refused(ready: Graph) -> None:
    assert not add_edit(ready, request_id="nope", edit_id="t1", tool="Edit", path="a", summary="", at=2)
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/graph/test_writes.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handoff.graph.writes'`.

- [ ] **Step 3: Write `src/handoff/graph/writes.py`**

```python
"""Every query that writes to the graph."""

from __future__ import annotations

from falkordb import Graph


def upsert_session(graph: Graph, *, session_id: str, role: str, cwd: str, at: int) -> None:
    """Create the session on first sight; refresh its role, folder and last-seen time."""
    graph.query(
        "MERGE (s:Session {id: $id}) "
        "ON CREATE SET s.started_at = $at "
        "SET s.role = $role, s.cwd = $cwd, s.last_seen_at = $at",
        {"id": session_id, "role": role, "cwd": cwd, "at": at},
    )


def add_request(graph: Graph, *, session_id: str, request_id: str, text: str, at: int) -> int:
    """Record a prompt as the session's next request and return its sequence number.

    Calling again with the same request_id changes nothing and returns the same number.
    """
    existing = graph.query(
        "MATCH (r:Request {id: $rid}) RETURN r.seq", {"rid": request_id}
    ).result_set
    if existing:
        return int(existing[0][0])

    previous = graph.query(
        "MATCH (:Session {id: $sid})-[:RECEIVED]->(p:Request) "
        "RETURN p.id, p.seq ORDER BY p.seq DESC LIMIT 1",
        {"sid": session_id},
    ).result_set
    seq = int(previous[0][1]) + 1 if previous else 1

    created = graph.query(
        "MATCH (s:Session {id: $sid}) "
        "CREATE (s)-[:RECEIVED]->(:Request {id: $rid, seq: $seq, text: $text, at: $at})",
        {"sid": session_id, "rid": request_id, "seq": seq, "text": text, "at": at},
    )
    if created.nodes_created == 0:
        raise LookupError(f"no session with id {session_id}")

    if previous:
        graph.query(
            "MATCH (p:Request {id: $pid}), (r:Request {id: $rid}) CREATE (p)-[:NEXT]->(r)",
            {"pid": previous[0][0], "rid": request_id},
        )
    return seq


def add_edit(
    graph: Graph,
    *,
    request_id: str,
    edit_id: str,
    tool: str,
    path: str,
    summary: str,
    at: int,
) -> bool:
    """Attach an edit of `path` to the request that caused it.

    Returns False when the request is unknown. Calling again with the same edit_id
    changes nothing, which makes replaying the local file safe.
    """
    rows = graph.query(
        "MATCH (r:Request {id: $rid}) "
        "MERGE (e:Edit {id: $eid}) "
        "ON CREATE SET e.tool = $tool, e.summary = $summary, e.at = $at "
        "MERGE (r)-[:CAUSED]->(e) "
        "MERGE (f:File {path: $path}) "
        "MERGE (e)-[:TOUCHED]->(f) "
        "RETURN e.id",
        {
            "rid": request_id,
            "eid": edit_id,
            "tool": tool,
            "path": path,
            "summary": summary,
            "at": at,
        },
    ).result_set
    return bool(rows)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/graph/test_writes.py -q`
Expected: 8 passed.

- [ ] **Step 5: Check and commit**

```bash
make fmt && make check
git add src/handoff/graph/writes.py tests/graph/test_writes.py
git commit -m "feat(graph): record sessions, requests and edits idempotently

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 1.3: Recording decisions and needs

**Files:**
- Modify: `src/handoff/graph/writes.py` (append)
- Modify: `tests/graph/test_writes.py` (append)

**Interfaces:**
- Consumes: `add_request` (Task 1.2).
- Produces:
  - `normalise_topic(topic: str) -> str` (trimmed, lower case, inner whitespace collapsed)
  - `add_decision(graph, *, request_id: str, decision_id: str, text: str, reason: str, topic: str, at: int) -> bool`
  - `add_need(graph, *, request_id: str, need_id: str, text: str, for_role: str, at: int) -> bool`
  - `resolve_need(graph, *, need_id: str, request_id: str) -> bool`

- [ ] **Step 1: Append the failing tests** to `tests/graph/test_writes.py`

```python
from handoff.graph.writes import add_decision, add_need, normalise_topic, resolve_need


def test_topic_names_are_normalised() -> None:
    assert normalise_topic("  Auth   Tokens ") == "auth tokens"


def test_decision_hangs_off_request_with_topic(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert add_decision(
        ready, request_id="p1", decision_id="d1", text="use fullName",
        reason="no client-side joining", topic="User Profile", at=2,
    )
    rows = ready.query(
        "MATCH (:Request {id: 'p1'})-[:LED_TO]->(d:Decision)-[:ABOUT]->(t:Topic) "
        "RETURN d.text, d.reason, t.name"
    ).result_set
    assert rows == [["use fullName", "no client-side joining", "user profile"]]


def test_decisions_on_the_same_topic_share_one_topic_node(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    for i in range(2):
        add_decision(ready, request_id="p1", decision_id=f"d{i}", text="t", reason="r",
                     topic="Auth", at=2)
    assert ready.query("MATCH (t:Topic) RETURN count(t)").result_set == [[1]]


def test_decision_for_unknown_request_is_refused(ready: Graph) -> None:
    assert not add_decision(ready, request_id="nope", decision_id="d1", text="t",
                            reason="r", topic="x", at=1)


def test_need_starts_open_and_is_resolved_by_another_request(ready: Graph) -> None:
    upsert_session(ready, session_id="s2", role="backend", cwd="/w", at=1)
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    add_request(ready, session_id="s2", request_id="p9", text="pick up", at=5)
    assert add_need(ready, request_id="p1", need_id="n1", text="return avatarUrl",
                    for_role="backend", at=2)
    assert ready.query("MATCH (n:Need {id: 'n1'}) RETURN n.status").result_set == [["open"]]

    assert resolve_need(ready, need_id="n1", request_id="p9")
    rows = ready.query(
        "MATCH (n:Need {id: 'n1'})-[:RESOLVED_BY]->(r:Request) RETURN n.status, r.id"
    ).result_set
    assert rows == [["resolved", "p9"]]


def test_resolving_unknown_need_is_refused(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert not resolve_need(ready, need_id="nope", request_id="p1")
```

Move the new import to the import block at the top of the file.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/graph/test_writes.py -q`
Expected: FAIL with `ImportError: cannot import name 'add_decision'`.

- [ ] **Step 3: Append to `src/handoff/graph/writes.py`**

```python
def normalise_topic(topic: str) -> str:
    """Return the canonical form of a topic name, so 'Auth ' and 'auth' are one topic."""
    return " ".join(topic.split()).lower()


def add_decision(
    graph: Graph,
    *,
    request_id: str,
    decision_id: str,
    text: str,
    reason: str,
    topic: str,
    at: int,
) -> bool:
    """Record a decision made for a request, and the topic it is about."""
    rows = graph.query(
        "MATCH (r:Request {id: $rid}) "
        "MERGE (d:Decision {id: $did}) "
        "ON CREATE SET d.text = $text, d.reason = $reason, d.at = $at "
        "MERGE (r)-[:LED_TO]->(d) "
        "MERGE (t:Topic {name: $topic}) "
        "MERGE (d)-[:ABOUT]->(t) "
        "RETURN d.id",
        {
            "rid": request_id,
            "did": decision_id,
            "text": text,
            "reason": reason,
            "topic": normalise_topic(topic),
            "at": at,
        },
    ).result_set
    return bool(rows)


def add_need(
    graph: Graph, *, request_id: str, need_id: str, text: str, for_role: str, at: int
) -> bool:
    """Record something a request needs from another role. Needs start open."""
    rows = graph.query(
        "MATCH (r:Request {id: $rid}) "
        "MERGE (n:Need {id: $nid}) "
        "ON CREATE SET n.text = $text, n.for_role = $for_role, n.status = 'open', n.at = $at "
        "MERGE (r)-[:RAISED]->(n) "
        "RETURN n.id",
        {"rid": request_id, "nid": need_id, "text": text, "for_role": for_role, "at": at},
    ).result_set
    return bool(rows)


def resolve_need(graph: Graph, *, need_id: str, request_id: str) -> bool:
    """Mark a need resolved by a request, usually one in another session."""
    rows = graph.query(
        "MATCH (n:Need {id: $nid}), (r:Request {id: $rid}) "
        "SET n.status = 'resolved' "
        "MERGE (n)-[:RESOLVED_BY]->(r) "
        "RETURN n.id",
        {"nid": need_id, "rid": request_id},
    ).result_set
    return bool(rows)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/graph/test_writes.py -q`
Expected: 14 passed.

- [ ] **Step 5: Check and commit**

```bash
make fmt && make check
git add src/handoff/graph/writes.py tests/graph/test_writes.py
git commit -m "feat(graph): record decisions, topics and needs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 1.4: Reading history

**Files:**
- Create: `src/handoff/graph/records.py`, `src/handoff/graph/reads.py`, `tests/graph/test_reads.py`

**Interfaces:**
- Consumes: all writes from Tasks 1.2 and 1.3.
- Produces, in `records.py` (frozen dataclasses):
  - `SessionInfo(id: str, role: str, cwd: str, started_at: int, last_seen_at: int)`
  - `DecisionView(id: str, text: str, reason: str)`
  - `NeedView(id: str, text: str, for_role: str, status: str)`
  - `RequestView(id: str, role: str, seq: int, text: str, at: int, files: tuple[str, ...], decisions: tuple[DecisionView, ...], needs: tuple[NeedView, ...])`
  - `WhyRow(role: str, request_text: str, decision_text: str | None, decision_reason: str | None, edit_summary: str, at: int)`
- Produces, in `reads.py`:
  - `latest_request_id(graph, session_id: str) -> str | None`
  - `active_session(graph, *, role: str, cwd: str) -> SessionInfo | None` (most recently seen)
  - `active_sessions(graph, *, since: int) -> list[SessionInfo]` (seen at or after `since`, ordered by role)
  - `why_file(graph, path: str, limit: int = 20) -> list[WhyRow]` (newest edit first)
  - `handoff_requests(graph, *, role: str | None, since: int) -> list[RequestView]` (oldest first; `role=None` means all roles)

- [ ] **Step 1: Write the failing tests** `tests/graph/test_reads.py`

```python
from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.reads import (
    active_session,
    active_sessions,
    handoff_requests,
    latest_request_id,
    why_file,
)
from handoff.graph.records import DecisionView, NeedView
from handoff.graph.schema import ensure_schema
from handoff.graph.writes import (
    add_decision,
    add_edit,
    add_need,
    add_request,
    upsert_session,
)


@pytest.fixture
def history(graph: Graph) -> Graph:
    """Frontend made two requests; backend made one."""
    ensure_schema(graph)
    upsert_session(graph, session_id="fe", role="frontend", cwd="/w", at=100)
    upsert_session(graph, session_id="be", role="backend", cwd="/w", at=200)
    add_request(graph, session_id="fe", request_id="p1", text="show avatar", at=110)
    add_edit(graph, request_id="p1", edit_id="e1", tool="Edit", path="Card.tsx",
             summary="+avatar", at=111)
    add_decision(graph, request_id="p1", decision_id="d1", text="read avatarUrl",
                 reason="server owns urls", topic="profile", at=112)
    add_need(graph, request_id="p1", need_id="n1", text="return avatarUrl",
             for_role="backend", at=113)
    add_request(graph, session_id="fe", request_id="p2", text="tidy styles", at=120)
    add_edit(graph, request_id="p2", edit_id="e2", tool="Edit", path="Card.tsx",
             summary="+class", at=121)
    add_request(graph, session_id="be", request_id="p3", text="pick up frontend", at=210)
    return graph


def test_latest_request_is_the_highest_numbered(history: Graph) -> None:
    assert latest_request_id(history, "fe") == "p2"
    assert latest_request_id(history, "nobody") is None


def test_active_session_is_found_by_role_and_folder(history: Graph) -> None:
    session = active_session(history, role="backend", cwd="/w")
    assert session is not None and session.id == "be"
    assert active_session(history, role="deploy", cwd="/w") is None


def test_active_sessions_are_filtered_by_last_seen(history: Graph) -> None:
    assert [s.role for s in active_sessions(history, since=0)] == ["backend", "frontend"]
    assert [s.role for s in active_sessions(history, since=150)] == ["backend"]


def test_why_file_lists_newest_edit_first_with_decisions(history: Graph) -> None:
    rows = why_file(history, "Card.tsx")
    assert [r.request_text for r in rows] == ["tidy styles", "show avatar"]
    assert rows[0].decision_text is None
    assert (rows[1].decision_text, rows[1].decision_reason) == ("read avatarUrl", "server owns urls")


def test_handoff_bundles_files_decisions_and_needs(history: Graph) -> None:
    requests = handoff_requests(history, role="frontend", since=0)
    assert [r.id for r in requests] == ["p1", "p2"]
    first = requests[0]
    assert first.files == ("Card.tsx",)
    assert first.decisions == (DecisionView(id="d1", text="read avatarUrl", reason="server owns urls"),)
    assert first.needs == (NeedView(id="n1", text="return avatarUrl", for_role="backend",
                                    status="open"),)


def test_handoff_request_without_decisions_has_empty_tuples(history: Graph) -> None:
    second = handoff_requests(history, role="frontend", since=0)[1]
    assert (second.decisions, second.needs) == ((), ())


def test_handoff_filters_by_time_and_covers_all_roles(history: Graph) -> None:
    assert [r.id for r in handoff_requests(history, role="frontend", since=115)] == ["p2"]
    assert [r.id for r in handoff_requests(history, role=None, since=0)] == ["p1", "p2", "p3"]
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/graph/test_reads.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'handoff.graph.reads'`.

- [ ] **Step 3: Write `src/handoff/graph/records.py`**

```python
"""Typed results returned by the read queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionInfo:
    id: str
    role: str
    cwd: str
    started_at: int
    last_seen_at: int


@dataclass(frozen=True)
class DecisionView:
    id: str
    text: str
    reason: str


@dataclass(frozen=True)
class NeedView:
    id: str
    text: str
    for_role: str
    status: str


@dataclass(frozen=True)
class RequestView:
    id: str
    role: str
    seq: int
    text: str
    at: int
    files: tuple[str, ...]
    decisions: tuple[DecisionView, ...]
    needs: tuple[NeedView, ...]


@dataclass(frozen=True)
class WhyRow:
    role: str
    request_text: str
    decision_text: str | None
    decision_reason: str | None
    edit_summary: str
    at: int
```

- [ ] **Step 4: Write `src/handoff/graph/reads.py`**

```python
"""Every query that reads from the graph."""

from __future__ import annotations

from typing import Any

from falkordb import Graph

from handoff.graph.records import DecisionView, NeedView, RequestView, SessionInfo, WhyRow

_SESSION_FIELDS = "s.id, s.role, s.cwd, s.started_at, s.last_seen_at"


def _session(row: list[Any]) -> SessionInfo:
    return SessionInfo(
        id=str(row[0]),
        role=str(row[1]),
        cwd=str(row[2]),
        started_at=int(row[3]),
        last_seen_at=int(row[4]),
    )


def latest_request_id(graph: Graph, session_id: str) -> str | None:
    """Return the id of the session's most recent request, if it has one."""
    rows = graph.ro_query(
        "MATCH (:Session {id: $sid})-[:RECEIVED]->(r:Request) "
        "RETURN r.id ORDER BY r.seq DESC LIMIT 1",
        {"sid": session_id},
    ).result_set
    return str(rows[0][0]) if rows else None


def active_session(graph: Graph, *, role: str, cwd: str) -> SessionInfo | None:
    """Return the most recently seen session with this role in this folder."""
    rows = graph.ro_query(
        f"MATCH (s:Session {{role: $role, cwd: $cwd}}) RETURN {_SESSION_FIELDS} "
        "ORDER BY s.last_seen_at DESC LIMIT 1",
        {"role": role, "cwd": cwd},
    ).result_set
    return _session(rows[0]) if rows else None


def active_sessions(graph: Graph, *, since: int) -> list[SessionInfo]:
    """Return sessions seen at or after `since`, ordered by role."""
    rows = graph.ro_query(
        f"MATCH (s:Session) WHERE s.last_seen_at >= $since RETURN {_SESSION_FIELDS} "
        "ORDER BY s.role",
        {"since": since},
    ).result_set
    return [_session(row) for row in rows]


def why_file(graph: Graph, path: str, limit: int = 20) -> list[WhyRow]:
    """Return the requests and decisions behind edits to `path`, newest edit first."""
    rows = graph.ro_query(
        "MATCH (f:File {path: $path})<-[:TOUCHED]-(e:Edit)<-[:CAUSED]-(r:Request)"
        "<-[:RECEIVED]-(s:Session) "
        "OPTIONAL MATCH (r)-[:LED_TO]->(d:Decision) "
        "RETURN s.role, r.text, d.text, d.reason, e.summary, e.at "
        "ORDER BY e.at DESC LIMIT $limit",
        {"path": path, "limit": limit},
    ).result_set
    return [
        WhyRow(
            role=str(row[0]),
            request_text=str(row[1]),
            decision_text=None if row[2] is None else str(row[2]),
            decision_reason=None if row[3] is None else str(row[3]),
            edit_summary=str(row[4]),
            at=int(row[5]),
        )
        for row in rows
    ]


def handoff_requests(graph: Graph, *, role: str | None, since: int) -> list[RequestView]:
    """Return requests made at or after `since`, oldest first, with what each led to."""
    rows = graph.ro_query(
        "MATCH (s:Session)-[:RECEIVED]->(r:Request) "
        "WHERE ($role IS NULL OR s.role = $role) AND r.at >= $since "
        "OPTIONAL MATCH (r)-[:CAUSED]->(:Edit)-[:TOUCHED]->(f:File) "
        "WITH s, r, collect(DISTINCT f.path) AS files "
        "OPTIONAL MATCH (r)-[:LED_TO]->(d:Decision) "
        "WITH s, r, files, collect(DISTINCT [d.id, d.text, d.reason]) AS decisions "
        "OPTIONAL MATCH (r)-[:RAISED]->(n:Need) "
        "RETURN s.role, r.id, r.seq, r.text, r.at, files, decisions, "
        "collect(DISTINCT [n.id, n.text, n.for_role, n.status]) AS needs "
        "ORDER BY r.at",
        {"role": role, "since": since},
    ).result_set
    return [
        RequestView(
            role=str(row[0]),
            id=str(row[1]),
            seq=int(row[2]),
            text=str(row[3]),
            at=int(row[4]),
            files=tuple(sorted(str(p) for p in row[5])),
            # OPTIONAL MATCH with no match collects one list of nulls; drop it.
            decisions=tuple(
                DecisionView(id=str(i), text=str(t), reason=str(why))
                for i, t, why in row[6]
                if i is not None
            ),
            needs=tuple(
                NeedView(id=str(i), text=str(t), for_role=str(r), status=str(st))
                for i, t, r, st in row[7]
                if i is not None
            ),
        )
        for row in rows
    ]
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/graph/test_reads.py -q`
Expected: 7 passed. If `handoff_requests` fails on `$role IS NULL`, FalkorDB is not accepting a null parameter in that position; split into two query strings chosen in Python by whether `role` is `None`, and rerun.

- [ ] **Step 6: Check and commit**

```bash
make fmt && make check
git add src/handoff/graph/records.py src/handoff/graph/reads.py tests/graph/test_reads.py
git commit -m "feat(graph): add history reads for sessions, files and handoffs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 1.5: Rendering a handoff

**Files:**
- Create: `src/handoff/format.py`, `tests/test_format.py`

**Interfaces:**
- Consumes: `RequestView`, `DecisionView`, `NeedView` (Task 1.4).
- Produces:
  - `select_requests(requests: Sequence[RequestView], limit: int) -> list[RequestView]`: which requests a handoff shows when there are more than `limit`. **Written by you (Aditya)**: it decides what the receiving session sees first.
  - `render_handoff(requests: Sequence[RequestView]) -> str`

- [ ] **Step 1: Write the failing tests** `tests/test_format.py`

```python
from __future__ import annotations

from handoff.format import render_handoff, select_requests
from handoff.graph.records import DecisionView, NeedView, RequestView


def _request(i: int, *, need: bool = False) -> RequestView:
    needs = (NeedView(id=f"n{i}", text="return avatarUrl", for_role="backend", status="open"),)
    return RequestView(
        id=f"p{i}", role="frontend", seq=i, text=f"request {i}", at=i,
        files=("Card.tsx",),
        decisions=(DecisionView(id=f"d{i}", text="read avatarUrl", reason="server owns urls"),),
        needs=needs if need else (),
    )


def test_render_shows_prompt_decision_files_and_need() -> None:
    text = render_handoff([_request(1, need=True)])
    assert "frontend session: 1 request, 1 file changed" in text
    assert 'Request 1 (person): "request 1"' in text
    assert "Decided: read avatarUrl" in text
    assert "Why: server owns urls" in text
    assert "Changed: Card.tsx" in text
    assert "Needs from backend: return avatarUrl (open)" in text


def test_render_of_nothing_says_so() -> None:
    assert render_handoff([]) == "No requests recorded in this period."


def test_selection_keeps_everything_under_the_limit() -> None:
    requests = [_request(i) for i in range(1, 4)]
    assert select_requests(requests, limit=5) == requests


def test_selection_respects_the_limit_and_keeps_order() -> None:
    requests = [_request(i) for i in range(1, 21)]
    chosen = select_requests(requests, limit=5)
    assert len(chosen) == 5
    assert [r.seq for r in chosen] == sorted(r.seq for r in chosen)


def test_selection_never_drops_a_request_with_an_open_need() -> None:
    requests = [_request(1, need=True)] + [_request(i) for i in range(2, 21)]
    assert requests[0] in select_requests(requests, limit=5)
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest tests/test_format.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/handoff/format.py` with your `select_requests`**

The rendering is given. `select_requests` is yours: the tests above are the
contract. Things to weigh: open needs must survive; the newest requests are
usually what the receiver is picking up; a request with decisions explains more
than one without.

```python
"""Turning history into text a session can read."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from handoff.graph.records import RequestView


def select_requests(requests: Sequence[RequestView], limit: int) -> list[RequestView]:
    """Choose at most `limit` requests to show, in their original order."""
    # Aditya: write the selection policy here (5-10 lines). The tests in
    # tests/test_format.py are the contract.
    raise NotImplementedError


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def render_handoff(requests: Sequence[RequestView]) -> str:
    """Render requests grouped by role, with what each decided, changed and needs."""
    if not requests:
        return "No requests recorded in this period."
    by_role: dict[str, list[RequestView]] = defaultdict(list)
    for request in requests:
        by_role[request.role].append(request)

    blocks: list[str] = []
    for role, items in by_role.items():
        files = {f for r in items for f in r.files}
        lines = [
            f"{role} session: {_plural(len(items), 'request')}, "
            f"{_plural(len(files), 'file')} changed"
        ]
        for r in items:
            lines.append("")
            lines.append(f'Request {r.seq} (person): "{r.text}"')
            for d in r.decisions:
                lines.append(f"  Decided: {d.text}")
                lines.append(f"  Why: {d.reason}")
            if r.files:
                lines.append(f"  Changed: {', '.join(r.files)}")
            for n in r.needs:
                lines.append(f"  Needs from {n.for_role}: {n.text} ({n.status})")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/test_format.py -q`
Expected: 5 passed once `select_requests` is written.

- [ ] **Step 5: Check and commit**

```bash
make fmt && make check
git add src/handoff/format.py tests/test_format.py
git commit -m "feat: render handoffs and choose which requests to show

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Phase 1 gate

- [ ] `make check` passes.
- [ ] Show it working: run the script below, then look at the graph in the browser (graph `demo`) with `MATCH (n) RETURN n`.

```bash
HANDOFF_GRAPH=demo uv run python - <<'EOF'
from handoff.config import Config
from handoff.format import render_handoff
from handoff.graph.connection import connect
from handoff.graph.decisions import add_decision
from handoff.graph.edits import add_edit
from handoff.graph.history import handoff_requests
from handoff.graph.needs import add_need
from handoff.graph.requests import add_request
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session

g = connect(Config.from_env())
ensure_schema(g)
upsert_session(g, session_id="fe", role="frontend", cwd="/w", at=1)
add_request(g, session_id="fe", request_id="p1", text="Show the avatar on the profile card", at=2)
add_edit(g, request_id="p1", edit_id="e1", tool="Edit", path="ProfileCard.tsx", summary="+<img>", at=3)
add_decision(g, request_id="p1", decision_id="d1", text="read avatarUrl from GET /users/:id",
             reason="the server owns image URLs", topic="profile", at=4)
add_need(g, request_id="p1", need_id="n1", text="return avatarUrl", for_role="backend", at=5)
print(render_handoff(handoff_requests(g, role="frontend", since=0)))
EOF
```

- [ ] Merge and tag `phase-1` as in Phase 0. Notebook: change-log row.
- [ ] Write Phase 2's steps in full into this plan.

---

## Phase 2: Capture hooks

Branch: `phase/2-hooks`. Steps are written at the Phase 1 gate.

### Task 2.1: Redaction

- Create `src/handoff/redact.py`, `tests/test_redact.py`.
- Produces `redact(text: str) -> str`, replacing each match with `[redacted]`.
- Patterns: Anthropic keys (`sk-ant-…`), OpenAI-style keys (`sk-…` 20+ chars), AWS access key ids (`AKIA` + 16), GitHub tokens (`ghp_`, `gho_`, `ghs_`, `github_pat_`), Slack tokens (`xox[abprs]-`), `Bearer <token>`, PEM private key blocks, and `password|secret|token|api_key = <value>` assignments.
- Tests: one per pattern; ordinary prose and code are unchanged.

### Task 2.2: Replay file

- Create `src/handoff/spool.py`, `tests/test_spool.py`.
- Produces `append(home: Path, event: Mapping[str, object]) -> None` and `replay(home: Path, apply: Callable[[dict[str, object]], None]) -> int` (returns events applied; events whose `apply` raises stay in the file, in order). File `home/spool.jsonl`, guarded by `fcntl.flock`.
- Tests: append then replay applies in order; a failing event is kept and later ones still apply; replay of a missing file returns 0; concurrent appends from two processes produce two whole lines.

### Task 2.3: Hook handlers

- Create `src/handoff/hooks/__init__.py`, `src/handoff/hooks/edits.py`, `src/handoff/hooks/events.py`, `tests/hooks/fixtures/*.json`, `tests/hooks/test_edits.py`, `tests/hooks/test_events.py`.
- Produces:
  - `edits.summarise(tool_name: str, tool_input: Mapping[str, object]) -> str`: unified diff of `old_string`→`new_string` for `Edit`; `"wrote N lines"` plus the first lines for `Write`; cell summary for `NotebookEdit`; capped at 40 lines / 4,000 characters.
  - `edits.relative_path(file_path: str, project_dir: str) -> str`: relative inside the project, absolute outside it.
  - `events.HookInput` frozen dataclass parsed from stdin JSON: `session_id`, `prompt_id: str | None`, `cwd`, `hook_event_name`, `prompt`, `tool_name`, `tool_input`, `tool_use_id`, `stop_hook_active`.
  - `events.on_session_start(graph, hook, role, at)`, `events.on_user_prompt(graph, hook, role, at) -> str` (stdout text), `events.on_post_tool_use(graph, hook, role, project_dir, at) -> dict | None` (JSON output).
- Tests: fixtures copied from the hooks reference; prompt recorded under `prompt_id`, redacted and capped; edit recorded under `tool_use_id` with relative path; `test_edit_without_prompt_id_attaches_to_latest_request`; non-edit tools record nothing.

### Task 2.4: Entry point

- Create `src/handoff/hooks/cli.py`, `tests/hooks/test_cli.py`; add `[project.scripts] handoff-hook = "handoff.hooks.cli:main"`.
- `main()` reads the event name from `argv[1]` and JSON from stdin, replays the spool, runs the handler, prints its output; on a connection error appends the event to the spool. Note from the Phase 0 review: `connect()` itself talks to the server (FalkorDB's constructor runs `INFO`), and failures raise `redis.exceptions.ConnectionError` or `TimeoutError`, not the builtins, so the fallback wraps `connect()` and every query and catches `redis.exceptions.RedisError`; on any other exception logs it; always exits 0 (the waiter in Phase 4 is the exception).
- Tests run `handoff-hook` as a subprocess: with the database up the request appears; with `HANDOFF_DB_PORT` pointing at a closed port the event lands in the spool and the exit code is 0; a later run with the database up replays it.

### Phase 2 gate

- Show it working: in a scratch folder, add the hooks to `.claude/settings.local.json` by hand, run `HANDOFF_ROLE=frontend claude`, ask for a small edit, and see the `Session → Request → Edit → File` chain in the browser.

---

## Phase 3: MCP server

Branch: `phase/3-mcp`. Before writing steps: read the installed `mcp` 2.3 package's server API (`FastMCP` or its successor) and record the exact decorator and run calls here.

### Task 3.1: Tool logic

- Create `src/handoff/mcp/__init__.py`, `src/handoff/mcp/tools.py`, `tests/mcp/test_tools.py`.
- Produces `ToolContext(graph, role: str, cwd: str, now: Callable[[], int])` and plain functions returning text for Claude: `record_decision(ctx, text, reason, topic)`, `record_need(ctx, for_role, text)`, `resolve_need(ctx, need_id)`, `sessions(ctx, within_minutes=120)`, `handoff(ctx, role: str | None, since_minutes=240, limit=10)`, `why(ctx, path)`.
- Writes attach to `latest_request_id(active_session(role, cwd))`; with no active session or request they return a sentence saying so instead of raising.
- Tests for each function against a real graph, including the no-session case.

### Task 3.2: Server

- Create `src/handoff/mcp/server.py`; add `handoff-mcp = "handoff.mcp.server:main"`.
- Registers each tool with a one-line description written for the agent, reads `HANDOFF_ROLE` and `CLAUDE_PROJECT_DIR`, calls `ensure_schema` once at start.
- Test: start the server over stdio with the `mcp` client in a test and list its tools.

### Phase 3 gate

- Show it working: add the server to the scratch folder's `.mcp.json`, run two sessions (`frontend`, `backend`), record a decision and a need in one, call `handoff` from the other.

---

## Phase 4: Finish check and live messages

Branch: `phase/4-messages`.

### Task 4.1: Finish check

- `requests.request_needs_decision(graph, request_id) -> bool` (has an edit, has no decision).
- `events.on_stop(graph, hook, at) -> dict | None` returns `{"decision": "block", "reason": "No decision is recorded for this request yet; record_decision records it."}` when needed and `stop_hook_active` is false.
- Tests: blocks once; never blocks when `stop_hook_active`; never blocks a request without edits; allows the stop when the database is down.

### Task 4.2: Messages in the graph

- `messages.add_message(graph, *, message_id, from_session_id, to_role, kind, text, reply_to: str | None, at) -> bool` in new module `src/handoff/graph/messages.py`.
- `messages.claim_pending_messages(graph, *, session_id, role, at) -> list[MessageView]`: in one query, matches messages to `role` from other sessions with no `DELIVERED_TO` edge to this session, creates the edge, returns them oldest first.
- `MessageView(id, kind, from_role, text, reply_to, at)` in `records.py`.
- Tests: delivered once; not delivered to the sender; `test_role_message_reaches_each_session_once`; replies keep `REPLY_TO`.

### Task 4.3: Delivery and the `send_message` tool

- `tools.send_message(ctx, to_role, text, reply_to=None)`.
- `on_user_prompt` appends pending messages and open needs for the role to its stdout text; `on_post_tool_use` returns them as `additionalContext` for every tool.
- `format.render_messages(messages) -> str`, stated as facts: `Message from backend (12:04): "…"`.
- Tests for both delivery points and the rendering.

### Task 4.4: The waiter

- `src/handoff/hooks/waiter.py`, run as `handoff-hook wait`, registered on `Stop` and `SessionStart` with `"asyncRewake": true` and `"timeout": 3600`.
- Takes a lock file `home/locks/<session_id>.lock` (non-blocking); if held, exits 0. Polls `claim_pending_messages` every 2 seconds until `HANDOFF_WAIT_SECONDS` (default 3500); on messages writes `render_messages` to stderr and exits 2; on timeout or database error exits 0.
- Tests run the waiter as a subprocess with `HANDOFF_WAIT_SECONDS=5`: exits 2 with the message on stderr when one is sent; exits 0 on timeout; a second waiter for the same session exits 0 at once.

### Phase 4 gate

- Show it working: three sessions; the frontend's finish check fires once; the backend sends a message to `deploy`; the idle deploy session wakes and shows it.

---

## Phase 5: Stand-in answers

Branch: `phase/5-standin`. No API key and no new dependency: the stand-in runs Claude Code headless on the person's existing login. Command, verified 17 October: `claude -p --output-format json --model haiku --tools "" --setting-sources "" --strict-mcp-config --no-session-persistence`, prompt on stdin, run from a temporary folder; the answer text is the `result` field of the JSON.

### Task 5.1: Context gathering

- `standin/context.py`: `StandinContext(role, requests: tuple[RequestView, ...], messages: tuple[MessageView, ...])` and `gather_context(graph, role, since, limit) -> StandinContext`; `context_ids(ctx) -> set[str]`.
- Tests: includes requests, decisions, needs and messages of that role only; respects the limit.

### Task 5.2: The model call

- `standin/answer.py`: `ModelClient` protocol with `complete(system: str, user: str) -> str`; `ClaudeCodeClient` (runs the command above with `subprocess.run`, 60-second timeout, system text passed with `--system-prompt`, raises `StandinUnavailable` on a missing binary, non-zero exit, timeout or unparseable JSON); `StandinAnswer(text: str, cited_ids: tuple[str, ...], found: bool)`; `answer(client, context, question) -> StandinAnswer`.
- The model returns JSON `{"answer": str, "cited_ids": [str], "found": bool}`. Unknown cited ids are dropped; unparseable output becomes `found=False` with a plain sentence.
- Tests with a fake client: valid answer; invented id dropped; garbage output handled; `ClaudeCodeClient` with a missing binary raises `StandinUnavailable`; one live test runs only when `HANDOFF_LIVE_TESTS=1`.

### Task 5.3: The `ask` tool

- `tools.ask(ctx, role, question, client: ModelClient)`: stores the question as a `question` message to `role` (so the real session gets it and its waiter wakes it), calls the stand-in, stores the answer as a `standin_answer` message replying to the question with `CITES` edges, returns text beginning `Stand-in answer for <role> (from recorded history, not the live session):`.
- When the client raises `StandinUnavailable`: returns that the question was delivered and no stand-in answer is available.
- Tests for both paths and the stored graph shape.

### Phase 5 gate

- Show it working: the backend asks the frontend a question answered by a recorded decision; the answer cites it; the idle frontend session wakes with the question.

---

## Phase 6: Search by meaning

Branch: `phase/6-search`. Dropped if Phase 4 has not passed its gate by Sunday 13:00. Before writing steps: confirm `fastembed` 0.9's model list and the embedding size of the chosen small English model.

### Task 6.1: Embeddings

- `embed.py`: `embed(texts: Sequence[str]) -> list[list[float]]`, model loaded once and cached under `home/models`.
- Tests: fixed size; similar sentences closer than unrelated ones.

### Task 6.2: Vector indexes and topic reuse

- `schema.ensure_vector_schema(graph, dim)`; `add_decision` stores `vecf32` embeddings; topics reuse the nearest existing topic above a threshold set from a small labelled list of pairs in the tests.
- Tests: "auth tokens" and "login tokens" share a topic; "auth tokens" and "css grid" do not.

### Task 6.3: `search` tool

- `decisions.similar_decisions(graph, vector, k) -> list[tuple[DecisionView, str, float]]` (decision, role, score); `tools.search(ctx, query, k=5)`; stand-in context adds the top matches.

---

## Phase 7: Ship

Branch: `phase/7-ship`.

### Task 7.1: Installer

- `install.py`, command `handoff install <workspace>`: merges hook entries into `<workspace>/.claude/settings.local.json` and the server into `<workspace>/.mcp.json` without removing existing entries; prints the launch command for each role.
- Tests: fresh workspace; workspace with existing settings keeps them; running twice adds nothing.

### Task 7.2: End-to-end run

- `scripts/e2e_scenario.sh`: three `claude -p` runs with different `HANDOFF_ROLE` values against a scratch workspace, then a Python check that the deploy handoff contains the frontend request, the resolved need and the backend request.

### Task 7.3: README and licence

- README: problem, how it works (graph diagram), setup in three commands, demo walkthrough, graph schema, design decisions, limits.
- `LICENSE` (MIT).

### Task 7.4: Submission (you)

- Record the demo video, write the blog post, submit on the WeMakeDevs panel before 18 October 11:59 PM IST.
