# handoff as a product: one-command CLI, agent-written Cypher, graph insights

Date: 17 October 2026. Status: approved in conversation (sections 0–3); this document
records it. Builds on `2026-10-07-session-handoff-graph-design.md` (phases 0–8).

## 1. Purpose

handoff lets parallel Claude Code sessions understand each other's intent and talk to each
other through a shared FalkorDB graph. Phases 0–8 built the engine: hooks, MCP tools,
messages, stand-in answers, search, the knowledge graph. This phase turns it into a
product a person installs with one command, uses from a CLI, and can *see* working, and
makes the graph intelligent: agents write their own Cypher against it, and FalkorDB's
algorithms surface what matters without anyone asking.

**What the owner asked for:** a full product, intelligent and dynamic rather than
hard-coded, using FalkorDB's features where they do real work, one-command install,
CLI-first, visually convincing ("open multiple sessions and show me").

**Success looks like:**
1. `uv tool install git+<repo> && handoff init` in a project folder gives a working setup.
2. `handoff demo --live` opens three real Claude Code sessions and a live feed in a tmux
   grid and runs a collaboration a viewer can follow; `handoff demo` does the same headless
   and checks the result.
3. A session (or `handoff ask`) answers a question no tool anticipated by writing its own
   read-only Cypher, grounded by `graph_guide`.
4. `handoff insights` and the agents' handoff context show load-bearing decisions, bridge
   work, collision clusters and themes computed by FalkorDB algorithms.

**Constraints:** no API key required (Claude Code login is the default model); LLM-written
Cypher only ever runs read-only with a time limit; the small-files and naming rules in
`CLAUDE.md`; deadline Sunday 18 October 2026, 23:59 IST.

## 2. Decisions taken while designing

- **No custom dashboard.** FalkorDB Browser 2.6.2 (in our Docker image, port 3000) already
  has graph visualisation, a Cypher editor and a built-in LLM chat (`/api/chat`, with
  Anthropic, OpenAI, Gemini, Groq and Ollama; `/api/chat/fix` repairs failing Cypher). The
  person's visual surface is the Browser plus `handoff watch`; our job is to make the graph
  itself carry the intelligence so the Browser shows it.
- **No text-to-Cypher engine of our own.** Each Claude Code session is already an LLM and
  already has FalkorDB's official MCP server (`query_graph_readonly`, `get_graph_schema`,
  strict read-only). What it lacks is knowledge of our graph; `graph_guide` supplies it.
  GraphRAG-SDK's `generate_cypher` was rejected (fixed to its own schema, regex validator,
  runs queries with write access); FalkorDB's `text-to-cypher` service was rejected (an
  extra service, needs an API-key model, write blocking undocumented).
- **Insights are deterministic algorithm queries**, not an LLM choosing algorithms: faster,
  testable, and the useful set is small and known. Agents remain free to call `algo.*`
  procedures in their own Cypher.

## 3. Section 0 — the product shape: install and CLI

**Install.** `uv tool install git+<repo>` puts a permanent `handoff` command on PATH (hooks
need a stable path, so not a throwaway `uvx` environment). The README gives the one line
`uv tool install git+<repo> && handoff init`.

**`handoff init [folder]`** (default: current folder), safe to run twice:
1. Checks prerequisites and prints a fix for each one missing: Docker reachable, `claude`
   on PATH, `npx` (Node 18+) for FalkorDB's MCP server (optional: without it, init installs
   with `--no-falkordb-mcp` and says what is lost).
2. Ensures FalkorDB: if `HANDOFF_DB_HOST:PORT` answers, use it. Otherwise start
   `falkordb/falkordb:v4.22.1` as container `handoff-falkordb`, ports bound to 127.0.0.1
   (6379, 3000), named volume `handoff-data`, and wait until it answers (30 s cap).
3. Installs hooks and both MCP servers into the folder on its own graph (today's
   `install()`).
4. Prints the three-terminal start lines, the graph name and the Browser link.

**Commands.** `main.py` becomes a thin dispatcher; each command is a module in
`handoff/cli/` that parses nothing itself beyond its own arguments and calls the existing
packages.

