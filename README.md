# handoff

**Parallel Claude Code sessions that know what each other are doing, and why.**

Open a frontend terminal, a backend terminal and a deploy terminal. Normally they cannot
talk: the backend session sees the frontend's diff but not what the person asked, what was
decided, or why. handoff puts all of that in one [FalkorDB](https://www.falkordb.com) graph
that every session reads and writes through hooks and MCP tools.

- **Intent, not diffs.** Each request, decision (with its reason), file edit and open need
  is recorded as it happens, and linked.
- **Sessions talk.** One session messages another; an idle one is woken. A question to an
  absent session gets a stand-in answer from that role's own history, with its sources.
- **Collisions and relays are visible.** Who changed the same file, who read whose work.
- **The graph is queryable by the sessions themselves.** `graph_guide` teaches Claude the
  graph, and it writes its own read-only Cypher.
- **FalkorDB's algorithms find what matters:** collisions, load-bearing work, bridges and
  themes.

Built for [Graph Hacks](https://www.wemakedevs.org/hackathons/falkordb) (WeMakeDevs ×
FalkorDB). Python 3.12+, MIT licence.

## Install

You need Docker (or Colima), [Claude Code](https://claude.com/claude-code) logged in, and
[uv](https://docs.astral.sh/uv/). Node 18+ is optional (FalkorDB's own MCP server).

```bash
uv tool install "handoff[knowledge] @ git+https://github.com/adityailab/graph-agent"
cd your-project
handoff init
```

`handoff init` checks what is missing and says how to fix it, uses a FalkorDB that is
already running or starts one in Docker (localhost only, data in a volume), and installs the
hooks and MCP servers into the folder on a graph of its own. Then start one Claude Code per
role:

```bash
HANDOFF_ROLE=frontend claude
HANDOFF_ROLE=backend  claude
HANDOFF_ROLE=deploy   claude
```

No API key: everything runs on your Claude Code login. Drop `[knowledge]` to skip the
knowledge graph (it pulls a large dependency).

## See it work

```bash
handoff demo --live
```

opens a tmux grid of three real Claude Code sessions plus a live feed, and runs a
collaboration (a small shop, "ShopLite") round by round. Accept Claude Code's folder-trust
prompt in each pane and it starts by itself. `handoff demo` does the same headless and
checks the result (PASS or what is missing). Both use your plan.

Open **http://localhost:3000** (FalkorDB Browser), pick the demo graph and run
`MATCH p=()-[]->() RETURN p`.

## The commands

| Command | What it does |
|---|---|
| `handoff init` | Check prerequisites, make sure FalkorDB runs, install into this folder |
| `handoff status` | Database, graph, active sessions and what each is on, open needs |
| `handoff log [role]` | What each role asked, decided, changed and needs |
| `handoff send <role> "text"` | You message a role; an idle session wakes and acts |
| `handoff ask "question"` | Claude answers from the graphs, writing read-only Cypher; prints the query |
| `handoff insights` | Collisions, load-bearing work, bridges, themes |
| `handoff watch` | Live feed of the graph |
| `handoff coordinator` | Always-on agent: reminds a role about a need open 30 min, tells two roles who changed the same file, sends you an hourly digest (`--once`, `--dry-run`) |
| `handoff knowledge` | Build the knowledge graph (concepts the work is about) |
| `handoff demo [--live]` | The proof |
| `handoff doctor` | Diagnose hooks, servers, database |

Inside a session the tools are: `handoff`, `why`, `sessions`, `record_decision`,
`record_need`, `resolve_need`, `send_message`, `ask`, `search`, `connection`, `ask_graph`,
`concepts`, `graph_guide`.

## How it works

```
 frontend ─┐  hooks record each prompt and edit        ┌─> other sessions (context on each prompt,
 backend  ─┼─ + MCP tools record decisions, needs ────>│    wake-ups when a message arrives)
 deploy   ─┘  and messages                  FalkorDB   ├─> handoff watch / insights / ask
                                            graph      └─> FalkorDB Browser
```

Graph (per project): `Session -RECEIVED-> Request -LED_TO-> Decision -ABOUT-> Topic`,
`Request -CAUSED-> Edit -TOUCHED-> File`, `Request -RAISED-> Need -RESOLVED_BY-> Request`,
`Session -SENT-> Message -DELIVERED_TO-> Session`, `Message -CITES-> …`,
`Request -CONSULTED-> Request`, `Insight -CONCERNS-> …`. A second graph `<name>_kg` holds
concepts extracted from the work by GraphRAG-SDK (entity types: Component, File, Function,
API, DataField, Service, Library, Setting, Concept). The types grow from the data: every 10
ingested items GraphRAG-SDK proposes kinds the text mentions that we lack (e.g. Pipeline, Job,
DatabaseTable); sound ones are added for future extraction, up to 20, and saved per graph.

### FalkorDB features in use

| Feature | Used for |
|---|---|
| Vector index (384-d cosine) | Search decisions by meaning |
| Full-text index (fuzzy, prefix) | Typo-tolerant search of requests, decisions, needs, messages |
| Unique and range indexes | Idempotent writes on Claude Code's own ids |
| `algo.SPpaths` | The chain of work linking two roles |
| `algo.WCC`, `algo.pageRank`, `algo.labelPropagation` | Collisions, load-bearing work, themes |
| JavaScript UDF | `handoff.overlap`, file overlap between two requests, inside the database |
| `db.meta.stats`, `db.indexes` | Live schema for `graph_guide` |
| Official FalkorDB MCP server (strict read-only) | Agents' own Cypher |
| GraphRAG-SDK | Knowledge graph and provenance back to requests |
| FalkorDB Browser | Seeing it all |

## Models

By default every model job (stand-in answers, the knowledge graph, `handoff ask`) runs
Claude Code headless on your login. Set `HANDOFF_MODEL_NAME` to pick the model (`haiku`
is cheapest). Alternatives for the stand-in and knowledge jobs:

- `HANDOFF_MODEL=anthropic` with `ANTHROPIC_API_KEY` (and `ANTHROPIC_WORKSPACE_ID` if the
  key is not scoped to a workspace).
- `HANDOFF_MODEL=ollama` with a local model, e.g. `HANDOFF_MODEL_NAME=qwen2.5:7b`.
  Small local models answer from the graph but may not cite their sources.

## Privacy and safety

- FalkorDB is bound to 127.0.0.1 and holds your prompts: no password, so keep it local.
- Prompts and diffs pass through a redactor (API keys, tokens, private keys) before storage.
- Hooks fail open: if handoff breaks, your session is never blocked; events are saved and
  replayed.
- Cypher written by a model only runs through FalkorDB's server in strict read-only mode.
- `handoff demo --workspace` only resets a folder the demo made.

## Limits

- Roles are names you choose per terminal; two terminals with one role in one folder share
  an identity unless Claude Code's process id tells them apart.
- Stand-in answers, the knowledge graph and growing entity types spend model calls on your
  plan; the coordinator, insights and `watch` call no model.
- FalkorDB 4.22's `betweenness` is a sampled estimate; handoff uses an exact pattern for
  bridges. The guide teaches sessions this and other 4.22 quirks.
- The live demo reads Claude Code's screen to know when a turn ended, which may change
  between versions; the headless demo is the dependable proof.

## Development

```bash
uv sync --extra knowledge
make db-up      # FalkorDB for the tests
make check      # format, lint, mypy --strict, tests
```

Design, plan and decision log: `docs/superpowers/`.
