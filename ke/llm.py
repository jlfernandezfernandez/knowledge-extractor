"""The two LLM calls this project needs, over any OpenAI-compatible endpoint."""

import json
import re

import httpx

from . import config

EXTRACT_PROMPT = """You turn a person's raw brain-dump into discrete, self-contained \
knowledge claims for a shared knowledge base.

Rules:
- One claim per idea. Split compound statements.
- Each claim must stand alone: no "it", "that", "as mentioned above".
- Write claims in the same language the person used.
- Keep the person's meaning. Do not invent facts, caveats or numbers.
- Drop pleasantries, thinking-out-loud and anything that is not knowledge.

Reply with JSON only, in this shape:
{"atoms": [{"title": "short label", "statement": "the full claim, 1-3 sentences", \
"tags": ["lowercase", "topic", "tags"]}]}"""

COMPARE_PROMPT = """You compare a NEW knowledge claim against EXISTING claims already \
in a knowledge base, and decide how they relate.

For each existing claim, pick exactly one verdict:
- "conflict"   the two cannot both be true, or the new one contradicts/updates the old
- "duplicate"  the same fact, no new information
- "refines"    the new claim adds detail or nuance to the old one, both can stand
- "unrelated"  they only look similar; they are about different things

Be strict about "conflict": disagreement about the same subject, not merely a \
different topic. Explain in one sentence, in the same language as the claims.

Reply with JSON only, in this shape:
{"comparisons": [{"existing_id": "<id>", "verdict": "conflict", "reason": "..."}]}"""


def chat(system: str, user: str) -> dict:
    response = httpx.post(
        f"{config.LLM_API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
        json={
            "model": config.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        },
        timeout=180,
    )
    response.raise_for_status()
    return parse_json(response.json()["choices"][0]["message"]["content"])


def parse_json(text: str) -> dict:
    """Pull a JSON object out of a model reply that may be fenced or prefaced."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model reply: {text[:200]!r}")
    return json.loads(text[start : end + 1])


def extract_atoms(raw_text: str) -> list[dict]:
    atoms = chat(EXTRACT_PROMPT, raw_text).get("atoms", [])
    clean = []
    for atom in atoms:
        title, statement = atom.get("title", "").strip(), atom.get("statement", "").strip()
        if not statement:
            continue
        tags = [str(t).strip().lower() for t in atom.get("tags") or [] if str(t).strip()]
        clean.append({"title": title or statement[:60], "statement": statement, "tags": tags})
    return clean


def compare(new_atom: dict, existing: list[dict]) -> dict[str, dict]:
    """Map existing-claim id -> {"verdict", "reason"}."""
    if not existing:
        return {}
    payload = {
        "new": {"title": new_atom["title"], "statement": new_atom["statement"]},
        "existing": [
            {"id": e["id"], "title": e["title"], "statement": e["statement"]}
            for e in existing
        ],
    }
    result = chat(COMPARE_PROMPT, json.dumps(payload, ensure_ascii=False))
    valid = {"conflict", "duplicate", "refines", "unrelated"}
    by_id = {}
    for item in result.get("comparisons", []):
        verdict = item.get("verdict")
        if verdict in valid:
            by_id[str(item.get("existing_id"))] = {
                "verdict": verdict,
                "reason": item.get("reason", ""),
            }
    return by_id
