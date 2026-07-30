"""The contribution values and rules that must stay true without any I/O."""

import pytest
from pydantic import ValidationError

from knowli.domain.claim import ClaimDraft
from knowli.domain.conflict import ConflictResolution
from knowli.domain.policy import can_transition


def test_reviewing_a_draft_keeps_its_stable_key():
    """Changing the statement must not turn the draft into a new claim."""
    draft = ClaimDraft(
        draft_key="draft-7",
        title="Deployments",
        statement="Deploy on Tuesdays.",
        tags=["release"],
    )

    edited = draft.model_copy(update={"statement": "Deploy on Tuesdays and Fridays."})

    assert edited.draft_key == "draft-7"


def test_contribution_stages_only_move_forward_one_step():
    assert can_transition("claims", "conflicts")
    assert can_transition("conflicts", "commit")
    assert can_transition("commit", "committed")
    assert not can_transition("claims", "commit")
    assert not can_transition("committed", "claims")


def test_merge_resolution_requires_a_replacement_statement():
    with pytest.raises(ValidationError, match="replacement_statement"):
        ConflictResolution(claim_draft_key="draft-7", action="merge")
