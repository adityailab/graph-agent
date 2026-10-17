# handoff: letting parallel Claude Code sessions know why each other changed things

*Built solo for Graph Hacks (WeMakeDevs × FalkorDB). Code: https://github.com/adityailab/graph-agent*

## The problem

I run Claude Code in several terminals at once: a frontend session, a backend session, a
deploy session. They are good at their own work and blind to each other. The backend
session can read the frontend's diff, but a diff says *what* changed, never *why*: what
the person asked, what was decided, what the frontend still needs from the backend.

So I ended up as the messenger, copying context between terminals.

## The idea

Put the intent in a graph that every session reads and writes. Not the code, the *why*:

- every request a person sends a session,
- every decision with its reason,
- every file edit, tied to the request that caused it,
- every need one role has of another, open until someone resolves it,
- every message between sessions.

I chose FalkorDB because the questions are about relationships: which request caused this
edit, who read whose work, what links the backend's change to the frontend's decision.

## How it works

Claude Code hooks record each prompt and edit as it happens. A small MCP server gives each
session tools to record decisions and needs, send messages, and ask questions. When a
session submits a prompt it gets, as plain context, what others did and what is waiting
for it. An idle session is woken by a message through an `asyncRewake` hook. Ask a role
that has no live session and a stand-in answers from that role's recorded history, citing
its sources. All of it runs on your Claude Code login: no API key.

On top of the graph:

- **Search by meaning** (a 384-dimension vector index) and typo-tolerant full-text.
- **Insights from FalkorDB's own algorithms**: `algo.WCC` finds files two roles both
  changed, PageRank finds work other roles lean on, label propagation finds themes in
  the knowledge graph.
- **A knowledge graph** built by GraphRAG-SDK from the same work, with entity types that
  grow from the data (it learned `Pipeline`, `Job` and `DatabaseTable` on its own).
- **Sessions that write their own Cypher.** A `graph_guide` tool teaches Claude the graph
  and FalkorDB 4.22's quirks, and the sessions query it through FalkorDB's read-only MCP
  server. `handoff ask "which needs are still open?"` prints the Cypher it wrote.
- **A coordinator**: an always-on agent, deterministic and model-free, that reminds a role
  about a need left open, tells two roles they edited the same file, and sends a digest.

## What it looks like

`handoff demo` opens a tmux grid with three real Claude Code sessions and a live
feed. In one rehearsal, building a small shop called ShopLite, the three sessions made
31 edits across 19 files, recorded 15 decisions with reasons, resolved 3 of 4 needs
between roles, and read each other's work 17 times. The deploy session summarised what
the others had changed and why without being shown a single diff. The coordinator found a
need that had sat open for 95 minutes and reminded the backend, which then offered to
write the missing tests.

## What I learned the hard way

- **FalkorDB 4.22 has sharp edges, and the graph told me.** `EXISTS {}` is unsupported;
  `shortestPath` is directed only; `algo.betweenness` is a *sampled estimate* that scored
  a three-node chain correctly 0 times in 20; a second pattern comprehension that reuses a
  variable name silently returns `[]`. I wrote them down and put them in `graph_guide`,
  so sessions stop tripping on them.
- **A review by a fresh agent at the end of every phase paid for itself.** One found that
  `handoff demo --workspace .` would have deleted a whole project. Another found that
  two projects on one machine shared a graph and could read each other's prompts.
- **Test the real thing.** Mocks passed while live runs found a stand-in that cited
  nothing, a knowledge extractor whose instructions never reached the model, and a
  Docker volume mounted at the wrong path that would have lost every graph.

## Try it

```bash
uv tool install "handoff[knowledge] @ git+https://github.com/adityailab/graph-agent"
cd your-project && handoff init
handoff demo
```

Needs Docker, Claude Code and uv. FalkorDB runs in a container bound to localhost, and
prompts pass through a redactor before they are stored. There are 472 tests, and the whole
design, plan and decision log are in the repo.
