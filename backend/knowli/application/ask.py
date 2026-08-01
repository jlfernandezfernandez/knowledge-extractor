"""Global claim retrieval, the grounded answer agent, and contribution history."""

from collections.abc import Iterator
from dataclasses import asdict

from ..domain.ports import ContributionStore, Embedder, InterviewStore, Model


class InvalidQuestion(ValueError):
    pass


class InvalidHistoryCursor(ValueError):
    pass


class AskService:
    """Answers questions from stored claims, with tools for what claims cannot hold."""

    def __init__(
        self,
        store: ContributionStore,
        model: Model,
        embedder: Embedder,
        interviews: InterviewStore,
        *,
        retrieve_limit: int = 8,
    ) -> None:
        self._store = store
        self._model = model
        self._embedder = embedder
        self._interviews = interviews
        self._retrieve_limit = retrieve_limit

    def stream_ask(self, question: str, user_id: str, thread_id: str) -> Iterator[dict]:
        if not question.strip():
            raise InvalidQuestion("question is required")
        claims = self._store.search_claims(
            question, self._embedder.embed([question])[0], self._retrieve_limit
        )
        # Retrieval can legitimately come back empty ("what interviews do I have?"):
        # the prompt, not this guard, keeps the agent inside the claims and the tools.
        claims_payload = [asdict(claim) for claim in claims]
        if claims_payload:
            yield {"type": "claims", "items": claims_payload}
        yield from self._model.stream_answer(
            question,
            claims_payload,
            tools=self._tools(user_id),
            # Namespaced so a guessed thread id cannot read another person's conversation.
            thread_id=f"{user_id}:{thread_id}",
        )
        yield {"type": "done"}

    def _tools(self, user_id: str) -> list:
        """Plain callables: the agent adapter turns their signature and docstring into
        the tool schema, so nothing here depends on the LLM library."""
        store = self._interviews

        def list_my_interviews() -> str:
            """List the interviews assigned to the person asking that are still open,
            with their title, status and request date. Use this whenever they ask about
            their interviews, what they have been asked, or what is pending."""
            interviews = store.list_interviews(user_id, "pending")
            if not interviews:
                return "No open interviews are assigned to this person."
            return "\n".join(
                f"- {interview.title} ({interview.status}, requested "
                f"{interview.created_at:%Y-%m-%d})"
                for interview in interviews
            )

        return [list_my_interviews]


class HistoryService:
    """Read-only history projection that does not require an LLM configuration."""

    def __init__(self, store: ContributionStore) -> None:
        self._store = store

    def history(self, cursor: str | None, limit: int) -> dict:
        try:
            items, next_cursor = self._store.list_history(cursor, limit)
        except ValueError as error:
            raise InvalidHistoryCursor("invalid history cursor") from error
        return {
            "items": [asdict(item) for item in items],
            "next_cursor": next_cursor,
        }
