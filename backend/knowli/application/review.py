"""The pipeline, as a LangGraph state machine.

    extract ──► confirm ──┬─► detect ──► resolve ──► commit ──► END
       ▲                  │      (human)      (human)
       └──── clarify ─────┘

`confirm` and `resolve` call `interrupt()`. That does three things at once:
LangGraph writes the state to its Postgres checkpointer, stops the run, and
returns the payload to the caller. Nothing is running while a human thinks —
the "session" is a row in a table, so a review can be resumed hours later, from
another device, or by a different person. Resuming is `Command(resume=value)`
against the same `thread_id`.

This is why the workflow is a graph and not a chain: a chain has nowhere to
stop. Human-in-the-loop is the product here, not a feature bolted onto it.

The second half of the file is the session API the surfaces talk to: start a
review, answer a gate, read where it is, go back a step. It returns plain
dictionaries rather than response models, so the HTTP layer owns its own DTOs
and the A2A and MCP servers are not dragged through FastAPI to call this.
"""

import uuid
from collections.abc import Iterator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .. import config
from ..domain.policy import RESOLUTION_POLICY, plan
from ..wiring import catalog, checkpointer, embedder, extractor, repository
from . import knowledge_bases


class State(TypedDict, total=False):
    raw_text: str
    author: str | None
    source: str | None
    # The slug, not the KnowledgeBase. This state is serialised into a
    # checkpoint that outlives the process, and a slug is the one part of a
    # knowledge base that is stable enough to still mean something a week later
    # — a cached name or claim count would be a stale copy of a row that moved.
    knowledge_base: str
    clarifications: Annotated[list[str], lambda a, b: (a or []) + (b or [])]
    summary: str
    open_questions: list[str]
    claims: list[dict]
    conflicts: list[dict]
    resolutions: dict[str, Any]
    committed: list[dict]


# --- nodes --------------------------------------------------------------


def extract(state: State) -> dict:
    text = state["raw_text"]
    for clarification in state.get("clarifications") or []:
        text += f"\n\nClarification from the person: {clarification}"

    result = extractor.extract(text)
    claims = [
        {"id": f"c{i}", "title": c.title or c.statement[:60], "statement": c.statement,
         "topic": (c.topic or "").strip(),
         "tags": [t.strip().lower() for t in c.tags if t.strip()]}
        for i, c in enumerate(result.claims)
        if c.statement.strip()
    ]
    return {
        "claims": claims,
        "summary": result.summary,
        "open_questions": result.open_questions,
    }


def confirm(state: State) -> Command:
    """Human gate 1: did the model understand correctly?"""
    reply = interrupt(
        {
            "stage": "confirm",
            "summary": state.get("summary", ""),
            "open_questions": state.get("open_questions", []),
            "claims": state.get("claims", []),
        }
    )
    # The person can answer the open questions instead of accepting; that loops
    # back through extraction with the extra context rather than moving forward.
    if reply.get("clarification"):
        return Command(goto="extract", update={"clarifications": [reply["clarification"]]})
    return Command(goto="detect", update={"claims": reply["claims"]})


def detect(state: State) -> dict:
    """Retrieve neighbours per claim and ask the model how they relate.

    Neighbours come from this session's knowledge base and nowhere else. That
    single argument is the whole point of the container: a claim about kitchen
    returns and one about sofa deliveries can sit at a perfectly conflict-shaped
    cosine distance from each other, and the comparison prompt has no way to
    know they are about different departments. Scoping the retrieval is what
    stops that; asking the model to be careful would not.
    """
    claims = state["claims"]
    if not claims:
        return {"conflicts": []}

    kb = knowledge_bases.resolve(state["knowledge_base"])
    conflicts = []
    vectors = embedder.embed([c["statement"] for c in claims])
    for claim, vector in zip(claims, vectors):
        candidates = repository.neighbours(
            kb, vector, config.CONFLICT_TOP_K, config.CONFLICT_MAX_DISTANCE
        )
        if not candidates:
            continue
        verdicts = {c.existing_id: c for c in extractor.compare(claim, candidates)}
        for candidate in candidates:
            comparison = verdicts.get(candidate.id)
            if comparison and comparison.verdict != "unrelated":
                policy = RESOLUTION_POLICY[comparison.verdict]
                conflicts.append(
                    {
                        "key": f"{claim['id']}::{candidate.id}",
                        "draft_id": claim["id"],
                        "stored": candidate.model_dump(),
                        "verdict": comparison.verdict,
                        "reason": comparison.reason,
                        "allowed": policy["allowed"],
                        "recommended": policy["default"],
                    }
                )
    return {"conflicts": conflicts}


def resolve_node(state: State) -> dict:
    """Human gate 2: which claim wins? Skipped entirely when nothing collides."""
    conflicts = state.get("conflicts") or []
    if not conflicts:
        return {"resolutions": {}}
    reply = interrupt({"stage": "resolve", "conflicts": conflicts})
    return {"resolutions": reply["resolutions"]}


