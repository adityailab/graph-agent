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
| 7 Knowledge layer (GraphRAG-SDK, FalkorDB MCP, three model backends) | 6 h | Sat evening |
| 8 Ship | 4 h | Sun afternoon |
| 9 Coordinator (stretch) | 3 h | Sun evening, only with time to spare |

Phase 6 was revised and expanded on 17 October (FalkorDB-native search); the schedule allows it.

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
  - `WhyRow(role: str, request_text: str, decisions: tuple[DecisionView, ...], edit_summary: str, at: int)` (changed at the Phase 1 gate: one row per edit)
  - `decision_views(raw) -> tuple[DecisionView, ...]`, shared row parser
- Produces, in `reads.py`:
  - `latest_request_id(graph, session_id: str) -> str | None` (latest by time, so a late replay never counts as latest)
  - `active_session(graph, *, role: str, cwd: str) -> SessionInfo | None` (most recently seen)
  - `active_sessions(graph, *, since: int) -> list[SessionInfo]` (seen at or after `since`, ordered by role)
  - `why_file(graph, path: str, limit: int = 20) -> list[WhyRow]` (one row per edit, newest first)
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

**Changed at the Phase 2 gate review** (code is the source of truth):
- `hooks/prepare.py` `prepare_hook_input(data, project_dir) -> dict` slims, redacts and caps raw hook input and fills every id the moment the hook fires; only this slim form is applied or saved.
- `HookInput` now carries `edit_path` and `edit_summary` instead of `tool_input`; `on_post_tool_use(graph, hook, *, role, at)` (no `project_dir`).
- Saved event shape: `{"input": prepared, "role", "at"}`.
- `spool.replay(home, apply, *, is_outage) -> ReplayResult(applied, pending)`: stops at the first outage, at most `MAX_REPLAY` (100) per call, bad events go to `spool.dead.jsonl`, files are 0600, rewrite is atomic. When `pending`, the live event is queued behind the saved ones.
- `cli.is_outage(exc)`: only redis `ConnectionError`/`TimeoutError` count as the database being down.

### Phase 2 gate

- Show it working: in a scratch folder, add the hooks to `.claude/settings.local.json` by hand, run `HANDOFF_ROLE=frontend claude`, ask for a small edit, and see the `Session → Request → Edit → File` chain in the browser.

---

## Phase 3: MCP server

