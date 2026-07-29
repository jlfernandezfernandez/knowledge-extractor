"""The pure decision logic of the pipeline.

Which resolutions a verdict allows, and what a set of human decisions turns
into. Everything else in the pipeline is I/O; this is the part that can be
silently wrong, so it is the part with tests.
"""

from typing import Any

# Which resolutions make sense depends on how the two claims relate. Offering
# every action for every verdict is what the first version did, and it is wrong:
# keeping both sides of a genuine contradiction leaves retrieval to surface two
# incompatible statements and lets the generator pick one arbitrarily — the
# exact failure this project exists to prevent. Conversely, superseding one side
# of a complementary pair throws away information that was worth keeping.
#
# The taxonomy follows the conflict-type split in the 2026 RAG literature
# (temporal / complementary / duplicate), and each verdict carries a recommended
# default so the common case needs no clicking. For a contradiction the default
# is the incoming claim, on the recency prior that the person telling you now is
# describing the current state.
RESOLUTION_POLICY: dict[str, dict] = {
    "conflict": {"allowed": ["keep_new", "keep_old", "merge"], "default": "keep_new"},
    "duplicate": {"allowed": ["keep_old", "keep_new", "merge"], "default": "keep_old"},
    "refines": {"allowed": ["keep_both", "merge", "keep_new"], "default": "keep_both"},
}


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
