"""The `ClaimExtractor` port, implemented against LangChain.

Three calls, one per thing the pipeline needs a model for: read a person's text
into claims, compare a claim against its neighbours, answer a question from
claims. Each is a prompt plus a schema and nothing else — no chains, no agent,
no retries. When one of them misbehaves, the fix is in `prompts.py` or
`schemas.py`, which is the point of keeping them one directory apart.
"""

import json
from collections.abc import Mapping, Sequence

from ...domain.claim import StoredClaim
from .chat_model import structured
from .prompts import ANSWER_SYSTEM, COMPARE_SYSTEM, EXTRACT_SYSTEM
from .schemas import Answer, Comparison, Comparisons, Extraction


class LangChainClaimExtractor:
    """The one implementation of `domain.ports.ClaimExtractor`."""

    def extract(self, text: str) -> Extraction:
        return structured(Extraction).invoke(
            [("system", EXTRACT_SYSTEM), ("human", text)]
        )

    def compare(
        self, claim: Mapping[str, str], candidates: Sequence[StoredClaim]
    ) -> list[Comparison]:
        payload = {
            "new": {"title": claim["title"], "statement": claim["statement"]},
            "existing": [
                {"id": c.id, "title": c.title, "statement": c.statement}
                for c in candidates
            ],
        }
        result: Comparisons = structured(Comparisons).invoke(
            [("system", COMPARE_SYSTEM), ("human", json.dumps(payload, ensure_ascii=False))]
        )
        return result.comparisons

    def answer(self, question: str, claims: Sequence[StoredClaim]) -> Answer:
        context = "\n".join(f"[{c.id}] {c.title}: {c.statement}" for c in claims)
        return structured(Answer).invoke(
            [
                ("system", ANSWER_SYSTEM),
                ("human", f"Claims:\n{context}\n\nQuestion: {question}"),
            ]
        )
