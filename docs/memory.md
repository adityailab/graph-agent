# Memory in handoff

An agent's memory is more than one thing. handoff keeps six kinds in one FalkorDB graph, and
`handoff memory` (or the **memory** page of mission control, key 3) shows how much of each the
graph holds and what each live session has in hand.

| Kind | What it is | Where it lives | How it gets there | How to read it |
|---|---|---|---|---|
| **Working** | What a live session holds right now: its task, what it learned from others, what was delivered to it | `Session`, its latest `Request`, `CONSULTED` and `DELIVERED_TO` edges | Hooks record the prompt; reading another role's work and delivering messages add edges | `handoff memory`, mission control |
| **Episodic** | What happened, in order, with who and when | `Request`, `Edit`, `File`, `Message` nodes with times | Hooks record every prompt, file edit and message | `handoff log`, `why`, `handoff watch` |
| **Semantic** | What things mean: decisions with their reasons, the topics they are about, and the concepts in the knowledge graph | `Decision` (with embeddings), `Topic`, the concept graph from `handoff knowledge` | `record_decision` by the agent; the knowledge worker extracts concepts | `search`, `concepts`, `handoff ask` |
| **Procedural** | How the team does things: standing rules | `Convention` nodes (a rule, its reason, who it is for) | `record_convention` by an agent, or `handoff conventions add` by a person | `conventions`, `handoff conventions` |
| **Temporal** | How decisions changed, and what replaced what | `SUPERSEDES` edges between `Decision` nodes, `superseded_at` | `record_decision` lists earlier decisions on the topic that still stand; `supersede_decision` marks a replacement | `timeline`, `handoff timeline <topic>` |
| **Social** | Who knows what from whom | `CONSULTED` (a session read another's work), `Message` between roles, shared files | The `handoff` tool records a read; `send_message` records a message | `connection`, mission control's orchestration page |

## How the kinds work together

- A session's first prompt carries the standing rules for its role (procedural), plus any
  messages waiting for it and needs addressed to it (social, working). Later prompts carry only
  what is new.
- When an agent records a decision it is told about earlier decisions on the same topic that
  still stand. If the new one replaces an older one, `supersede_decision` keeps both and marks the
  order, so a later reader sees the history and the current answer. The `handoff` view marks a
  replaced decision as "replaced later".
- Decisions are searchable by words and by meaning (vector index), so a session can find
  a relevant earlier decision it never saw.

## What is not built

- **Forgetting.** Nothing is deleted or faded; the graph only grows. A `Convention` can be
  retired, and a decision can be superseded, but nothing expires by itself.
- **Summaries of old history.** The coordinator's digest summarises recent activity for a
  person, but older episodes are not condensed into a shorter memory.

## Opening a memory

On the dashboard's memory page, click a kind to see it drawn as a graph on the graph page (a `memory · kind` button); click a node there to read its full text. Each
session's card also lists "relevant memories": decisions whose words match what that session is
working on now. They come from `/api/memory/<kind>/graph` (also `/api/memory/<kind>` as a list) and `/api/memory/relevant/<role>`.

## Asking the graph

The dashboard's **ask** tab is a chat with the graphs. It remembers the last six turns (so "and who
replaced it?" works), shows what Claude Code is doing as it happens (reading the guide, each Cypher
query, the answer being written) and keeps the Cypher it ran. Thinking text is not exposed by Claude
Code, so the page shows steps and notes, not raw reasoning.
