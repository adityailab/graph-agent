# Session Handoff Graph: design

- **Date:** 7 October 2026, updated 17 October 2026
- **Status:** design agreed; 17 October update adds live messages and the stand-in
- **Working name:** `handoff` (not final)
- **For:** Graph Hacks: Context for AI Agents (WeMakeDevs, sponsored by FalkorDB), 15–18 October 2026, solo entry

## 1. Problem

Several Claude Code sessions work in parallel in one workspace, for example one on
the frontend, one on the backend and one on deployment. The person running them
hands work from one session to the next: "frontend made changes, pick them up".

The receiving session can read the diff, so it knows *what* changed. It cannot see
the conversation that produced the change: what the person asked for, what the
other agent decided, and why. It guesses the intent from the code. The sessions
also have no way to talk to each other.

## 2. Goals

1. **Intent handoff.** Any session can read the requests, decisions and reasons
   behind another session's changes, with every statement traceable to the
   message it came from.
2. **Live messages.** A session can send a message to another session by role.
   The message reaches a working session on its next tool call and wakes an idle
   session immediately.
3. **Stand-in answers.** A session can ask another role a question and get an
   answer at once, written by a model from that role's recorded history and
   marked as a stand-in answer. The real session also receives the question.

Success is the scenario in section 8 running end to end.

### Not goals

- Analysing code structure: no parsing, no API contracts, no dependency graph.
- More than one machine, or agents other than Claude Code.
- A custom dashboard. The FalkorDB browser is the graph view.

## 3. Competition constraints

- Build window: 15 October 12:01 AM IST to 18 October 11:59 PM IST.
- Building starts 17 October, so the build is two days, not four.
- The submission and its main FalkorDB implementation must be new work done in
  the window. Libraries, templates and infrastructure may be reused.
- FalkorDB must be the primary graph database and central to the product.
- Submit a code repository. A live deployment is preferred; otherwise complete
  local setup instructions and a working demo video.
- AI coding assistants are allowed; the entrant must be able to explain what was
  built and why.
- Tracks: Track 02 (agent memory and coordination) is the closest fit; Track 01
  (agents that act on connected data) is a second entry.

## 4. Parts

```
 Claude session (frontend)          Claude session (backend)
   hooks ──► write, deliver          MCP tools ──► read, write, message, ask
        │                                  │
        ▼                                  ▼
      ┌──────────────── FalkorDB graph ────────────────┐
      └────────────────────────────────────────────────┘
```

Everything is Python. Coding standards are in `CLAUDE.md` at the repository root.

### 4.1 Capture and delivery hooks

One command, `handoff-hook <event>`, registered for each event in the workspace's
Claude Code settings.

| Hook event | What it does |
|---|---|
| `SessionStart` | Registers the session with its role and folder. |
| `UserPromptSubmit` | Records the prompt verbatim as a `Request`. Prints pending messages and open needs for this role as context. |
| `PostToolUse` on `Edit\|Write\|MultiEdit\|NotebookEdit` | Records an `Edit` with a short diff, linked to the session's latest `Request` and to the `File`. |
| `PostToolUse` on all tools | Delivers pending messages as `additionalContext`, so a working session sees them mid-task. |
| `Stop` | The finish check (4.3), then starts the message waiter (4.5). |

Facts verified in the Claude Code hooks reference on 17 October:

- Every hook receives `session_id`, `transcript_path`, `cwd` and
  `hook_event_name` on stdin.
- `UserPromptSubmit` receives `prompt`. Plain stdout on exit 0 becomes context
  Claude sees.
- `PostToolUse` receives `tool_name`, `tool_input` (file paths are absolute) and
  `tool_response`, and can return
  `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}`.
- `Stop` receives `stop_hook_active` and `last_assistant_message`, and blocks
  with `{"decision": "block", "reason": "..."}`.
- A hook with `asyncRewake: true` runs in the background; when it exits with
  code 2 its stderr is shown to Claude and Claude wakes immediately, even if the
  session is idle. Its `timeout` is enforced.
