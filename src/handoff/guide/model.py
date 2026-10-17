"""What each part of the graph means. Fixed text, kept as data beside the schema."""

from __future__ import annotations

WORK_MODEL: tuple[tuple[str, str], ...] = (
    (
        "(:Session {id, role, cwd, name})",
        "one Claude Code terminal; role 'person' is the human using the handoff CLI",
    ),
    (
        "(:Session)-[:RECEIVED]->(:Request {id, seq, text, at, name})",
        "what the person asked that session, numbered by seq",
    ),
    ("(:Request)-[:NEXT]->(:Request)", "the same session's next request"),
    (
        "(:Request)-[:LED_TO]->(:Decision {id, text, reason, at})",
        "a decision taken for the request, with its reason",
    ),
    ("(:Decision)-[:ABOUT]->(:Topic {name})", "what the decision is about"),
    (
        "(:Request)-[:RAISED]->(:Need {id, text, for_role, status})",
        "what the request needs from another role; status 'open' or 'resolved'",
    ),
    ("(:Need)-[:RESOLVED_BY]->(:Request)", "the request that met the need"),
    (
        "(:Request)-[:CAUSED]->(:Edit {id, tool, summary, at})-[:TOUCHED]->(:File {path})",
        "a file change made for the request (paths are relative to the project)",
    ),
    (
        "(:Session)-[:SENT]->(:Message {id, kind, text, to_role, at})",
        "kind is 'message', 'question' or 'standin_answer'",
    ),
    ("(:Message)-[:DELIVERED_TO {at}]->(:Session)", "the message reached that session"),
    ("(:Message)-[:REPLY_TO]->(:Message)", "an answer to a question"),
    (
        "(:Message)-[:CITES]->(:Request|:Decision|:Need|:Message)",
        "what a stand-in answer relied on",
    ),
    (
        "(:Request)-[:CONSULTED {at}]->(:Request)",
        "this request's session read that other session's request",
    ),
)

KNOWLEDGE_MODEL: tuple[tuple[str, str], ...] = (
    (
        "(:__Entity__ {name, description})",
        "a thing the work is about; a second label gives its type: Component, File, Function, "
        "API, DataField, Service, Library, Setting or Concept",
    ),
    (
        "(:__Entity__)-[:RELATES {rel_type, fact}]->(:__Entity__)",
        "how two things relate, named by the model (rel_type) with the sentence it came from "
        "(fact)",
    ),
    (
        "(:Document {id})-[:PART_OF]->(:Chunk)<-[:MENTIONED_IN]-(:__Entity__)",
        "where a thing was mentioned: Document.id is a Request or Decision id in the work graph",
    ),
)
