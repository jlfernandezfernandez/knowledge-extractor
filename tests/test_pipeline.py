"""The only logic here that can silently do the wrong thing: JSON extraction from a
model reply, and turning conflict decisions into writes. Run with `python -m pytest`
or plain `python tests/test_pipeline.py`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ke.llm import parse_json  # noqa: E402
from ke.pipeline import plan  # noqa: E402

ATOMS = [
    {"id": "a0", "title": "Deploys", "statement": "We deploy on Tuesdays."},
    {"id": "a1", "title": "Coffee", "statement": "The good coffee is on floor 3."},
]
CONFLICTS = [
    {"key": "a0::x1", "atom_id": "a0", "existing_id": "x1", "verdict": "conflict"},
    {"key": "a0::x2", "atom_id": "a0", "existing_id": "x2", "verdict": "duplicate"},
]


def test_parse_json_survives_fences_and_preamble():
    assert parse_json('Sure!\n```json\n{"atoms": []}\n```') == {"atoms": []}
    assert parse_json('{"a": 1}') == {"a": 1}
    assert parse_json('Here you go: {"a": [1, 2]} hope that helps') == {"a": [1, 2]}


def test_atom_without_conflicts_is_inserted_as_is():
    actions = plan(ATOMS, CONFLICTS, {
        "a0::x1": {"action": "keep_new"}, "a0::x2": {"action": "keep_new"},
    })
    coffee = next(a for a in actions if a["atom"]["id"] == "a1")
    assert coffee["statement"] == "The good coffee is on floor 3."
    assert coffee["supersedes"] == []


def test_keep_new_supersedes_only_the_chosen_existing_claims():
    actions = plan(ATOMS, CONFLICTS, {
        "a0::x1": {"action": "keep_new"}, "a0::x2": {"action": "keep_both"},
    })
    deploys = next(a for a in actions if a["atom"]["id"] == "a0")
    assert deploys["supersedes"] == ["x1"]
    assert deploys["statement"] == "We deploy on Tuesdays."


def test_atom_is_dropped_only_when_every_decision_keeps_the_old_claim():
    dropped = plan(ATOMS, CONFLICTS, {
        "a0::x1": {"action": "keep_old"}, "a0::x2": {"action": "keep_old"},
    })
    assert next(a for a in dropped if a["atom"]["id"] == "a0") == {
        "atom": ATOMS[0], "skipped": "keep_old"
    }

    kept = plan(ATOMS, CONFLICTS, {
        "a0::x1": {"action": "keep_old"}, "a0::x2": {"action": "keep_new"},
    })
    assert "statement" in next(a for a in kept if a["atom"]["id"] == "a0")


def test_merge_replaces_the_statement_and_supersedes():
    actions = plan(ATOMS, CONFLICTS, {
        "a0::x1": {"action": "merge", "statement": "We deploy on Tuesdays and Fridays."},
        "a0::x2": {"action": "keep_old"},
    })
    deploys = next(a for a in actions if a["atom"]["id"] == "a0")
    assert deploys["statement"] == "We deploy on Tuesdays and Fridays."
    assert deploys["supersedes"] == ["x1"]


def test_missing_decision_is_an_error_rather_than_a_silent_default():
    try:
        plan(ATOMS, CONFLICTS, {"a0::x1": {"action": "keep_new"}})
    except ValueError:
        return
    raise AssertionError("expected a ValueError for the undecided conflict")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("all good")
