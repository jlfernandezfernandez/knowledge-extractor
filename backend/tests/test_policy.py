"""The pure decision logic: given conflicts and a human's resolutions, what gets
written? Everything else in the pipeline is I/O; this is the part that can be
silently wrong, so it is the part with tests. No database, no model."""

from knowli.domain.policy import plan

CLAIMS = [
    {"id": "c0", "title": "Deploys", "statement": "We deploy on Tuesdays."},
    {"id": "c1", "title": "Coffee", "statement": "The good coffee is on floor 3."},
]
CONFLICTS = [
    {"key": "c0::x1", "draft_id": "c0", "stored": {"id": "x1"}, "verdict": "conflict"},
    {"key": "c0::x2", "draft_id": "c0", "stored": {"id": "x2"}, "verdict": "duplicate"},
]
REFINES = [
    {"key": "c0::x3", "draft_id": "c0", "stored": {"id": "x3"}, "verdict": "refines"},
]


def action_for(actions, claim_id):
    return next(a for a in actions if a["claim"]["id"] == claim_id)


def test_claim_without_conflicts_is_written_unchanged():
    actions = plan(CLAIMS, CONFLICTS, {
        "c0::x1": {"action": "keep_new"}, "c0::x2": {"action": "keep_new"},
    })
    coffee = action_for(actions, "c1")
    assert coffee["statement"] == "The good coffee is on floor 3."
    assert coffee["supersedes"] == []


def test_only_the_chosen_stored_claims_are_superseded():
    # keep_old on the duplicate leaves x2 alone; keep_new on the contradiction
    # supersedes x1. The claim is still written once, carrying both outcomes.
    actions = plan(CLAIMS, CONFLICTS, {
        "c0::x1": {"action": "keep_new"}, "c0::x2": {"action": "keep_old"},
    })
    assert action_for(actions, "c0")["supersedes"] == ["x1"]


def test_claim_is_dropped_only_when_every_decision_keeps_the_old_one():
    dropped = plan(CLAIMS, CONFLICTS, {
        "c0::x1": {"action": "keep_old"}, "c0::x2": {"action": "keep_old"},
    })
    assert action_for(dropped, "c0") == {"claim": CLAIMS[0], "skipped": "keep_old"}

    kept = plan(CLAIMS, CONFLICTS, {
        "c0::x1": {"action": "keep_old"}, "c0::x2": {"action": "keep_new"},
    })
    assert "statement" in action_for(kept, "c0")


def test_merge_replaces_the_statement_and_supersedes():
    actions = plan(CLAIMS, CONFLICTS, {
        "c0::x1": {"action": "merge", "statement": "We deploy on Tuesdays and Fridays."},
        "c0::x2": {"action": "keep_old"},
    })
    deploys = action_for(actions, "c0")
    assert deploys["statement"] == "We deploy on Tuesdays and Fridays."
    assert deploys["supersedes"] == ["x1"]


def test_a_missing_resolution_falls_back_to_the_verdicts_recommendation():
    # conflict → keep_new (recency), duplicate → keep_old. So the claim is
    # written and supersedes only the contradicted one.
    actions = plan(CLAIMS, CONFLICTS, {})
    assert action_for(actions, "c0")["supersedes"] == ["x1"]


def test_keep_both_is_rejected_for_a_contradiction():
    # Keeping both sides of a contradiction is what leaves retrieval to surface
    # two incompatible claims. The policy must refuse it, not just hide it.
    try:
        plan(CLAIMS, CONFLICTS, {"c0::x1": {"action": "keep_both"},
                                 "c0::x2": {"action": "keep_old"}})
    except ValueError as error:
        assert "keep_both" in str(error)
        return
    raise AssertionError("expected keep_both to be rejected for a conflict")


def test_keep_both_is_the_default_for_a_complementary_claim():
    actions = plan(CLAIMS, REFINES, {})
    # Nothing is superseded: both claims stay live.
    assert action_for(actions, "c0")["supersedes"] == []
    assert action_for(actions, "c0")["statement"] == "We deploy on Tuesdays."
