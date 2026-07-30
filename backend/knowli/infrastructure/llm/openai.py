"""Direct ``langchain_openai`` adapter; no general LangChain dependency."""

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ... import config
from ...domain.claim import ClaimDraft
from .prompts import ANSWER_SYSTEM, COMPARE_SYSTEM, EXTRACT_SYSTEM
from .schemas import Answer, Comparisons, Extraction


class OpenAIModel:
    def __init__(self, chat_model: BaseChatModel | None = None):
        self._chat = chat_model or ChatOpenAI(
            model=config.OPENAI_MODEL,
            api_key=config.OPENAI_API_KEY,
            temperature=0,
        )

    def extract_claims(self, raw_text: str) -> list[ClaimDraft]:
        result = self._chat.with_structured_output(Extraction).invoke(
            [("system", EXTRACT_SYSTEM), ("human", raw_text)]
        )
        extraction = (
            result if isinstance(result, Extraction) else Extraction.model_validate(result)
        )
        return [
            ClaimDraft(
                draft_key="",
                title=claim.title,
                statement=claim.statement,
                tags=claim.tags,
            )
            for claim in extraction.claims
        ]

    def find_conflicts(
        self, claims: list[ClaimDraft], candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        payload = {
            "new": [claim.model_dump() for claim in claims],
            "existing": candidates,
        }
        result = self._chat.with_structured_output(Comparisons).invoke(
            [
                ("system", COMPARE_SYSTEM),
                ("human", json.dumps(payload, ensure_ascii=False, default=str)),
            ]
        )
        comparisons = (
            result if isinstance(result, Comparisons) else Comparisons.model_validate(result)
        )
        return [comparison.model_dump() for comparison in comparisons.comparisons]

    def answer(self, question: str, claims: list[dict]) -> str:
        result = self._chat.with_structured_output(Answer).invoke(
            [
                ("system", ANSWER_SYSTEM),
                (
                    "human",
                    json.dumps(
                        {"claims": claims, "question": question},
                        ensure_ascii=False,
                        default=str,
                    ),
                ),
            ]
        )
        answer = result if isinstance(result, Answer) else Answer.model_validate(result)
        return answer.answer