| Command | Module | Does |
|---|---|---|
| `init [folder]` | `cli/init_cmd.py`, `prereqs.py`, `database.py` | Steps above |
| `install <folder>` | (existing) | Kept for scripting |
| `status` | `cli/status.py` | DB health, graph, active sessions and their current request, open needs, knowledge worker lead |
| `log [role]` | `cli/log.py` | The handoff view (`render_handoff`) for a person |
| `send <role> "text"` | `cli/send.py` | Message from the person to a role; an idle session wakes |
| `ask "question"` | `cli/ask.py` | Headless Claude Code with `graph_guide` + FalkorDB read-only server; prints the answer and the Cypher it ran |
| `insights` | `cli/insights_cmd.py` | Recompute and print insights |
| `watch` | `cli/watch.py` | Live terminal feed |
| `knowledge [--once]` | (existing `knowledge/cli.py`) | Knowledge worker |
| `demo [--live]` | `cli/demo.py`, `cli/demo_live.py` | Headless scenario with checks, or the tmux grid |
| `doctor` | `cli/doctor.py` | Hooks installed, servers reachable, recent hook errors |

The workspace graph name comes from the folder's `.claude/settings.local.json`
(`env.HANDOFF_GRAPH`, written by install) when run inside an installed folder, else
`HANDOFF_GRAPH`, else the folder's default name; one helper (`workspace_graph(folder)`)
decides. `handoff-hook`, `handoff-mcp` and `handoff-knowledge` stay as entry points.

**`send`'s sender.** A person is not a Claude session; `send` registers a Session with role
`person` for the folder (id stable per folder and machine) so messages keep a sender and
the graph shows the person as a participant.

## 4. Section 1 — agents write their own Cypher: `graph_guide`

A new MCP tool `graph_guide` (no arguments) returns a guide built live on each call:
1. **Which graphs:** this workspace's graph and its `_kg`, by name (FalkorDB's server sees
   every graph).
2. **The model with meanings:** each label and relationship pattern with one line of
   meaning (fixed text kept as data in `guide/model.py`), and live counts from
   `db.meta.stats()`.
3. **Indexes** from `db.indexes()`: which properties are full-text, vector or range indexed.
4. **FalkorDB 4.22 rules:** no `EXISTS {}`/`COUNT {}` (use pattern predicates or
   `size([...])`), `shortestPath` directed only and only in WITH/RETURN, `string.matchRegEx`
   not `=~`, no `datetime()`, times are integer ms, always `LIMIT`, the 1 s default timeout.
5. **Recipes** (Cypher templates): full-text with fuzzy/prefix, vector search over
   decisions, PageRank / betweenness / WCC on our graph, who consulted whose work, tracing a
   knowledge-graph entity back to requests.

The server instructions gain one line pointing at `graph_guide` for questions the other
tools don't answer. If FalkorDB's server is not installed the guide says so.

**Safety:** queries run through FalkorDB's server in strict read-only mode under the
server's 1 s default timeout. `handoff ask` adds `--allowedTools` limited to
`graph_guide`, `query_graph_readonly`, `get_graph_schema` and our read tools.

**Tests:** the guide names the right graphs and lists live labels and counts from a test
graph; every recipe runs read-only against a seeded test graph (so recipes cannot rot).

## 5. Section 2 — insight engine

`graph/insights.py` holds four algorithm queries (all verified on 4.22.1) and the writes:

| Kind | Query basis | Text |
|---|---|---|
| `load_bearing` | `algo.pageRank(null, ...)` over Decision/Topic/CITES/CONSULTED, top decisions | "<decision> is relied on by N sessions" |
| `bridge` | `algo.betweenness` over Request/Edit/File | "<file or request> links <role> and <role>" |
| `collision` | `algo.WCC` over Edit/File, components with edits from 2+ roles | "<roles> both changed <files>" |
| `theme` | `algo.labelPropagation` over Decision/Topic | "theme: <topics>" |

