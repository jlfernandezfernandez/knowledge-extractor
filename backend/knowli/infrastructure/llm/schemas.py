"""Structured-output shapes used only by the OpenAI-compatible adapter."""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedClaim(BaseModel):
    title: str
    statement: str
    tags: list[str] = Field(default_factory=list)


class Extraction(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)


class Comparison(BaseModel):
    claim_draft_key: str
    existing_id: str
    verdict: Literal["conflict", "duplicate", "refines", "unrelated"]
    reason: str


class Comparisons(BaseModel):
    comparisons: list[Comparison] = Field(default_factory=list)


class Answer(BaseModel):
    answer: str