def commit(state: State) -> dict:
    actions = plan(state["claims"], state.get("conflicts") or [], state.get("resolutions") or {})
    writes = [a for a in actions if "statement" in a]
    vectors = embedder.embed([a["statement"] for a in writes])

    kb = knowledge_bases.resolve(state["knowledge_base"])
    committed = []
    for action, vector in zip(writes, vectors):
        claim = action["claim"]
        new_id = repository.insert(
            kb, claim["title"], action["statement"], claim.get("tags"), vector,
            state.get("author"), state.get("source"),
        )
        for old_id in action["supersedes"]:
            repository.supersede(old_id, new_id)
        committed.append(
            {
                "id": new_id,
                "title": claim["title"],
                "statement": action["statement"],
                "superseded": action["supersedes"],
            }
        )
    return {"committed": committed}


# --- assembly -----------------------------------------------------------

_graph = None


def graph():
    global _graph
    if _graph is None:
        builder = StateGraph(State)
        builder.add_node("extract", extract)
        builder.add_node("confirm", confirm)
        builder.add_node("detect", detect)
        builder.add_node("resolve", resolve_node)
        builder.add_node("commit", commit)
        builder.add_edge(START, "extract")
        builder.add_edge("extract", "confirm")
        # confirm returns a Command, so it routes itself to extract or detect.
        builder.add_edge("detect", "resolve")
        builder.add_edge("resolve", "commit")
        builder.add_edge("commit", END)
        _graph = builder.compile(checkpointer=checkpointer())
    return _graph


# --- the session API ----------------------------------------------------
#
# Failures are exceptions rather than HTTP status codes: the HTTP layer turns
# them back into 404/409, and the A2A and MCP surfaces get to fail their own way.


class SessionNotFound(LookupError):
    pass


class SessionNotWaiting(RuntimeError):
    pass


class SessionFinished(RuntimeError):
    pass


Stage = Literal["extracting", "confirm", "detecting", "resolve", "done"]


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _pending(session_id: str):
    """The interrupt this session is currently parked on, if any."""
    snapshot = graph().get_state(_config(session_id))
    if not snapshot.created_at:
        raise SessionNotFound("no such session")
    interrupt_ = next((i for task in snapshot.tasks for i in task.interrupts), None)
    return snapshot, interrupt_


def _stage(values: dict, interrupt_) -> Stage:
    if interrupt_:
        return interrupt_.value.get("stage")
    return "done" if values.get("committed") is not None else "extracting"


def drain(runner: Iterator[dict]) -> None:
    """Run a stream to its next stop. Same effect as `invoke`, one code path."""
    for _ in runner:
        pass


def start(
    session_id: str,
    text: str,
    author: str | None,
    source: str | None,
    knowledge_base: str | None = None,
) -> Iterator[dict]:
    """Begin a review. Returns LangGraph's node updates; drain it, or forward
    them as progress events — extraction is slow enough that a caller may want
    to watch it happen."""
    # Resolved here, eagerly, even though the stream below is lazy: a bad slug
    # should fail before the first token is generated, not four seconds into an
    # extraction the caller is already watching.
    kb = knowledge_bases.resolve(knowledge_base)
    return graph().stream(
        {
            "raw_text": text,
            "author": author,
            "source": source,
            "knowledge_base": kb.slug,
        },
        _config(session_id),
        stream_mode="updates",
    )


def answer_gate(session_id: str, value: dict) -> Iterator[dict]:
    """Resume the paused node.

    The resume value is keyed by interrupt id on purpose. With a bare
    `Command(resume=value)` LangGraph hands the same value to *every* interrupt
    reached in that run — so the resolve gate would swallow the confirm gate's
    payload instead of pausing. Keying by id resumes exactly one interrupt and
    lets the next one stop the run properly.
    """
    _, interrupt_ = _pending(session_id)
    if interrupt_ is None:
        raise SessionNotWaiting("session is not waiting for input")
    return graph().stream(
        Command(resume={interrupt_.id: value}), _config(session_id), stream_mode="updates"
    )


def confirm_claims(
    session_id: str, claims: list[dict], clarification: str | None = None
) -> Iterator[dict]:
    """Step 2 -> 3. Accept the claims, or send a clarification to re-extract."""
    value = {"clarification": clarification} if clarification else {"claims": claims}
    return answer_gate(session_id, value)


def resolve(session_id: str, resolutions: dict[str, dict]) -> None:
    """Step 3 -> 4. Apply the conflict decisions and index the result."""
    stage = state(session_id)["stage"]
    if stage != "resolve":
        raise SessionNotWaiting(f"session is at stage '{stage}', not 'resolve'")
    drain(answer_gate(session_id, {"resolutions": resolutions}))


