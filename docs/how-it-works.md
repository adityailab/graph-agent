# How handoff works, with diagrams

This page answers two questions: *"I start a session in my project: what happens?"* and
*"I start a second session later: how do the two work together?"* The examples are from a
real run (three separate Claude Code sessions, captured on 17 October 2026).

## The idea in one picture

Sessions never talk to each other directly. They all read and write **one shared graph** that
lives on your machine, so they do not need to be running at the same time.

```mermaid
flowchart LR
    subgraph you[Your project folder]
        A[Claude Code<br/>role: frontend]
        B[Claude Code<br/>role: backend]
        C[Claude Code<br/>role: deploy]
    end
    A & B & C -- "hooks record every prompt and edit<br/>tools record decisions, needs, messages" --> G[(FalkorDB graph<br/>on your machine)]
    G -- "context on each prompt<br/>messages · open needs · collisions" --> A & B & C
    G --> W[handoff watch / status / insights]
    G --> BR[FalkorDB Browser<br/>localhost:3000]
    P([You]) -- "handoff send · ask · log" --> G
```

## Using it in your own project

```mermaid
flowchart TD
    I["1. Once per machine<br/><code>uv tool install handoff…</code>"] --> N["2. Once per project<br/><code>cd your-project &amp;&amp; handoff init</code>"]
    N --> T["3. Open a terminal per role, any time<br/><code>HANDOFF_ROLE=frontend claude</code>"]
    T --> W["4. Work normally: type prompts<br/>handoff records and shares in the background"]
    W --> S["5. Look in whenever you like<br/><code>handoff status · watch · log · insights</code>"]
```

`handoff init` installs hooks and two MCP servers into the project folder and starts FalkorDB
if it is not running. After that you do not run anything for handoff to work: you just start
Claude Code with a role. The first time, Claude Code asks you to approve the project's MCP
servers.

## Starting a second session later

This is the case that matters most. The first session does not have to be running when the
second one starts, because everything it did is already in the graph.

```mermaid
sequenceDiagram
    autonumber
    actor You
    participant F1 as Frontend session (first)
    participant G as Graph (FalkorDB)
    participant B as Backend session (started later)
    participant F2 as Frontend session (started again)

    You->>F1: "Create Login.tsx. Keep the token in an httpOnly cookie, not localStorage."
    F1->>G: request recorded · edit Login.tsx recorded
    F1->>G: decision + reason: "httpOnly cookie: scripts can't read it"
    F1->>G: need for backend: "POST /api/login must set that cookie"
    Note over F1: the first session ends

    Note over G: time passes: the graph keeps everything

    You->>B: starts a backend session: "see what the frontend needs"
    B->>G: handoff tool: what did the frontend do?
    G-->>B: decision, its reason, the open need, the file changed
    B->>G: creates api/login.py · records its decision
    B->>G: resolves the frontend's need
    B->>G: message for frontend: "endpoint is ready"
    Note over B: the backend session ends

    You->>F2: starts frontend again, first prompt
    G-->>F2: hook adds: "Message from the backend session: endpoint is ready"
    F2-->>You: "Yes, the backend says POST /api/login sets auth_token…"
```

What the sessions actually said in that run:

**Backend (started later), asked to look at the frontend's work:**

> **What the frontend decided:** store the auth token in an httpOnly cookie, not localStorage.
> **Why:** page scripts can't read httpOnly cookies, so an XSS bug can't steal the token.
> **What it needs from you:** `POST /api/login` must set that cookie in the `Set-Cookie` header.

The backend never saw the frontend's conversation. It got the decision, the reason and the
need from the graph, then built the endpoint to match, resolved the need and messaged back.

**Frontend (started again), first prompt, with no tools used:**

> Yes. The backend session sent a message: "Backend endpoint is ready: POST /api/login
> (api/login.py) sets the token as an httpOnly, Secure, SameSite=Lax cookie named auth_token…"

That message was added to the session's context by a hook as the prompt was submitted.

## What a session learns, and how

```mermaid
flowchart TD
    subgraph automatic["Automatic: handoff adds this to a session's context"]
        M["Messages sent to its role"]
        N["Open needs addressed to its role<br/>(with their ids)"]
        K["A warning when it edits a file<br/>another session just changed"]
    end
    subgraph onrequest["When the session asks: tools"]
        H["handoff: what each role asked, decided, changed, needs"]
        WH["why: the intent behind a file's edits"]
        S["search: decisions by words and meaning"]
        Q["ask: a stand-in answer from another role's history"]
    end
    G[(Graph)] --> automatic
    G --> onrequest
```

- **Automatic** items arrive on every prompt without anyone asking.
- **On request** items are Claude Code tools. handoff tells each session they exist, so you
  can simply say "check what the frontend did" or "ask the backend why tokens rotate".

## When both sessions run at the same time

```mermaid
sequenceDiagram
    participant F as Frontend (busy)
    participant G as Graph
    participant B as Backend
    participant D as Deploy (idle)

    B->>G: send_message to role "deploy": "JWT_SECRET must be set"
    G-->>D: waiter wakes the idle session
    D->>D: reads the message and acts on it
    B->>G: ask role "frontend": "may avatarUrl be null?"
    G-->>B: stand-in answer now, from frontend's history, with its sources
    G-->>F: the real frontend also receives the question
```

An **idle** session is woken when a message arrives (as long as it ended normally and its
waiter is still running). A **busy** session sees the message on its next tool call. Asking a
role that is not running gets an immediate **stand-in** answer written from that role's
recorded history, labelled as such, with the decisions and requests it relied on.

## What gets recorded

```mermaid
flowchart LR
    S[Session] -->|received| R[Request]
    R -->|led to| D[Decision + reason]
    R -->|caused| E[Edit] -->|touched| F[File]
    R -->|raised| N[Need] -->|resolved by| R2[Request]
    S -->|sent| M[Message] -->|delivered to| S2[Session]
    R -->|consulted| R3[Request of another session]
```

Every arrow is a relationship in FalkorDB, so questions like "which request caused this
edit?" or "who read whose work?" are graph queries. See them in the FalkorDB Browser at
http://localhost:3000, or run `handoff ask "…"`.

## Common questions

**Do I have to start the sessions in a particular order?** No. Start any role at any time.

**What if the first session is closed when I start the second?** Nothing is lost. The graph
holds its requests, decisions, needs and messages. The second session reads them with the
`handoff` tool.

**What if I start the second session before the first has done anything?** It sees an empty
graph and works on its own. As soon as the first session records something, it shows up.

**What if I restart the same role?** It is a new session with the same role. Messages sent
to that role while it was away are delivered on its first prompt.

**Two terminals, same role?** They share one identity, so give each terminal its own
`HANDOFF_ROLE`.

**Does Claude record decisions by itself?** Claude Code is told to use `record_decision` for
choices and `record_need` for what it needs from others. If a session changes files and
finishes without recording a decision, it is asked once to do so.

**Does anything leave my machine?** The graph and FalkorDB stay on your machine. Model calls
(stand-in answers, the knowledge graph) go through your Claude Code login like any other
Claude Code use.

More: [user guide](guide.md) for every command, [README](../README.md) for the overview.
