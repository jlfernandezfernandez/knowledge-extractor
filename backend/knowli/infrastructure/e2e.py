"""Deterministic dependencies enabled only by the Compose E2E override."""

from typing import Any

from ..domain.claim import AnswerResult, ClaimDraft


class E2EModel:
    """A stable model double for exercising the complete browser journey."""

    def extract_claims(self, raw_text: str) -> list[ClaimDraft]:
        return [
            ClaimDraft(
                draft_key="",
                title="Deployment policy",
                statement=raw_text.strip(),
                tags=["operations"],
            )
        ]

    def find_conflicts(
        self, claims: list[ClaimDraft], candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return []

    def answer(self, question: str, claims: list[dict[str, Any]]) -> AnswerResult:
        return AnswerResult(
            answer="The approved contribution says: Deploy production on Tuesdays.",
            cited_ids=tuple(claim["id"] for claim in claims),
        )


class E2EEmbedder:
    """Returns the configured vector width without downloading a local model."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * 383 for _ in texts]