Branch: `phase/3-mcp`. Checked 17 October against `mcp` 2.3.0: `FastMCP` is now `MCPServer`, imported from `mcp.server.mcpserver`. Construct with `MCPServer(name, instructions=...)`, register with `@server.tool(description=...)`, run with `server.run("stdio")`. `await server.list_tools()` lists tools in-process, so the server test needs no subprocess (async tests via anyio's pytest plugin, which `mcp` installs).

### Task 3.1: Tool logic

- Create `src/handoff/mcp/__init__.py`, `src/handoff/mcp/tools.py`, `tests/mcp/test_tools.py`.
- Produces `ToolContext(graph, role: str, cwd: str, now: Callable[[], int])` and plain functions returning text for Claude: `record_decision(ctx, text, reason, topic)`, `record_need(ctx, for_role, text)`, `resolve_need(ctx, need_id)`, `sessions(ctx, within_minutes=120)`, `handoff(ctx, role: str | None, since_minutes=240, limit=10)`, `why(ctx, path)`.
- Writes attach to `latest_request_id(active_session(role, cwd))`; with no active session or request they return a sentence saying so instead of raising.
- Input checks: an empty or whitespace-only text, reason, topic or role is refused with a sentence saying which field is empty (Phase 1 review: `normalise_topic` turns blank into `""`).
- Tests for each function against a real graph, including the no-session case.

### Task 3.2: Server

- Create `src/handoff/mcp/server.py`; add `handoff-mcp = "handoff.mcp.server:main"`.
- Registers each tool with a one-line description written for the agent, reads `HANDOFF_ROLE` and `CLAUDE_PROJECT_DIR`, calls `ensure_schema` once at start.
- Test: start the server over stdio with the `mcp` client in a test and list its tools.

**Changed at the Phase 3 gate review** (code is the source of truth):
- Tools live in `mcp/context.py`, `mcp/record_tools.py`, `mcp/read_tools.py`; `mcp/server.py` only wires them.
- `ToolContext(*, role, cwd, graph=None, connect=None, now)`; `ToolContext.lazy(connect=, role=, cwd=)` connects and applies the schema on the first call, so the server starts while FalkorDB is down. `context_from_env(env, *, cwd, connect)` resolves the project folder and normalises the role.
- `@guarded` turns a database outage into the sentence `UNREACHABLE` instead of a tool error.
- `current_session(ctx)` and `current_request(ctx) -> CurrentRequest(id, text, note)`; `note` warns when several sessions share a role and folder (`sessions.count_sessions`).
- `config.normalise_role`: roles are lower-case and trimmed everywhere.
- Handoff text shows need ids: `(open, id <id>)`, so another role can resolve them.
- Hooks store `Session.cwd` as the resolved `CLAUDE_PROJECT_DIR`.

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

- `src/handoff/hooks/waiter.py`, run as `handoff-hook wait`, registered on `Stop` only (not `SessionStart`, see spec 4.5) with `"asyncRewake": true` and `"timeout": 3600`.
- Takes a lock file `home/locks/<session_id>.lock` (non-blocking); if held, exits 0. Polls `claim_pending_messages` every 2 seconds until `HANDOFF_WAIT_SECONDS` (default 3500); on messages writes `render_messages` to stderr and exits 2; on timeout or database error exits 0.
- Tests run the waiter as a subprocess with `HANDOFF_WAIT_SECONDS=5`: exits 2 with the message on stderr when one is sent; exits 0 on timeout; a second waiter for the same session exits 0 at once.

**Changed at the Phase 4 gate review** (code is the source of truth):
- `hooks/generation.py` (`bump`, `current`): each waiter and each new prompt writes a token; a waiter whose token is stale quits. The waiter waits up to 3 polls for the lock.
- Outages: Stop events and tool calls that edited nothing are not saved to the replay file.
- `messages.has_pending_messages` (read-only) runs before any claim; the claim keeps one row per message.
- Indexes on `Message.to_role` and `Need.for_role`; `render_messages` caps at `MAX_MESSAGES` (20), 500 characters each.
- The finish check's reason is `events.FINISH_CHECK_REASON`; it checks the turn's prompt if recorded, else the latest request.

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

**Changed during Phase 5** (code is the source of truth):
- Stand-in modules: `standin/context.py` (`StandinContext`, `gather_context(graph, *, role, since, limit)`, `context_ids`), `standin/prompt.py` (`build_prompt`), `standin/answer.py` (`ModelClient`, `StandinUnavailable`, `StandinAnswer`, `parse_answer`, `answer`), `standin/claude_code.py` (`ClaudeCodeClient`, default model `opus`, `HANDOFF_STANDIN_MODEL` to change). `mcp/ask_tool.py` holds `ask`.
- `messages.role_messages` (read-only) and `messages.add_citations`.
- The waiter exits at once when `CLAUDE_CODE_SESSION_ATTENDED=0`: `claude -p` waits for asyncRewake hooks before exiting.
- MCP servers receive `CLAUDE_CODE_SESSION_ID`; `ToolContext.session_id` finds the exact session (`sessions.get_session`), with role and folder as the fallback. Lookup lives in `mcp/current.py`.

### Phase 5 gate

- Show it working: the backend asks the frontend a question answered by a recorded decision; the answer cites it; the idle frontend session wakes with the question.

---

## Phase 6: FalkorDB-native search and graph relevance

Branch: `phase/6-search`. Revised on 17 October after a survey of FalkorDB 4.22.1
features, each checked live: vector index (score is a cosine *distance*, lower is
closer), full-text index with parameters, `algo.*` procedures, unique constraints,
UDFs/FLEX, and `shortestPath` (allowed only in `WITH`/`RETURN`). FalkorDB has no
graph-embedding feature and does not compute embeddings. Model:
`BAAI/bge-small-en-v1.5` via fastembed 0.9 (384 dimensions; "auth tokens" vs "login
tokens" 0.82 cosine similarity, vs "css grid" 0.44). Embeddings are computed only in
the long-lived MCP server, never in hooks.

### Task 6.1: Schema: constraints, full-text and vector indexes
- `schema.ensure_schema` adds unique constraints on every id and `Topic.name`, full-text
  indexes on `Request.text`, `Decision.text`+`reason`, `Need.text`, `Message.text`, and
  vector indexes (384, cosine) on `Decision.embedding` and `Topic.embedding`.
- Tests: all present after one call; a second call changes nothing; a duplicate id is
  rejected by the constraint.

### Task 6.2: Embeddings
- `embed.py`: `Embedder` protocol (`embed(texts) -> list[list[float]]`), `FastEmbedder`
  (loads on first use, cache in `home/models`), `EMBED_DIM = 384`.
- Tests: fake embedder in unit tests; one live test under `HANDOFF_LIVE_TESTS=1` checks
  the dimension and that paraphrases are closer than unrelated text.

### Task 6.3: Search queries
- `graph/search.py`: `fulltext_decisions(graph, query, k)`, `similar_decisions(graph,
  vector, k)` (distance), `decision_context(graph, ids)` (role, request, files, and other
  sessions that touched the same files). `decisions.add_decision` takes an optional
  `embedding`.
- Tests: exact term found by full-text, paraphrase found by vector, expansion finds the
  other session that edited the same file.

### Task 6.4: The `search` tool
- `mcp/search_tool.py`: `search(ctx, query, k=5, embedder)`: full-text and vector hits
  merged by reciprocal rank fusion, then expanded through the graph; each result names
  its role, request, reason, files, and related sessions.

### Task 6.5: Topic reuse by meaning and by graph
- `decisions.resolve_topic`: reuse the nearest existing topic when its embedding is within
  the distance threshold, or when it is a little further but its decisions touched the
  same files as this request; otherwise a new topic. Threshold set from tests.

### Task 6.6: Stand-in context by relevance
- `gather_context` adds the role's decisions that match the question (hybrid search),
  beyond the recency window, so an old but relevant decision is not missed.

### Task 6.7: Colliding edits
- `graph/overlaps.py`: `recent_edits_by_others(graph, path, session_id, since)`.
- After an edit, the PostToolUse hook adds a fact when another role changed the same
  file recently: which role, when, and its request. `handoff` lists files changed by more
  than one role.

### Task 6.8: How two pieces of work connect
- `connection` tool: the shortest path (FalkorDB `shortestPath`) between this session's
  latest request and another role's, through files, needs and messages, rendered hop by
  hop. Shown in the demo.

### Phase 6 gate
- Live: two sessions edit the same file and the second is told; `search` finds a
  paraphrased decision; `connection` shows the path; the stand-in uses an old decision.

---

## Phase 7: Knowledge layer: GraphRAG-SDK, FalkorDB MCP, three model backends

Branch: `phase/7-knowledge`. Added 17 October at Aditya's request ("GraphRAG-SDK +
FalkorDB MCP", models: "all three"). Facts from the research (graphrag-sdk 1.4.0,
@falkordb/mcpserver 1.3.0) are in the ledger.

Design:
- **Two layers.** The provenance backbone (graph `handoff`) keeps its shape. The
  knowledge layer lives in its own graph, `<graph>_kg`, built by GraphRAG-SDK from the
  text of requests and decisions. Its ontology is not hard-coded: the model proposes it
  from the recorded text and extends it as new subjects appear.
- **Link between graphs.** Each ingested text is a GraphRAG `Document` whose id is our
  Request or Decision id. Cross-graph joins happen in Python.
- **Optional install.** `graphrag-sdk` pulls torch (about 1 GB), so it is the extra
  `handoff[knowledge]`. Without it the knowledge tools say so and everything else works.
- **Models.** One `ModelClient` protocol, three backends chosen by `HANDOFF_MODEL`
  (`claude-code` default, `anthropic`, `ollama`), used by both the stand-in and GraphRAG.

### Task 7.1: Model backends
- `handoff/models/`: `ModelClient` (moved from standin), `claude_code.py` (moved),
  `anthropic_api.py` (official `anthropic` SDK, model `claude-opus-5-5`, needs
  `ANTHROPIC_API_KEY`), `ollama.py` (`POST /api/chat`, `format: "json"`, default model
  `qwen2.5:7b`), `choose.py` (`model_from_env(env) -> ModelClient`).
- Tests: each backend's request shape with a fake transport; selection by env; live
  tests gated by `HANDOFF_LIVE_TESTS` and the backend being available.

### Task 7.2: GraphRAG adapters
- `knowledge/adapters.py`: an `LLMInterface` subclass wrapping any `ModelClient`
  (concurrency 1 for `claude-code`), an `Embedder` adapter wrapping `FastEmbedder` (384).
- Verify at task start, live: ingest of plain text with `document_id`, ontology
  discovery from text, `completion()`, provenance query back to document ids.

### Task 7.3: Ontology that grows
- `knowledge/ontology.py`: discover an ontology from the first texts with the model;
  extend it from new texts with `suggest_schema_extensions` on a schedule. Nothing about
  the project's subject is written in code.

### Task 7.4: Ingestion worker
- `knowledge/worker.py`: a background thread in the MCP server. It claims un-ingested
  Requests and Decisions from `handoff` (a claim property, set in one query so several
  servers never double-ingest), ingests each into `<graph>_kg`, and runs `finalize()`
  every few minutes. Failures leave the item unclaimed for a later try.

### Task 7.5: Knowledge tools
- `ask_graph(question)`: GraphRAG `completion()`; the answer plus the requests and
  decisions it drew on (via document ids), with their roles.
- `concepts(query)`: entities matching a query and which sessions' work mentions them.
- `search` and the stand-in add work linked by shared concepts, not only shared files.

### Task 7.6: FalkorDB MCP server alongside ours
- The installer (Phase 8) adds `@falkordb/mcpserver@1.3.0` to `.mcp.json` with
  `FALKORDB_STRICT_READONLY=true`, so agents can write their own read-only Cypher
  against both graphs. Here: a config builder function and its test.

**As built** (code is the source of truth): `models/` (base, claude_code, anthropic_api, ollama, choose); `knowledge/` (adapters, worker with `drain()`, startup → `Knowledge(rag, kg, worker)`, answers, cli); `graph/knowledge_queue.py`, `graph/knowledge.py`; `mcp/knowledge_tools.py` (`ask_graph`, `concepts`); `mcp_config.py`; console script `handoff-knowledge [--once]`. Task 7.3 needed no module: with no ontology given, GraphRAG-SDK extracts whatever entity types the text holds.

### Phase 7 gate
- Live: a decision about `avatarUrl` in one session and a request mentioning it in
  another are linked through a concept; `ask_graph` answers a cross-session question with
  sources; the FalkorDB MCP server lists both graphs and refuses a write.

---

## Phase 8: Ship

Branch: `phase/8-ship`. (Was Phase 7.)



### Task 8.1: Installer

- `install.py`, command `handoff install <workspace>`: merges hook entries into `<workspace>/.claude/settings.local.json` and the server into `<workspace>/.mcp.json` without removing existing entries; prints the launch command for each role.
- Tests: fresh workspace; workspace with existing settings keeps them; running twice adds nothing.

### Task 8.2: End-to-end run

- `scripts/e2e_scenario.sh`: three `claude -p` runs with different `HANDOFF_ROLE` values against a scratch workspace, then a Python check that the deploy handoff contains the frontend request, the resolved need and the backend request.

### Tasks 8.3 and 8.4: moved

README, licence and submission moved to Phase 10, so they describe the product built in
Phase 9 (`handoff init`, the CLI, the live demo). Phase 8 instead carried the fixes from
the graph review (17 October): a graph per workspace, readable node names, CONSULTED
edges, knowledge-graph quality, stand-in citations; see the ledger.

### Phase 8 gate

`make check` green; `scripts/e2e_scenario.sh` PASS (deploy handoff complete, a delivered
message, a cited stand-in answer, a CONSULTED edge); fresh opus review, fix pass; merge
`--no-ff`, tag `phase-8`, notebook updated.

---


---

# Product phases (from the 17 October product spec)

**Goal:** handoff installed with one command, used from a CLI, visibly working (live
tmux demo, live feed, FalkorDB Browser), with agents writing their own read-only Cypher
and FalkorDB algorithms surfacing what matters.

**Architecture:** a thin `handoff` dispatcher over one module per command in
`handoff/cli/`; Docker and tmux calls go through one injectable runner; all new Cypher in
`handoff.graph` (`introspect`, `insights`, `feed`, `udf`); the guide text as data in
`handoff/guide/`. No custom dashboard and no text-to-Cypher engine of our own (spec §2).

**Tech stack:** as before, plus tmux (optional, for `demo --live`). No new Python
dependencies.

**Spec:** `docs/superpowers/specs/2026-10-17-handoff-product-design.md`

## Global constraints (product phases)

- One-line install: `uv tool install git+https://github.com/adityailab/graph-agent && handoff init`.
- FalkorDB image `falkordb/falkordb:v4.22.1`, container `handoff-falkordb`, volume
  `handoff-data`, ports bound to `127.0.0.1` only (6379, 3000).
- LLM-written Cypher runs only through FalkorDB's MCP server in strict read-only mode
  (`FALKORDB_STRICT_READONLY=true`), under FalkorDB's 1 s default query timeout.
- No API key required; `ask` and `demo` spend the person's plan and say so first; the
  headless demo uses Haiku.
- CLI failures from missing prerequisites: exit code 1, one plain sentence and a fix, no
  traceback.
- The CLAUDE.md rules: modules ≤ ~150 lines, functions ≤ ~40, Cypher only in
  `handoff.graph`, `$params`, entry points thin, test first.

## Review focus (product phases)

1. `handoff init` where a FalkorDB is already listening on 6379 (e.g. this repo's compose
   container): use it, never start a second container that fails on the port. Test in 9.2.
2. `handoff ask` when `claude` is missing or the FalkorDB MCP server cannot start: a clear
   message within the timeout, never a hang. Test in 9.6.
3. Insights on an empty or tiny graph: no insights and no errors, even when an `algo.*`
   procedure has no matching nodes. Test in 9.7.
4. `handoff watch` when the database goes away mid-run: it shows "database unreachable"
   and keeps retrying; Ctrl-C exits with code 0. Test in 9.11.
5. `handoff send` to a role with no session yet: stored, says no live session has that
   role, delivered when one starts. Test in 9.4.

---

## Phase 9: The product

Branch: `phase/9-product`. Slices A–D are each mergeable; the gate is at the end.

### Task 9.1: The `handoff` dispatcher and the workspace's graph

**Files:**
- Create: `src/handoff/cli/__init__.py`, `src/handoff/cli/app.py`, `src/handoff/workspace.py`
- Modify: `src/handoff/main.py` (becomes `from handoff.cli.app import main`)
- Test: `tests/cli/test_app.py`, `tests/test_workspace.py`

**Interfaces:**
- Produces: `workspace_graph(folder: Path, env: Mapping[str, str]) -> str` (settings
  `env.HANDOFF_GRAPH`, else `env["HANDOFF_GRAPH"]`, else `graph_for_workspace(folder)`);
  `workspace_config(folder: Path, env: Mapping[str, str]) -> Config` (Config.from_env with
  that graph name); `cli.app.main(argv: list[str] | None = None) -> int`; each command
  module exposes `add_parser(commands) -> None` and `run(args) -> int`.

- [ ] Step 1: tests:
```python
def test_installed_folder_uses_the_graph_in_its_settings(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text('{"env": {"HANDOFF_GRAPH": "shop"}}')
    assert workspace_graph(tmp_path, {"HANDOFF_GRAPH": "other"}) == "shop"

def test_environment_then_folder_default(tmp_path: Path) -> None:
    assert workspace_graph(tmp_path, {"HANDOFF_GRAPH": "g"}) == "g"
    assert workspace_graph(tmp_path, {}) == graph_for_workspace(tmp_path)

def test_broken_settings_fall_back_to_the_default(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text("{not json")
    assert workspace_graph(tmp_path, {}) == graph_for_workspace(tmp_path)

def test_every_command_is_listed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for name in ("init", "install", "status", "log", "send", "ask", "insights", "watch",
                 "knowledge", "demo", "doctor"):
        assert name in out
```
- [ ] Step 2: run, expect ImportError.
- [ ] Step 3: implement `workspace.py`; `cli/app.py` builds `argparse` subparsers from a
  tuple of command modules (each `add_parser`, `set_defaults(run=module.run)`), then
  `return args.run(args)`. Commands not built yet are added by their tasks; this task
  wires `install` (moved from `main.py`) and `knowledge` (calls `knowledge.cli.main`).
- [ ] Step 4: tests pass; `make check`.
- [ ] Step 5: commit `feat(cli): add the handoff command dispatcher and per-folder graph lookup`.

### Task 9.2: `handoff init`: prerequisites, database, install

**Files:**
- Create: `src/handoff/cli/runner.py`, `src/handoff/prereqs.py`, `src/handoff/database.py`,
  `src/handoff/cli/init_cmd.py`
- Test: `tests/test_prereqs.py`, `tests/test_database.py`, `tests/cli/test_init_cmd.py`

**Interfaces:**
- Produces: `Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]`,
  `run_command(args) -> CompletedProcess[str]` (no shell, text, 60 s timeout);
  `Problem(name: str, fix: str)` frozen dataclass;
  `check_prerequisites(runner: Runner, which: Callable[[str], str | None]) -> list[Problem]`
  (docker info ok; `claude` and `npx` on PATH; `npx` missing is reported with
  `optional=True` field);
  `database_reachable(config: Config) -> bool` (ping);
  `ensure_database(config: Config, runner: Runner, *, wait_seconds: float = 30) -> str`
  returning one of "running", "started", "created"; raises `DatabaseUnavailable(str)`.
- Consumes: `install(...)` from `handoff.install`, `ping` from `handoff.graph.connection`.

- [ ] Step 1: tests (fake runner records argv and returns canned results):
```python
def test_a_reachable_database_is_used_as_is(config: Config) -> None:
    calls: list[list[str]] = []
    assert ensure_database(config, fake_runner(calls)) == "running"   # real FalkorDB is up
    assert calls == []                      # review focus 1: no docker call at all

def test_a_stopped_container_is_started(tmp_path: Path) -> None:
    down = Config("localhost", 1, "g", tmp_path)       # nothing listens on port 1
    calls: list[list[str]] = []
    runner = fake_runner(calls, {("docker", "ps", "-a"): "handoff-falkordb\n"})
    with pytest.raises(DatabaseUnavailable):           # still unreachable after start
        ensure_database(down, runner, wait_seconds=0.2)
    assert ["docker", "start", "handoff-falkordb"] in calls

def test_no_container_runs_the_pinned_image_on_localhost(tmp_path: Path) -> None:
    down = Config("localhost", 1, "g", tmp_path)
    calls: list[list[str]] = []
    with pytest.raises(DatabaseUnavailable):
        ensure_database(down, fake_runner(calls, {("docker", "ps", "-a"): ""}), wait_seconds=0.2)
    run = next(c for c in calls if c[:2] == ["docker", "run"])
    assert run[2:] == ["-d", "--name", "handoff-falkordb",
                       "-p", "127.0.0.1:6379:6379", "-p", "127.0.0.1:3000:3000",
                       "-v", f"handoff-data:{DATA_DIR}", "falkordb/falkordb:v4.22.1"]

def test_missing_docker_is_one_problem_with_a_fix() -> None:
    problems = check_prerequisites(failing_runner(), which=lambda name: f"/bin/{name}")
    assert [p.name for p in problems] == ["docker"]
    assert "Docker" in problems[0].fix
```
  Data directory: run `docker inspect graph-agent-falkordb-1 --format '{{json .Mounts}}'`
  and the image's `Config.Volumes` first; use the image's declared data path (ledger a
  Ruling with what was found).
- [ ] Step 2: run, expect failures.
- [ ] Step 3: implement. `init_cmd.run`: prerequisites (hard ones stop with exit 1 and
  each fix; npx missing → install with `falkordb_mcp=False` and a note), then
  `ensure_database`, then `install(folder, ...)`, then print its instructions.
- [ ] Step 4: tests pass; `make check`; live: `handoff init` in a scratch folder against
  the running compose database prints "running" and installs.
- [ ] Step 5: commit `feat(cli): add handoff init (prerequisites, database, install)`.

### Task 9.3: `status`, `log`, `doctor`

**Files:** Create `src/handoff/cli/status.py`, `log_cmd.py`, `doctor.py`; tests in `tests/cli/`.

**Interfaces:**
- Consumes: `active_sessions(graph, since=)`, `latest_request_id`, `request_text`,
  `count_open_needs(graph, role)`, `handoff_requests(graph, role=, since=)`,
  `select_requests`, `render_handoff`, `workspace_config`.
- Produces: `knowledge_leader(config: Config) -> bool` in `knowledge/worker.py` (true when
  the lead lock file is held, tried with a non-blocking lock and released at once), shown
  by `status` as "knowledge worker: running / not running";
  `doctor.findings(folder: Path, config: Config) -> list[str]` (empty = healthy):
  hooks present in settings, `.mcp.json` has `handoff`, database reachable, the last 5
  ERROR lines of `<home>/logs/hooks.log` from the last hour.

- [ ] Step 1: tests: `status` on `two_sessions` lists frontend and backend with their
  current request and "1 open need for backend"; `log frontend` prints the frontend block
  of `render_handoff`; `doctor` on a fresh folder reports "hooks not installed — run
  handoff init"; on an installed folder with an unreachable port reports the database.
- [ ] Step 2–4: red, implement, green, `make check`.
- [ ] Step 5: commit `feat(cli): add status, log and doctor`.

### Task 9.4: `handoff send` (the person as a participant)

**Files:** Create `src/handoff/cli/send.py`; Modify `src/handoff/graph/sessions.py`
(`person_session_id(cwd: str) -> str`); test `tests/cli/test_send.py`.

**Interfaces:**
- Consumes: `upsert_session(graph, session_id=, role="person", cwd=, at=)`,
  `add_message(graph, message_id=, from_session_id=, to_role=, kind="message", text=, reply_to=None, at=)`,
  `normalise_role`.
- Produces: `person_session_id(cwd) -> str` = `"person-" + sha256(f"{hostname}:{cwd}")[:12]`.

- [ ] Step 1: tests: after `send backend "use paise"`, `claim_pending_messages` for a
  backend session returns it from role `person`; sending to a role with no session prints
  "No session has the role backend yet; it will get this message when one starts."
  (review focus 5) and stores it; sending twice from one folder reuses one person session.
- [ ] Steps 2–4; live: in the tmux demo, `handoff send frontend "..."` wakes the idle
  frontend pane.
- [ ] Step 5: commit `feat(cli): let a person message a session with handoff send`.

### Task 9.5: `graph_guide`

**Files:**
- Create: `src/handoff/graph/introspect.py` (`label_counts(graph) -> dict[str, int]`,
  `relationship_counts(graph) -> dict[str, int]`, `index_summary(graph) -> list[str]`),
  `src/handoff/guide/__init__.py`, `guide/model.py` (MEANINGS: tuple of
  `(pattern, meaning)`), `guide/rules.py` (RULES: tuple of str), `guide/recipes.py`
  (RECIPES: tuple of `Recipe(name, cypher, params)`), `guide/build.py`
  (`build_guide(graph: Graph, kg: Graph | None, *, graph_name: str, kg_name: str, falkordb_mcp: bool) -> str`),
  `src/handoff/mcp/guide_tool.py` (`register(server, ctx)`)
- Modify: `src/handoff/mcp/server.py` (register; one INSTRUCTIONS line), `install.py`
  is unchanged.
- Test: `tests/graph/test_introspect.py`, `tests/guide/test_build.py`,
  `tests/guide/test_recipes.py`, `tests/mcp/test_guide_tool.py`

**Interfaces:**
- Consumes: `db.meta.stats()`; `CALL db.indexes()` (columns: label, properties, types,
  options — as printed by the Phase 8 review queries).
- Produces: `Recipe` frozen dataclass; the MCP tool `graph_guide()`.

- [ ] Step 1: tests:
```python
def test_every_recipe_runs_read_only(two_sessions: Graph) -> None:
    for recipe in RECIPES:
        if recipe.graph == "kg":
            continue
        two_sessions.ro_query(recipe.cypher, recipe.params)   # raises if broken

def test_the_guide_names_this_workspaces_graphs_and_live_counts(two_sessions: Graph) -> None:
    text = build_guide(two_sessions, None, graph_name="shop", kg_name="shop_kg", falkordb_mcp=True)
    assert "graph `shop`" in text and "`shop_kg`" in text
    assert "Request: 3" in text
    assert "EXISTS" in text            # the 4.22 rules are there
    assert "query_graph_readonly" in text

def test_without_falkordbs_server_the_guide_says_so(two_sessions: Graph) -> None:
    text = build_guide(two_sessions, None, graph_name="g", kg_name="g_kg", falkordb_mcp=False)
    assert "FalkorDB's MCP server is not installed" in text
```
  Recipes (each verified in Step 4 on the test graph): full-text with fuzzy/prefix terms
  over Decision; vector `db.idx.vector.queryNodes('Decision','embedding',5,vecf32($v))`
  (kg-free, skipped when no embedding); `algo.pageRank('Request','CONSULTED')`;
  `algo.betweenness({nodeLabels:['Request','Edit','File'], relationshipTypes:['CAUSED','TOUCHED']})`;
  `algo.WCC({nodeLabels:['Edit','File'], relationshipTypes:['TOUCHED']})`; who consulted
  whose work; open needs per role; entity → documents in `_kg`.
  First confirm each `algo.*` YIELD column name with `CALL dbms.procedures()` and record
  them in the ledger.
- [ ] Steps 2–4; `make check`.
- [ ] Step 5: commit `feat(mcp): add graph_guide so sessions can write their own Cypher`.

### Task 9.6: `handoff ask`

**Files:** Create `src/handoff/cli/ask.py`, `src/handoff/cli/stream_json.py`
(`ToolCall(name, input)`, `parse_stream(lines: Iterable[str]) -> tuple[str, list[ToolCall]]`);
tests `tests/cli/test_ask.py`, `tests/cli/test_stream_json.py`, fixture
`tests/cli/data/ask_stream.jsonl` (a trimmed real `claude -p --output-format stream-json
--verbose` transcript captured in Step 4).

**Interfaces:**
- Consumes: `install`-style entries `handoff_server_entry`, `falkordb_server_entry`;
  `Runner`.
- Produces: `ask_command(question: str, *, folder: Path, config: Config, mcp_config: Path, model: str) -> list[str]`.

- [ ] Step 1: tests: `parse_stream` returns the final result text and every
  `mcp__falkordb__query_graph_readonly` call's `query`; `ask_command` contains
  `--strict-mcp-config`, `--mcp-config <file>`, `--allowedTools` with exactly
  `mcp__handoff__graph_guide mcp__handoff__handoff mcp__handoff__search mcp__falkordb__query_graph_readonly mcp__falkordb__get_graph_schema`,
  `--no-session-persistence`, and no `--permission-mode`; `run` with a runner that raises
  `FileNotFoundError` prints "Claude Code (claude) is not installed" and returns 1;
  with a runner that times out prints "No answer within 180 s" (review focus 2).
- [ ] Steps 2–4: implement (prompt: answer from the graph; call graph_guide first; query
  read-only; say which queries you ran). Before running, print one line: "This runs
  Claude Code on your plan (about one minute)." `demo` prints the same kind of line; live: `handoff ask "which decisions did deploy
  read?"` against `live` prints an answer and at least one Cypher query.
- [ ] Step 5: commit `feat(cli): add handoff ask (Claude writes read-only Cypher)`.

### Task 9.7: Insight queries and `:Insight` nodes

**Files:** Create `src/handoff/graph/insights.py`; Modify `graph/schema.py` (range index
`Insight.kind`); test `tests/graph/test_insights.py`.

**Interfaces:**
- Produces: `InsightView(kind: str, score: float, text: str, about: tuple[str, ...])`
  frozen dataclass in `records.py`; `compute_insights(graph) -> list[InsightView]`;
  `replace_insights(graph, insights: list[InsightView], *, at: int) -> None`;
  `current_insights(graph, *, limit: int) -> list[InsightView]`.
- Kinds and queries (YIELD names confirmed in 9.5): `load_bearing` from
  `algo.pageRank('Request','CONSULTED')` over requests read by 2+ other roles, text
  "<role> #<seq> \"<text>\" was read by <roles>"; `bridge` from betweenness over
  Request/Edit/File, files with score > 0 touched by 2+ roles; `collision` from WCC over
  Edit/File, components with edits from 2+ roles; `theme` from
  `algo.labelPropagation({nodeLabels:['Decision','Topic'], relationshipTypes:['ABOUT']})`,
  communities with 2+ decisions.

- [ ] Step 1: tests on a seeded graph whose answer is known: a file edited by frontend and
  backend → one `collision` about that file; a request consulted by two roles →
  `load_bearing`; an empty graph → `[]` and no error (review focus 3); replacing twice
  leaves one set; insight nodes have a `name` caption.
- [ ] Steps 2–4; `make check`.
- [ ] Step 5: commit `feat(graph): compute insights with FalkorDB algorithms`.

### Task 9.8: Insights where people and agents see them

**Files:** Create `src/handoff/cli/insights_cmd.py`; Modify `mcp/read_tools.py` (handoff
text gains "What matters now" with the top 3, refreshing when the newest insight is older
than 5 minutes), `knowledge/worker.py` (refresh after each finalize), tests.

- [ ] Step 1: tests: `handoff` tool output on a graph with a collision contains
  "What matters now" and the file; `handoff insights` prints each kind; the worker calls
  the refresh after finalize (fake rag).
- [ ] Steps 2–4; `make check`.
- [ ] Step 5: commit `feat: show insights in the handoff, the CLI and after ingestion`.

### Task 9.9: Fuzzy and prefix full-text search

**Files:** Modify `src/handoff/graph/search.py` (`fulltext_query`); test
`tests/graph/test_search.py`.

- [ ] Step 1: tests. The rule: words of 5+ letters become fuzzy `%word%` (edit distance
  1, which also matches the exact word), words of 3–4 letters become prefix `word*`,
  shorter words are dropped, all OR-ed:
```python
def test_long_words_are_fuzzy_and_short_words_are_prefixes() -> None:
    assert fulltext_query("nginz api config ok") == "%nginz% | api* | %config%"

def test_a_misspelling_still_finds_the_decision(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="r1", text="x", at=1)
    add_decision(ready, request_id="r1", decision_id="d1", text="serve through nginx",
                 reason="tls in one place", topic="proxy", at=2)
    assert [d for d, _ in fulltext_decisions(ready, "nginz", k=5)] == ["d1"]
```
  The existing test that query syntax in the input cannot escape stays green.
- [ ] Steps 2–4; commit `feat(graph): typo-tolerant full-text search`.

### Task 9.10: FalkorDB UDF `handoff.fileOverlap`

**Files:** Create `src/handoff/graph/udf.py` (`UDF_LIBRARY` JS source,
`load_udfs(graph) -> bool`, `file_overlap(graph, a: str, b: str) -> float | None`);
Modify `graph/schema.py` (`ensure_schema` calls `load_udfs`, ignoring failure), 
`graph/insights.py` (collision text ranks pairs by overlap when available).

- [ ] Step 1: probe the UDF syntax on a throwaway graph per docs.falkordb.com/udfs (register
  call and `GRAPH.UDF LOAD REPLACE`), record it in the ledger, delete the probe graph.
- [ ] Step 2: tests: two requests editing {a, b} and {b, c} → overlap 1/3; loading twice
  is fine; `file_overlap` returns None when UDFs are unavailable (fake failing graph).
- [ ] Steps 3–5; commit `feat(graph): add a FalkorDB UDF for file overlap`.

### Task 9.11: `handoff watch`

**Files:** Create `src/handoff/graph/feed.py` (`FeedEvent(at, role, kind, text)`,
`recent_events(graph, *, limit) -> list[FeedEvent]`), `src/handoff/cli/watch.py`
(`render_frame(sessions, events, insights, width) -> str`, `run`); tests.

- [ ] Step 1: tests: `recent_events` on a seeded graph returns asked/DECIDED/NEEDS/edited/
  MESSAGE/STANDIN_ANSWER/READ in time order (one UNION ALL, shared column names);
  `render_frame` colours each role and cuts lines to the width; the loop shows
  "database unreachable — retrying" when the graph raises a connection error and exits 0
  on KeyboardInterrupt (review focus 4).
- [ ] Steps 2–4; commit `feat(cli): add handoff watch, a live feed of the graph`.

### Task 9.12: `handoff demo` (headless proof)

**Files:** Create `src/handoff/demo/__init__.py`, `demo/script.py` (the ShopLite rounds:
`ROUNDS: tuple[dict[str, str], ...]` and the short scenario used headless),
`demo/check.py` (moved from `scripts/e2e_check.py`), `cli/demo.py`; Modify
`scripts/e2e_scenario.sh` → one line `exec handoff demo "$@"`; delete `scripts/e2e_check.py`.

- [ ] Step 1: tests: `check` passes on a seeded graph with every expected part and names
  each missing part otherwise; `demo` refuses to start without `claude` (exit 1).
- [ ] Steps 2–4; live: `handoff demo` PASS.
- [ ] Step 5: commit `feat(cli): add handoff demo, the headless proof`.

### Task 9.13: `handoff demo --live` (tmux grid)

**Files:** Create `src/handoff/demo/tmux.py` (`layout_commands(session, folder, roles) -> list[list[str]]`,
`done_line(screen: str) -> str`), `src/handoff/demo/drive.py` (sends a round, waits for each
pane's done line to change, 8-minute cap per round); Modify `cli/demo.py` (`--live`,
`--manual`).

- [ ] Step 1: tests: `layout_commands` creates a 2×2 grid with frontend, deploy, backend
  and `handoff watch`, each Claude started through `env -i` with HOME, USER, PATH, TERM,
  LANG and its HANDOFF_ROLE only; `done_line` returns the latest "for 8s · done 12:29 PM"
  line (the alternate screen keeps no scrollback, so "changed", not "count", is the
  signal); without tmux, `--live` prints the install hint and exits 1.
- [ ] Steps 2–4; live: `handoff demo --live` opens the grid; after the person accepts the
  trust prompts, the rounds run and the feed fills.
- [ ] Step 5: commit `feat(cli): add handoff demo --live, a tmux grid of real sessions`.

### Phase 9 gate

`make check`; live: `handoff init` in a fresh folder, `handoff demo` PASS,
`handoff demo --live` watched end to end, `handoff ask` answered with Cypher shown,
`handoff insights` non-empty on the demo graph; fresh opus review and fix pass; merge,
tag `phase-9`, notebook.

---

## Phase 10: Ship

Branch: `phase/10-ship`.

### Task 10.1: README and licence

- README around the one-line install; what handoff does in four sentences; a diagram of
  the graph; the CLI table; `handoff demo --live` walkthrough with a screenshot; FalkorDB
  features used and why (vector, full-text, algorithms, UDF, read-only MCP, Browser);
  ready-made Browser queries; privacy (localhost only, redaction); limits.
- `LICENSE` (MIT). `pyproject.toml` metadata (description, license, urls).
- Check: a fresh clone in a scratch folder → `uv tool install <path> && handoff init` works.

### Task 10.2: Final notebook and demo script

- Notebook: Phases 9–10 done, decisions, change log. A two-minute video script in the
  notebook (which panes to show, which Browser queries, which `handoff` commands).

### Task 10.3: Submission (you)

- Make the GitHub repository public (owner's decision; Claude does not change it).
- Record the video, write the blog post, submit on WeMakeDevs before 18 October 2026,
  11:59 PM IST.

---

## Phase 11 (stretch): The coordinator, and an ontology that grows

- An always-on agent in the spirit of OpenAI's Dots: it watches the graph and acts within
  rules the person sets (a need left open for 30 minutes, two roles changing one file, an
  end-of-day digest).
- Growing the knowledge graph's entity types from data with GraphRAG-SDK's
  `suggest_schema_extensions` (needs our items written to files first).


---

## Phase 15 (stretch): Mission control, the graph made visible

A local web page that shows the orchestration, the hand-off of context, the graph itself and
the competition tracks, live. Plain HTML, CSS and JavaScript served by a small standard-library
server; no build step, no external assets.

- `graph/overview.py`: per-role counts, who talks to whom, reads with the decisions learned.
- `graph/context_view.py`: the work graph and the concept graph as nodes and edges.
- `dashboard/state.py` + `tracks.py`: one JSON snapshot; the track mapping with live numbers.
- `dashboard/server.py`: localhost only, exact-name static files, Host check, CSP.
- `dashboard/static/`: orchestration, handoff, graph view, tracks, one script per view.
- `cli/dashboard_cmd.py` (`handoff dashboard`); `demo/mission.py` starts it with the live demo.
- Gate: `make check`; the page rendered in headless Chrome against the real demo graph.
