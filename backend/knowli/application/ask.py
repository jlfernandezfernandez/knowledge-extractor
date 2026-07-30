"""Global claim retrieval, cited answers, and contribution history."""

from dataclasses import asdict

from ..domain.claim import ClaimSearchResult
from ..domain.ports import ContributionStore, Embedder, Model

INSUFFICIENT_EVIDENCE = "There is not enough evidence to answer this question."


class InvalidQuestion(ValueError):
    pass


class InvalidHistoryCursor(ValueError):
    pass


class AskService:
    def __init__(
        self,
        store: ContributionStore,
        model: Model,
        embedder: Embedder,
        *,
        retrieve_limit: int = 8,
    ) -> None:
        self._store = store
        self._model = model
        self._embedder = embedder
        self._retrieve_limit = retrieve_limit

    def ask(self, question: str) -> dict:
        if not question.strip():
            raise InvalidQuestion("question is required")
        claims = self._store.search_claims(
            question, self._embedder.embed([question])[0], self._retrieve_limit
        )
        if not claims:
            return {
                "answer": INSUFFICIENT_EVIDENCE,
                "citations": [],
                "sufficient_evidence": False,
            }
        answer = self._model.answer(question, [asdict(claim) for claim in claims])
        retrieved_ids = {claim.id for claim in claims}
        cited_ids = retrieved_ids.intersection(answer.cited_ids)
        citations = [self._citation(claim) for claim in claims if claim.id in cited_ids]
        return {
            "answer": answer.answer,
            "citations": citations,
            "sufficient_evidence": bool(citations),
        }

    def history(self, cursor: str | None, limit: int) -> dict:
        try:
            items, next_cursor = self._store.list_history(cursor, limit)
        except ValueError as error:
            raise InvalidHistoryCursor("invalid history cursor") from error
        return {
            "items": [asdict(item) for item in items],
            "next_cursor": next_cursor,
        }

    @staticmethod
    def _citation(claim: ClaimSearchResult) -> dict:
        return {
            "id": claim.id,
            "title": claim.title,
            "statement": claim.statement,
            "author": claim.author,
            "contribution_id": claim.contribution_id,
            "contribution_created_at": claim.contribution_created_at,
        }
