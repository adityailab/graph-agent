# handoff user guide

How to use handoff in a real project, from install to daily use. For a one-page overview see
the [README](../README.md).

## 1. What you are setting up

handoff connects several Claude Code sessions working in **one project folder**. Each
session has a **role** (frontend, backend, deploy, or any name you choose). While they
work, handoff records what each was asked, what it decided and why, which files it changed,
and what it needs from another role. Every session can read the others' intent, send
messages, and ask questions. You, the person, can watch and steer with the `handoff` command.

Everything lives in a FalkorDB graph that runs on your machine.

## 2. Before you start

You need:

- **Docker** (or Colima on macOS), running.
- **Claude Code**, logged in (run `claude` once).
- **uv** (https://docs.astral.sh/uv/).
- Optional: **Node 18+**, for FalkorDB's own MCP server. Without it handoff works but
  sessions cannot run their own Cypher queries.

## 3. Install and set up a project

```bash
uv tool install "handoff[knowledge] @ git+https://github.com/adityailab/graph-agent"
cd your-project
handoff init
```

`handoff init` does four things and tells you what it did:

1. Checks the prerequisites and prints how to fix anything missing.
2. Makes sure FalkorDB is running: it uses one that already answers, or starts one in Docker
   (container `handoff-falkordb`, data kept in the volume `handoff-data`, bound to this
   machine only).
3. Installs hooks and two MCP servers into the folder: `.claude/settings.local.json` and
   `.mcp.json`. Existing settings are kept, and running `init` again changes nothing.
4. Gives the project its own graph, named from the folder, for example `handoff_shop_1a2b3c`,
   so two projects never see each other's work.

`init` writes two files with paths specific to your machine: `.claude/settings.local.json`
and `.mcp.json`. Add both to the project's `.gitignore` so they are not committed.

Run `init` in the project you want sessions to share, not in handoff's own source folder.

Drop `[knowledge]` from the install line to skip the knowledge graph (it needs a large
dependency).

## 4. Start your sessions

Open one terminal per role, in the project folder:

```bash
HANDOFF_ROLE=frontend claude
HANDOFF_ROLE=backend  claude
HANDOFF_ROLE=deploy   claude
```

The first time, Claude Code asks you to approve the project's MCP servers: approve them. If
you leave `HANDOFF_ROLE` out, the role is the folder name, so give each terminal its own.
Two terminals with the same role share one identity.

Then work as usual. You type normal prompts; handoff does the rest in the background.

## 5. What happens while you work

| When | What handoff does |
|---|---|
| You send a prompt | It is recorded as a request. The session is shown any messages waiting for it and any open needs addressed to its role (each with its id). |
| A session edits a file | The edit is tied to the request that caused it. If another session changed that file recently, the editing session is told who and why. |
| A session finishes after changing files with no decision recorded | It is asked once to record the decision and its reason before it stops. |
| A session is idle and another sends it a message | It wakes and acts on the message. |

You can steer sessions in plain words, for example: *"Pick up what the frontend did and
resolve its need for avatarUrl"*, or *"Ask the backend why tokens rotate"*. The sessions
have these tools:

| Tool | Use |
|---|---|
| `handoff` | What each role was asked, decided, changed and needs. Ends with "What matters now". |
| `why` | The intent behind the edits to a file. |
| `sessions` | Which sessions are active and what each is working on. |
| `record_decision` | Record a choice with its reason (a field name, an API shape, a library, a trade-off). |
| `record_need` | Say what this work needs from another role. |
| `resolve_need` | Close a need, by its id, once it is met. |
| `send_message` | Message every session with a role. |
| `ask` | Ask a role a question; get an immediate stand-in answer from that role's history, with sources, and the real session also receives the question. |
| `search` | Find decisions by their words and by meaning, from any role. |
| `connection` | The chain of shared files, decisions and needs linking this work to another role's. |
| `ask_graph`, `concepts` | Questions answered from the knowledge graph. |
| `graph_guide` | Teaches the session the graphs so it can run its own read-only Cypher. |

## 6. The `handoff` command, in daily use

Run these from the project folder.

### See what is going on

```bash
handoff status
```

Shows the database, this project's graph, whether the knowledge worker is running, the
sessions seen in the last 24 hours with what each is working on, open needs per role, any
messages sessions sent **to you**, and the latest digest from the coordinator.

```bash
handoff log             # what every role asked, decided, changed and needs
handoff log backend     # one role
handoff log --hours 2   # only the last two hours
```

```bash
handoff watch
```

A live view, refreshed every 2 seconds: active sessions, the newest events (asked, decided
with its reason, needs, edits, messages, and READ when one session read another's work), and
"What matters now". Press Ctrl-C to stop. Keep it in its own terminal or tmux pane.

```bash
handoff dashboard            # opens http://127.0.0.1:8765/ in your browser
handoff dashboard --port 9000 --no-open
```

Mission control, the visual version of `watch`, with four views: **Orchestration** (sessions as
nodes, messages, reads and needs moving between them), **Context handoff** (what each session
learned from another's work, with the decision and its reason, and how much of each
session's memory is its own or learned), **Context graph** (the shared graph drawn live,
shaded by role; a toggle shows the concept graph) and **Tracks** (how handoff answers
each competition track, with live numbers). A live feed runs down the right side, and
**Replay last events** replays the newest ones as animation, which is handy when recording.
The server listens on `127.0.0.1` only and shows the graph of the folder you run it in.
`handoff demo` starts it for you.

### Talk to the sessions

```bash
handoff send backend "Use integer paise for prices"
```

Every session with that role receives it, and an idle one wakes. If no session has that role
yet, the message waits for the first one. Replies to you show up under "messages for you" in
`handoff status`.

### Ask questions of the graph

```bash
handoff ask "Which needs are still open, and who owes them?"
```

Claude Code is started, learns the graphs through `graph_guide`, writes read-only Cypher,
runs it through FalkorDB's server, and prints the answer followed by the Cypher it ran. It
uses your Claude plan (usually under a minute). It cannot change anything.

### What matters now

```bash
handoff insights
```

Computed with FalkorDB's graph algorithms:

| Kind | Meaning |
|---|---|
| `collision` | Two or more roles changed the same file in the last week. |
| `load_bearing` | Work that two or more other roles have read and rely on. |
| `bridge` | Work that read one role's output and was read by a third role. |
| `theme` | A cluster of related concepts in the knowledge graph (needs `handoff knowledge`). |

### The knowledge graph

```bash
handoff knowledge          # runs until Ctrl-C, ingesting new work as it arrives
handoff knowledge --once   # ingest what is pending, then exit
```

Turns requests and decisions into a graph of concepts (components, files, functions, APIs,
data fields, services, libraries, settings) and how they relate, with each concept linked
back to the request or decision it came from. Every 10 items it may learn a new entity type
from your work (for example `Pipeline`), up to 20. One worker runs per project; each
extraction uses a model call.

### The always-on coordinator

```bash
handoff coordinator                 # keep running; Ctrl-C to stop
handoff coordinator --once          # one pass
handoff coordinator --dry-run --once   # say what it would send, send nothing
```

It sends messages only, from the role `coordinator`, and calls no model:

| Rule | When |
|---|---|
| Stale need | A need has been open 30 minutes: reminds the role that owes it (again every 4 hours). |
| Collision | Two roles changed the same file within an hour: tells both. |
| Digest | Every hour, if anything happened: a summary to you, shown in `handoff status`. |

Options: `--stale-minutes`, `--repeat-minutes`, `--collision-minutes`, `--digest-minutes`
(0 turns the digest off).

### Check and repair

```bash
handoff doctor
```

Reports missing hooks, a missing handoff server in `.mcp.json`, an unreachable database, and
hook errors from the last hour, each with what to do. Prints "All good" otherwise.

### Try it without a project

```bash
handoff demo             # a tmux grid: three real sessions plus the live feed
handoff demo --headless  # the same collaboration as plain text, then a PASS/FAIL check
```

Without tmux, or when output is piped, plain `handoff demo` runs headless and says so.
Both build a small shop called ShopLite in a scratch folder and graph `handoff_demo`. They
use your Claude plan and run the sessions on Haiku. For the grid you need tmux
(`brew install tmux`): attach with `tmux attach -t handoff-demo` and accept Claude Code's
"trust this folder" prompt in each of the three Claude panes; the rounds then start by
themselves. Add `--manual` to type your own prompts instead. A pane may also ask permission
to run a shell command: answer it as you would normally.

## 7. Looking at the graph in a browser

FalkorDB Browser runs at **http://localhost:3000**. Connect to host `localhost`, port
`6379`, no password, choose your project's graph (`handoff status` prints its name), and try:

```cypher
MATCH p=()-[]->() RETURN p                                   // everything
MATCH (n:Need {status: 'open'}) RETURN n                     // open needs
MATCH (r:Request)-[:CONSULTED]->(c:Request) RETURN r, c      // who read whose work
MATCH (i:Insight)-[:CONCERNS]->(n) RETURN i, n               // insights
```

The knowledge graph is the same name with `_kg` added. Nodes are captioned with short readable
names. The Browser also has its own chat for asking questions in plain English; give it a
model in its Settings page.

## 8. Settings

Set these in the environment of the terminal that starts a session or command.

| Variable | Meaning | Default |
|---|---|---|
| `HANDOFF_ROLE` | This session's role | the folder name |
| `HANDOFF_GRAPH` | The graph to use | one named for the project (written by `init`) |
| `HANDOFF_HOME` | Where handoff keeps its logs, models and state | `~/.handoff` |
| `HANDOFF_DB_HOST`, `HANDOFF_DB_PORT` | Where FalkorDB is | `localhost`, `6379` |
| `HANDOFF_BROWSER_PORT` | Browser port when `init` starts the database | `3000` |
| `HANDOFF_MODEL` | Model backend: `claude-code`, `anthropic` or `ollama` | `claude-code` |
| `HANDOFF_MODEL_NAME` | The model for stand-in answers and the knowledge graph | Claude Code's default |
| `HANDOFF_KNOWLEDGE_MODEL` | A different model for knowledge extraction only | the same |
| `HANDOFF_ASK_MODEL` | The model for `handoff ask` | `sonnet` |
| `HANDOFF_KNOWLEDGE` | `off` stops a session from starting a knowledge worker | on |
| `HANDOFF_KNOWLEDGE_MAX_PER_HOUR` | Cap on items ingested per hour | 60 |
| `HANDOFF_WAIT_SECONDS` | How long an idle session waits for a message before the waiter ends | 3500 |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID` | For `HANDOFF_MODEL=anthropic` | none |

Pick `haiku` with `HANDOFF_MODEL_NAME=haiku` to spend the least. Do not export
`ANTHROPIC_API_KEY` in a terminal where you run interactive `claude`: Claude Code would bill
the API instead of your plan.

## 9. Troubleshooting

| Symptom | What to do |
|---|---|
| Anything seems off | `handoff doctor` |
| `handoff init` says Docker is not running | Start Docker (with Colima: `colima start`), run `init` again. |
| "Something answers but is not FalkorDB" | Another Redis uses the port. Run `HANDOFF_DB_PORT=6380 handoff init`. |
| Port 3000 is taken (a dev server) | `HANDOFF_BROWSER_PORT=3100 handoff init`. |
| Sessions do not see each other | Check they run in the same project folder and use different `HANDOFF_ROLE`s; `handoff status` lists the sessions. |
| A message did not wake an idle session | The waiter only runs after a normal finish; a session you interrupted will see the message on its next prompt. |
| Hook trouble | Hooks never block a session. Errors go to `$HANDOFF_HOME/logs/hooks.log`; events saved during a database outage are replayed later. |
| Commands from a subfolder | They find the project's graph by looking upward for the folder `init` was run in. |

## 10. Privacy and safety

- FalkorDB listens on this machine only and holds your prompts, so keep it local.
- Prompts and diffs pass through a redactor (API keys, tokens, private keys, secret
  assignments) before they are stored.
- Cypher written by a model runs only through FalkorDB's server in strict read-only mode.
- `handoff demo --workspace` only resets a folder the demo created.

## 11. Removing handoff

- From a project: delete the handoff entries from `.claude/settings.local.json` (the hooks
  and the `HANDOFF_*` environment values) and the `handoff` and `falkordb` servers from
  `.mcp.json`.
- The tool: `uv tool uninstall handoff`.
- The database: `docker rm -f handoff-falkordb` and, to delete the data too,
  `docker volume rm handoff-data`.
