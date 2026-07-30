"""The contribution review's observable rewind decisions."""

from knowli.application.review import rewind_action


def test_conflicts_rewind_to_editable_claims():
    assert rewind_action("conflicts") == "rewind"


def test_claims_have_nowhere_further_back_inside_the_graph():
    assert rewind_action("claims") == "stay"


def test_committed_contributions_are_not_rewindable():
    assert rewind_action("committed") == "refuse"


def test_a_contribution_ready_to_commit_is_left_alone():
    assert rewind_action("commit") == "stay"