def _record(session_id: str, values: dict, stage: Stage) -> None:
    """Keep the session list in step with the checkpointer.

    `review_session` is an index over the checkpointer, not a second source of
    truth — the claims, the conflicts and the gate all still live in LangGraph's
    tables, and are still read from them. So the row is written from the same
    read that computes the stage, rather than maintained alongside it at each
    transition: every surface calls `state()` after every step it takes, and an
    index refreshed by the thing it indexes has nowhere to drift to. Maintaining
    it by hand would mean remembering to, in five places, forever.

    Cheap because it usually writes nothing: see `record_session`, which only
    touches the row when the stage or the summary actually moved. A UI polling
    for progress therefore does not keep reordering its own list.
    """
    slug = values.get("knowledge_base")
    if not slug:
        return  # a thread that never got as far as its first checkpoint
    catalog.record_session(
        session_id,
        knowledge_bases.resolve(slug),
        values.get("author"),
        stage,
        values.get("summary", ""),
    )


def state(session_id: str) -> dict:
    """Read the current state of a review straight out of the checkpointer."""
    snapshot, interrupt_ = _pending(session_id)
    values = snapshot.values
    stage = _stage(values, interrupt_)
    _record(session_id, values, stage)
    return {
        "session_id": session_id,
        "stage": stage,
        "knowledge_base": values.get("knowledge_base") or config.DEFAULT_KNOWLEDGE_BASE,
        # The text the person originally dictated or typed. Sent back so a UI
        # that steps out of the review can put it back in the composer instead
        # of making them say it again.
        "raw_text": values.get("raw_text", ""),
        "summary": values.get("summary", ""),
        "open_questions": values.get("open_questions", []),
        "claims": values.get("claims", []),
        "conflicts": values.get("conflicts", []),
        "committed": values.get("committed", []),
    }


def capture(
    text: str,
    author: str | None = None,
    source: str | None = None,
    knowledge_base: str | None = None,
) -> dict:
    """Run a capture to its first human gate and return the session state.
    What a caller that has no interest in progress events wants."""
    session_id = str(uuid.uuid4())
    drain(start(session_id, text, author, source, knowledge_base))
    return state(session_id)


def live_claim_count(knowledge_base: str | None = None) -> int:
    """How many stored claims a capture is being compared against — in its own
    knowledge base, which is the only number that means anything now: a capture
    into an empty new knowledge base is compared against nothing, however full
    the database is."""
    return repository.count(knowledge_bases.resolve(knowledge_base))


# --- going back a step --------------------------------------------------


def rewind_action(stage: Stage) -> Literal["rewind", "stay", "refuse"]:
    """What "back" means from each stage. Pure, so the decision is testable
    without a graph, a database or a model behind it."""
    if stage == "done":
        return "refuse"
    if stage == "resolve":
        return "rewind"
    return "stay"


def back(session_id: str) -> dict:
    """Move the review one gate backwards, and return where it ended up.

    A review is a conversation, and people change their minds mid-sentence.
    Until now the only way out of the conflict gate was to abandon the session
    and dictate everything again, which is a punishing price for "wait, that
    third claim is wrong".

    Going back is not an undo stack we maintain: the checkpointer already has
    every state this thread has been in. `get_state_history` walks them newest
    first; the one whose `.next` is `("confirm",)` is the checkpoint taken just
    before the confirm node last ran. Invoking from *that* checkpoint's config
    forks the thread there and replays confirm, which hits its `interrupt()`
    again and parks the session on the confirm gate. Nothing is rewritten, and
    the abandoned branch stays in the history — going back is itself auditable.

    That old checkpoint holds the claims as the *model* first proposed them,
    though, because the person's edits arrived later, as the value that resumed
    the gate. Replaying it bare would quietly undo their editing along with
    their navigating, so the current claims are written onto the fork first.
    Going back a step should cost you the step, not your typing.

    Two stages have no rewind. From the confirm gate there is nothing further
    back *inside* the graph: the step before it is the raw text, which is not a
    graph state but a text box — so this returns the state untouched and the
    caller repopulates its composer from `raw_text`. And a committed review is
    not rewindable at all: the claims are in the store, superseding real rows,
    and other people may already have read them. Undoing that is what
    superseding is for, not what a back button is for.
    """
    snapshot, interrupt_ = _pending(session_id)
    stage = _stage(snapshot.values, interrupt_)
    action = rewind_action(stage)

    if action == "refuse":
        raise SessionFinished("session is committed; go back is not possible")
    if action == "stay":
        return state(session_id)

    target = next(
        (s for s in graph().get_state_history(_config(session_id)) if s.next == ("confirm",)),
        None,
    )
    if target is not None:
        forked = graph().update_state(target.config, {"claims": snapshot.values["claims"]})
        graph().invoke(None, forked)
    return state(session_id)
