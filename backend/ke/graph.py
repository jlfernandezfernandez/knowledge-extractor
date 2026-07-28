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
"""

import json
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from . import config, embed, store
from .llm import structured
from .schemas import RESOLUTION_POLICY, Comparisons, Extraction

EXTRACT_SYSTEM = """You turn what a person said into separate, self-contained claims \
for a shared knowledge base.

Rules:
- One claim per fact. Split compound statements; do not split a single fact \
into fragments. Prefer three good claims over six thin ones.
- Each claim stands alone. No "it", "that", "the above". Someone reading only \
this claim, a year from now, with no other context, must understand it.
- Use the person's own language and their words. Do not translate, do not \
upgrade the register, do not add words like "proceso", "política" or \
"operaciones" if they did not say them.
- Never add a fact, a number, a caveat or a reason they did not give. If they \
said Friday morning, do not write "the weekend".
- Drop greetings, thinking aloud, and anything that is not a fact worth storing.
- `title` is a label for this one claim, two to five words. It must not be the \
same as `topic`: the topic groups several claims, the title tells them apart.
- `topic` groups claims: one or two words, and reuse the exact same wording for \
every claim about the same subject.
- `summary`: one or two sentences, in their language, saying what you took from \
this. Start with the fact, not with "The user says" or "It has been identified".
- `open_questions`: only genuine ambiguity. Usually empty."""

COMPARE_SYSTEM = """You compare a NEW knowledge claim against EXISTING claims already \
stored in a knowledge base, and decide how each pair relates.

Verdicts:
- "conflict"   they cannot both be true, or the new one updates/contradicts the old
- "duplicate"  the same fact, no new information
- "refines"    the new claim adds detail to the old one; both can stand
- "unrelated"  they only look similar; they are about different things

Be strict about "conflict": it means the two cannot both be true about the same \
subject, not merely that they are related.

Write `reason` as one short sentence in the same language as the claims."""

ANSWER_SYSTEM = """Answer the question using only the knowledge claims provided. \
Cite the ids of the claims you actually used. If the claims do not answer the \
question, say so plainly instead of guessing. Answer in the question's language."""


class State(TypedDict, total=False):
    raw_text: str
    author: str | None
    source: str | None
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

    result: Extraction = structured(Extraction).invoke(
        [("system", EXTRACT_SYSTEM), ("human", text)]
    )
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
    """Retrieve neighbours per claim and ask the model how they relate."""
    claims = state["claims"]
    if not claims:
        return {"conflicts": []}

    conflicts = []
    vectors = embed.embed([c["statement"] for c in claims])
    for claim, vector in zip(claims, vectors):
        candidates = store.neighbours(
            vector, config.CONFLICT_TOP_K, config.CONFLICT_MAX_DISTANCE
        )
        if not candidates:
            continue
        payload = {
            "new": {"title": claim["title"], "statement": claim["statement"]},
            "existing": [
                {"id": c.id, "title": c.title, "statement": c.statement}
                for c in candidates
            ],
        }
        result: Comparisons = structured(Comparisons).invoke(
            [("system", COMPARE_SYSTEM), ("human", json.dumps(payload, ensure_ascii=False))]
        )
        verdicts = {c.existing_id: c for c in result.comparisons}
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


def resolve(state: State) -> dict:
    """Human gate 2: which claim wins? Skipped entirely when nothing collides."""
    conflicts = state.get("conflicts") or []
    if not conflicts:
        return {"resolutions": {}}
    reply = interrupt({"stage": "resolve", "conflicts": conflicts})
    return {"resolutions": reply["resolutions"]}


def commit(state: State) -> dict:
    actions = plan(state["claims"], state.get("conflicts") or [], state.get("resolutions") or {})
    writes = [a for a in actions if "statement" in a]
    vectors = embed.embed([a["statement"] for a in writes])

    committed = []
    for action, vector in zip(writes, vectors):
        claim = action["claim"]
        new_id = store.insert(
            claim["title"], action["statement"], claim.get("tags"), vector,
            state.get("author"), state.get("source"),
        )
        for old_id in action["supersedes"]:
            store.supersede(old_id, new_id)
        committed.append(
            {
                "id": new_id,
                "title": claim["title"],
                "statement": action["statement"],
                "superseded": action["supersedes"],
            }
        )
    return {"committed": committed}


# --- the pure bit, unit-tested without a database or a model ------------


def plan(claims: list[dict], conflicts: list[dict], resolutions: dict[str, Any]) -> list[dict]:
    """Turn the human's decisions into writes.

    Returns one action per claim: `{"claim", "statement", "supersedes": [ids]}`
    for claims to insert, or `{"claim", "skipped": reason}` for claims to drop.
    """
    by_claim: dict[str, list[dict]] = {}
    for conflict in conflicts:
        by_claim.setdefault(conflict["draft_id"], []).append(conflict)

    actions = []
    for claim in claims:
        pairs = by_claim.get(claim["id"], [])
        if not pairs:
            actions.append({"claim": claim, "statement": claim["statement"], "supersedes": []})
            continue

        decided = []
        for pair in pairs:
            policy = RESOLUTION_POLICY[pair["verdict"]]
            resolution = resolutions.get(pair["key"]) or {}
            action = resolution.get("action") if isinstance(resolution, dict) else None
            if action is None:
                # No decision sent: fall back to the verdict's recommendation
                # rather than erroring. The UI pre-selects it, so this path is
                # for callers that only want to override the interesting ones.
                resolution = {"action": policy["default"]}
            elif action not in policy["allowed"]:
                raise ValueError(
                    f"{action!r} is not a valid resolution for a "
                    f"{pair['verdict']!r} pair ({pair['key']})"
                )
            decided.append((pair, resolution))

        if all(r["action"] == "keep_old" for _, r in decided):
            actions.append({"claim": claim, "skipped": "keep_old"})
            continue

        statement = next(
            (
                r["statement"].strip()
                for _, r in decided
                if r["action"] == "merge" and (r.get("statement") or "").strip()
            ),
            claim["statement"],
        )
        supersedes = [
            pair["stored"]["id"]
            for pair, resolution in decided
            if resolution["action"] in ("keep_new", "merge")
        ]
        actions.append({"claim": claim, "statement": statement, "supersedes": supersedes})
    return actions


# --- assembly -----------------------------------------------------------

_graph = None


def graph():
    global _graph
    if _graph is None:
        builder = StateGraph(State)
        builder.add_node("extract", extract)
        builder.add_node("confirm", confirm)
        builder.add_node("detect", detect)
        builder.add_node("resolve", resolve)
        builder.add_node("commit", commit)
        builder.add_edge(START, "extract")
        builder.add_edge("extract", "confirm")
        # confirm returns a Command, so it routes itself to extract or detect.
        builder.add_edge("detect", "resolve")
        builder.add_edge("resolve", "commit")
        builder.add_edge("commit", END)

        checkpointer = PostgresSaver(store.checkpoint_pool())
        checkpointer.setup()
        _graph = builder.compile(checkpointer=checkpointer)
    return _graph