Results replace the previous set: `(:Insight {kind, score, text, at, name})-[:ABOUT]->(n)`.
Recomputed after each knowledge-worker pass, by `handoff insights`, and lazily by the
`handoff` tool when older than 5 minutes. The handoff text gains a short "What matters
now" section (top 3). Thresholds: an insight needs 2+ roles involved (bridge, collision)
or a PageRank score above the median (load-bearing); fewer than 3 decisions gives no
load-bearing insight. Text is templated, not model-written.

**Also in this slice:** full-text search gains fuzzy and prefix terms
(`%word%`, `word*`) for words of 5+ letters, and a FalkorDB JavaScript UDF library
`handoff` with `fileOverlap(a, b)` (Jaccard over files touched by two requests) used to
rank collision insights; loaded idempotently by `ensure_schema` (`GRAPH.UDF LOAD
REPLACE`), and the insight falls back to plain counts if UDFs are unavailable.

**Tests:** seeded graphs with a known answer per kind; insight replacement leaves one set;
fuzzy search finds a misspelling; the UDF returns the expected Jaccard.

## 6. Section 3 — making it visible

- **`handoff watch`:** a live terminal feed refreshed every 2 s: sessions with last-seen
  times, an event stream (asked, decided, needs, edited, messages, stand-in answers, READ
  for CONSULTED), open needs, and current insights; colour per role; no new dependency
  (ANSI codes). The event query lives in `graph/feed.py` (one UNION ALL with shared column
  names).
- **`handoff demo --live`:** builds a scratch project with its own graph, pre-approves
  `mcp__handoff` in that folder's settings, opens tmux session `handoff-demo` in a 2×2 grid
  (frontend, deploy, backend, watch) with each Claude session started in a clean
  environment, and runs the ShopLite collaboration in rounds (parallel within a round,
  waiting on each pane's "done" line). It asks the person to accept Claude Code's folder
  trust prompt in each pane and does not press it for them. `--manual` skips the script.
  Without tmux it says how to install it and offers the headless demo.
- **`handoff demo`:** today's `scripts/e2e_scenario.sh` as a Python module with the same
  checks; the shell script becomes a one-line wrapper or is removed.
- **FalkorDB Browser** for the picture; the README lists ready-made queries.

## 7. Error handling

- CLI commands exit non-zero with one plain sentence and a fix when a prerequisite is
  missing (Docker, database, `claude`, tmux for `--live`). No tracebacks for expected
  failures; unexpected ones propagate.
- `init` never deletes data: if a container named `handoff-falkordb` exists but is
  stopped, it starts it; if the port is taken by another FalkorDB, it uses that.
- Insights and the guide read only; insight writes replace only `:Insight` nodes.
- `ask` and `demo` spend model usage on the person's plan; each says so before starting.

## 8. Testing

Unit tests per module as above, against the real FalkorDB (`graph` fixture), no database
mocks. The CLI dispatch is tested by calling `main(argv)`. Docker and tmux calls go
through a small runner function that tests replace with a fake (the one place, besides
models, where a fake stands in). The live checks per slice are listed in the plan.

## 9. Phases

- **Phase 8 (close):** review fixes and e2e as built (graph per workspace, captions,
  CONSULTED, knowledge quality, citations). Gate, merge, tag.
- **Phase 9 — product:** 9A CLI skeleton + `init`/`doctor`/`status`/`log`/`send`;
  9B `graph_guide` + `ask`; 9C insights + fuzzy search + UDF; 9D `watch` + `demo`/`--live`.
  Each slice is mergeable on its own.
- **Phase 10 — ship:** README around `handoff init`, licence, demo recording; the owner
  records the video and submits.
- **Stretch:** growing the knowledge graph's entity types from data
  (`suggest_schema_extensions`), the always-on coordinator agent.

## 10. Risks

- FalkorDB Browser's chat is unverified with the owner's key; Ollama is the fallback.
- `uv tool install git+...` needs the repository to be public, or the person to have access.
- Live demos spend plan usage; the headless demo uses Haiku.
- tmux pane "done" detection reads Claude Code's screen text, which can change between
  Claude Code versions; the headless demo is the dependable proof.