- Hook processes inherit the environment. Stdio MCP servers receive
  `CLAUDE_PROJECT_DIR` but no session id.
- Context text should be written as plain statements of fact, not as commands,
  to avoid tripping prompt-injection defences.

### 4.2 MCP server

Each session runs its own copy of the server over stdio. All copies connect to
the same FalkorDB.

| Tool | Kind | What it does |
|---|---|---|
| `sessions` | read | Active sessions, their roles, and the latest request each is working on. |
| `handoff` | read | For one role or all roles, since a given time: requests, decisions with reasons, files changed, open needs. |
| `why` | read | For a file path: the requests and decisions behind its changes, newest first. |
| `search` | read | Past decisions that match a query by meaning. |
| `record_decision` | write | What was chosen, why, and the subject it is about. Attached to the session's current request. |
| `record_need` | write | Something this session requires from another role. |
| `resolve_need` | write | Marks a need as handled by the current request. |
| `send_message` | message | Sends text to a role, optionally as a reply to an earlier message. |
| `ask` | message | Asks a role a question. Returns a stand-in answer (4.6) and also delivers the question to the real session. |

### 4.3 Finish check

When a session tries to end a turn, the `Stop` hook asks the graph whether the
current request has at least one edit and no decision. If so, and
`stop_hook_active` is false, it blocks once with the reason "No decision is
recorded for this request yet; record_decision records it." If the database is
unreachable, the stop is allowed.

### 4.4 Session identity

- A session's role comes from the `HANDOFF_ROLE` environment variable set when
  the session is launched, falling back to the folder name.
- Hooks receive the Claude session id and store it on the `Session` node.
- The MCP server receives the role through its configuration
  (`"env": {"HANDOFF_ROLE": "${HANDOFF_ROLE}"}`) and addresses writes to the
  active session for that role in that workspace.
- Constraint: one active session per role per workspace. MCP servers do not
  receive a session id, so this constraint stays.

### 4.5 Live messages

- `send_message(to_role, text, reply_to=None)` creates a `Message` from the
  sender's session to a role.
- **Working session:** the `PostToolUse` hook on every tool call checks for
  undelivered messages to its role, returns them as `additionalContext`, and
  marks them delivered.
- **Next prompt:** the `UserPromptSubmit` hook does the same.
- **Idle session:** the `Stop` hook starts a background waiter with
  `asyncRewake: true`. (Not `SessionStart`: a waiter there claimed messages
  before the first prompt could deliver them; found in the Phase 4 live run.) The waiter polls the graph every 2 seconds.
  When a message arrives it marks it delivered, writes it to stderr and exits
  with code 2, which wakes the session. If nothing arrives before its timeout it
  exits 0. A lock file per session keeps at most one waiter running.
- Each message is delivered to a session once. Delivery is recorded as an edge,
  so the graph shows who received what and when.

### 4.6 Stand-in answers

- `ask(role, question)` records the question as a `Message` of kind `question`
  and delivers it to the real session like any message.
- It then gathers that role's recent requests, decisions with reasons, open needs
  and messages, plus decisions that match the question by meaning, and sends them
  with the question to Claude through Claude Code itself, run headless:
  `claude -p --output-format json --model haiku --tools "" --setting-sources ""
  --strict-mcp-config --no-session-persistence`, from a temporary folder. This
  runs on whatever Claude Code login the person already has (Pro or Max plan),
  so no API key is needed. With no tools, settings or MCP servers loaded, the
  call cannot trigger this project's own hooks. Measured on 17 October: about 4
  seconds for a short answer.
- The model must answer only from that material, cite the request or decision
  ids it used, and say plainly when the history does not contain the answer.
- The answer is stored as a `Message` of kind `standin_answer` with `CITES` edges
  to the nodes it used, and returned to the asking session labelled as a
  stand-in answer.
- The real session can later send a reply that corrects it.
- If the `claude` command is missing, not logged in, or fails, `ask` still
  delivers the question and says no stand-in answer is available.

