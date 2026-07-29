"""What "back" means from each stage.

The rewind itself needs LangGraph and a checkpointer, so it is not unit-tested
here — but *which* of the three things it does is a pure decision, and that is
the part with a right and a wrong answer.
"""

from knowli.application.review import rewind_action


def test_the_resolve_gate_rewinds_to_confirm():
    assert rewind_action("resolve") == "rewind"


def test_the_confirm_gate_has_nowhere_further_back_inside_the_graph():
    # The step before confirm is the text box, not a node. The caller is told
    # nothing moved and repopulates its composer from raw_text.
    assert rewind_action("confirm") == "stay"


def test_a_committed_review_is_not_rewindable():
    # The claims are in the store and may already have been read by someone else.
    assert rewind_action("done") == "refuse"


def test_a_session_still_working_is_left_alone():
    assert rewind_action("extracting") == "stay"
    assert rewind_action("detecting") == "stay"
