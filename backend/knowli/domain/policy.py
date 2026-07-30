"""Contribution review rules."""

from .claim import ContributionStage

_NEXT_STAGE: dict[ContributionStage, ContributionStage] = {
    "claims": "conflicts",
    "conflicts": "commit",
    "commit": "committed",
}


def can_transition(current: ContributionStage, target: ContributionStage) -> bool:
    """Whether a contribution may make this one forward stage transition."""
    return _NEXT_STAGE.get(current) == target