## 5. Graph

Graph name: `handoff`.

| Node | Properties | Written by |
|---|---|---|
| `Session` | `id`, `role`, `cwd`, `started_at`, `last_seen_at` | Hook |
| `Request` | `id`, `seq`, `text`, `at` | Hook |
| `Edit` | `id`, `tool`, `summary` (short diff), `at` | Hook |
| `File` | `path` (relative to the workspace root) | Hook |
| `Decision` | `id`, `text`, `reason`, `at`, `embedding` | Session's agent |
| `Need` | `id`, `text`, `for_role`, `status` (`open` or `resolved`), `at` | Session's agent |
| `Topic` | `name`, `embedding` | Session's agent |
| `Message` | `id`, `kind` (`message`, `question`, `standin_answer`), `text`, `to_role`, `at` | Session's agent or stand-in |

| Edge | Meaning |
|---|---|
| `(Session)-[:RECEIVED]->(Request)` | The person sent this message to this session. |
| `(Request)-[:NEXT]->(Request)` | Order of requests within a session. |
| `(Request)-[:CAUSED]->(Edit)` | The edit happened while working on this request. |
| `(Edit)-[:TOUCHED]->(File)` | The file the edit changed. |
| `(Request)-[:LED_TO]->(Decision)` | A choice the agent made for this request. |
| `(Decision)-[:ABOUT]->(Topic)` | The subject of the decision. |
| `(Request)-[:RAISED]->(Need)` | The request exposed something another role must do. |
| `(Need)-[:RESOLVED_BY]->(Request)` | A request in another session handled the need. |
| `(Session)-[:SENT]->(Message)` | Who sent the message. |
| `(Message)-[:DELIVERED_TO {at}]->(Session)` | Which session received it, and when. |
| `(Message)-[:REPLY_TO]->(Message)` | Thread structure; a stand-in answer replies to its question. |
| `(Message)-[:CITES]->(Request\|Decision)` | Sources a stand-in answer used. |

Two layers:

- **Recorded:** `Session → Request → Edit → File`. Deterministic, written by
  hooks, always present.
- **Agent-written:** `Decision`, `Need`, `Topic`, `Message`. If the agent records
  nothing or records badly, the recorded layer is still complete.

`RESOLVED_BY`, `DELIVERED_TO` and `CITES` are the edges that cross sessions.

### Example query: why was this file changed?

```cypher
MATCH (f:File {path: $path})<-[:TOUCHED]-(e:Edit)<-[:CAUSED]-(r:Request)<-[:RECEIVED]-(s:Session)
OPTIONAL MATCH (r)-[:LED_TO]->(d:Decision)
RETURN s.role, r.text, d.text, d.reason, e.summary
ORDER BY e.at DESC
```

### Search by meaning

- `Decision.embedding` and `Topic.embedding` carry FalkorDB vector indexes with
  cosine similarity.
- The server computes embeddings locally when a decision is written, using a
  small embedding library. No API key.
- When an agent names a topic, the server reuses an existing topic whose
  embedding is close enough, so near-duplicates such as "auth tokens" and "login
  tokens" stay one subject. The threshold is set by testing.

## 6. What `handoff` returns

```
Frontend session, last 40 min: 2 requests, 5 files changed

Request 1 (you): "Show the user's full name and avatar on the profile card"
  Decided: read `fullName` and `avatarUrl` from GET /users/:id
  Why:     you rejected joining first + last name on the client
  Changed: ProfileCard.tsx, useUser.ts
  Needs from backend: `avatarUrl` is not returned yet
```

The person's original message always appears beside the agent's summary. The
call takes a "since" time and caps its output. How it chooses what to include
when history is long is a design decision left for the build.

## 7. Failure handling

| What goes wrong | What happens |
|---|---|
| FalkorDB is down | Hooks never block a session. They append the event to a local file and exit 0. The file is replayed when the database is back. The waiter exits 0. |
| An event is written twice after a replay | Event ids are generated when the hook fires and stored in the replay file. Writes use `MERGE` on the id, so duplicates collapse. |
| The agent records no decision | The finish check blocks the stop once. |
| The agent records a misleading decision | `handoff` shows the original message beside it. |
| Two waiters for one session | A lock file per session; a second waiter exits 0 at once. |
| A message is delivered twice | Delivery is claimed in one query that creates the `DELIVERED_TO` edge only if it does not exist. |
| The stand-in invents an answer | It may answer only from the material sent; answers carry citations and the stand-in label; the real session also gets the question. |
| Headless Claude Code fails or is not logged in | `ask` delivers the question and reports that no stand-in answer is available. |
| Secrets in messages or diffs | Data stays on the local machine. Common key patterns are redacted before writing. |
| Long history | `handoff` and the stand-in context are bounded by time and size; edits store a short diff, not whole files. |

## 8. Scenario

1. **Frontend session.** The person sends a request; the hook records it. Each
   edit is recorded against that request. The agent calls `record_decision` as it
   chooses and `record_need` for the backend when it finds `avatarUrl` is
   missing. The finish check confirms something was recorded.
2. **Backend session.** The person says "frontend made changes, pick them up".
   The agent calls `handoff` for the frontend role and receives the requests,
   decisions with reasons, files changed and the open need. Unsure whether the
   avatar may be empty, it calls `ask("frontend", ...)` and gets a stand-in
   answer citing the frontend's decision. The idle frontend session wakes with
   the question. The backend handles the need and calls `resolve_need`.
3. **Live message.** The backend calls `send_message("deploy", "avatarUrl added;
   needs the CDN env var")`. The deploy session, idle, wakes with the message.
4. **Deploy session.** The agent calls `handoff` across both roles and receives
   one chain: frontend request → need → backend request → edits, with reasons and
   the messages exchanged.

## 9. Testing

- **Graph layer:** tests against a real FalkorDB in Docker, each test on its own
  graph name.
- **Hooks:** saved hook inputs are fed to `handoff-hook` and the graph contents
  checked, including the replay path with the database stopped and the waiter's
  exit codes.
- **MCP tools:** tool functions called directly against a real database.
- **Stand-in:** the model client is replaced by a recorded fake in unit tests;
  one live test runs when `HANDOFF_LIVE_TESTS=1` is set, calling headless
  Claude Code.
- **End to end:** one scripted run of section 8 with Claude in non-interactive
  mode and three roles, asserting that the deploy handoff contains the full
  chain. This is also the demo rehearsal.

## 10. Setup, demo and submission

- **Setup:** `docker compose up -d` starts FalkorDB (port 6379) with its browser
  (port 3000). `handoff install <workspace>` adds the hooks and the MCP server to
  that workspace's Claude Code configuration.
- **Demo:** three terminals beside the FalkorDB browser, with the graph growing
  as the sessions work. The backend session is shown first without the tool,
  then with it, then a live message wakes the idle deploy session.
- **Submission:** repository, one-command setup, demo video, blog post if time
  allows.

## 11. Build phases

Each phase ends at a gate: every check passes, the phase's behaviour is shown
working, the work is committed and merged, and the notebook is updated. The
next phase starts only after the gate. Details are in the implementation plan.

| Phase | Builds |
|---|---|
| 0 | Project skeleton, tooling, coding standards, FalkorDB in Docker. |
| 1 | Graph layer: schema, indexes, writes, the `why` and `handoff` queries. |
| 2 | Capture hooks, replay file, redaction. |
| 3 | MCP server: record, read and need tools. |
| 4 | Finish check and live messages, including the waiter. |
| 5 | Stand-in answers. |
| 6 | Search by meaning and topic reuse. |
| 7 | Installer, end-to-end run, README, demo video, submission. |

Phase 6 comes after the stand-in because the stand-in works without it, using
the graph and recency; it is the first phase to drop if time runs short.

## 12. To confirm

- Final project name.
- All sessions share one workspace folder (assumed throughout).
