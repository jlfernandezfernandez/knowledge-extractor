"""Resumable contribution review as a dependency-injected LangGraph."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from ..domain.claim import ClaimDraft, ClaimToCommit, ContributionStage
from ..domain.conflict import ConflictResolution
from ..domain.contribution import StaleRevision, StoredContribution
from ..domain.ports import ContributionStore, Embedder, Model

DRAFT_NAMESPACE = uuid.UUID("91c9d12d-729a-4c1f-820b-f93b7065cfef")


class ContributionUnavailable(LookupError):
    """The contribution does not exist or is not visible to this caller."""


class ReviewStageError(RuntimeError):
    """The requested review action is not valid at the current stage."""


class InvalidReview(ValueError):
    """The submitted review data does not preserve the graph's invariants."""


class ReviewState(TypedDict, total=False):
    contribution_id: str
    raw_text: str
    revision: int
    summary: str
    claims: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    resolutions: list[dict[str, Any]]
    prepared_claims: list[dict[str, Any]]
    commit_requested: bool
    committed: bool


RewindAction = Literal["rewind", "stay", "refuse"]


def rewind_action(stage: ContributionStage) -> RewindAction:
    if stage == "committed":
        return "refuse"
    if stage == "conflicts":
        return "rewind"
    return "stay"


class ContributionService:
    """Owns contribution authorization, revision checks, and graph resumption."""

    def __init__(
        self,
        store: ContributionStore,
        model: Model,
        embedder: Embedder,
        checkpointer: Any,
        *,
        conflict_limit: int = 5,
    ):
        self._store = store
        self._model = model
        self._embedder = embedder
        self._conflict_limit = conflict_limit
        self._graph = self._build_graph(checkpointer)

    def _build_graph(self, checkpointer: Any):
        builder = StateGraph(ReviewState)
        builder.add_node("extract_claims", self._extract_claims)
        builder.add_node("find_conflicts", self._find_conflicts)
        builder.add_node("prepare_commit", self._prepare_commit)
        builder.add_node("commit_claims", self._commit_claims)
        builder.add_edge(START, "extract_claims")
        builder.add_edge("extract_claims", "find_conflicts")
        builder.add_edge("find_conflicts", "prepare_commit")
        builder.add_conditional_edges(
            "prepare_commit",
            lambda state: "commit_claims" if state.get("commit_requested") else END,
            {"commit_claims": "commit_claims", END: END},
        )
        builder.add_edge("commit_claims", END)
        return builder.compile(
            checkpointer=checkpointer,
            interrupt_after=["extract_claims", "find_conflicts"],
        )

    @staticmethod
    def _config(contribution_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": contribution_id}}

    def _extract_claims(self, state: ReviewState) -> dict[str, Any]:
        extracted = self._model.extract_claims(state["raw_text"])
        claims = []
        for position, item in enumerate(extracted):
            draft = item if isinstance(item, ClaimDraft) else ClaimDraft.model_validate(item)
            statement = draft.statement.strip()
            if not statement:
                continue
            claims.append(
                ClaimDraft(
                    draft_key=str(
                        uuid.uuid5(
                            DRAFT_NAMESPACE,
                            f"{state['contribution_id']}:{position}",
                        )
                    ),
                    title=draft.title.strip() or statement[:60],
                    statement=statement,
                    tags=[tag.strip().lower() for tag in draft.tags if tag.strip()],
                ).model_dump()
            )
        summary = " ".join(claim["statement"] for claim in claims)
        return {"claims": claims, "summary": summary}

    def _find_conflicts(self, state: ReviewState) -> dict[str, Any]:
        claims = [ClaimDraft.model_validate(item) for item in state.get("claims", [])]
        vectors = self._embedder.embed([claim.statement for claim in claims])
        candidates: dict[str, dict[str, Any]] = {}
        for claim, vector in zip(claims, vectors, strict=True):
            for candidate in self._store.search_claims(
                claim.statement, vector, self._conflict_limit
            ):
                candidates[candidate.id] = asdict(candidate)
        found = self._model.find_conflicts(claims, list(candidates.values()))
        conflicts = [
            dict(item)
            for item in found
            if item.get("verdict") != "unrelated"
            and item.get("claim_draft_key") in {claim.draft_key for claim in claims}
            and item.get("existing_id") in candidates
        ]
        return {"conflicts": conflicts}

    def _prepare_commit(self, state: ReviewState) -> dict[str, Any]:
        parsed_resolutions = [
            ConflictResolution.model_validate(resolution)
            for resolution in state.get("resolutions", [])
        ]
        self._validate_resolutions(parsed_resolutions, state.get("conflicts", []))
        resolutions = {
            resolution.claim_draft_key: resolution
            for resolution in parsed_resolutions
        }
        conflicts_by_draft: dict[str, list[dict[str, Any]]] = {}
        for conflict in state.get("conflicts", []):
            conflicts_by_draft.setdefault(conflict["claim_draft_key"], []).append(conflict)

        drafts: list[tuple[ClaimDraft, tuple[str, ...]]] = []
        for raw_claim in state.get("claims", []):
            claim = ClaimDraft.model_validate(raw_claim)
            related = conflicts_by_draft.get(claim.draft_key, [])
            resolution = resolutions.get(claim.draft_key)
            if related and resolution is None:
                raise InvalidReview(f"missing resolution for draft {claim.draft_key}")
            if resolution and resolution.action == "keep_old":
                continue
            supersedes: tuple[str, ...] = ()
            if resolution and resolution.action in {"keep_new", "merge"}:
                supersedes = tuple(dict.fromkeys(item["existing_id"] for item in related))
            if resolution and resolution.action == "merge":
                claim = claim.model_copy(
                    update={"statement": resolution.replacement_statement.strip()}
                )
            drafts.append((claim, supersedes))

        vectors = self._embedder.embed([claim.statement for claim, _ in drafts])
        prepared = [
            {
                "draft_key": claim.draft_key,
                "title": claim.title,
                "statement": claim.statement,
                "tags": list(claim.tags),
                "embedding": vector,
                "supersedes": list(supersedes),
            }
            for (claim, supersedes), vector in zip(drafts, vectors, strict=True)
        ]
        return {"prepared_claims": prepared}

    def _commit_claims(self, state: ReviewState) -> dict[str, Any]:
        claims = [
            ClaimToCommit(
                draft_key=item["draft_key"],
                title=item["title"],
                statement=item["statement"],
                tags=tuple(item.get("tags", [])),
                embedding=tuple(item["embedding"]),
                supersedes=tuple(item.get("supersedes", [])),
            )
            for item in state.get("prepared_claims", [])
        ]
        self._store.commit_claims(
            state["contribution_id"], state["revision"], claims
        )
        return {"committed": True}

    def _owned(self, user_id: str, contribution_id: str) -> StoredContribution:
        contribution = self._store.get_contribution(contribution_id)
        if contribution is None or contribution.author_id != user_id:
            raise ContributionUnavailable(contribution_id)
        return contribution

    @staticmethod
    def _expect_revision(contribution: StoredContribution, revision: int) -> None:
        if contribution.revision != revision:
            raise StaleRevision(contribution.id)

    @staticmethod
    def _validate_resolutions(
        resolutions: list[ConflictResolution],
        conflicts: list[dict[str, Any]],
    ) -> None:
        keys = [resolution.claim_draft_key for resolution in resolutions]
        if len(keys) != len(set(keys)):
            raise InvalidReview("duplicate resolution for a conflicted draft")
        conflicted_keys = {conflict["claim_draft_key"] for conflict in conflicts}
        if set(keys) - conflicted_keys:
            raise InvalidReview("every resolution must target a conflicted draft")

    def _values(self, contribution_id: str) -> ReviewState:
        snapshot = self._graph.get_state(self._config(contribution_id))
        return dict(snapshot.values)

    def _response(self, contribution: StoredContribution) -> dict[str, Any]:
        values = self._values(contribution.id)
        return {
            **asdict(contribution),
            "claims": values.get("claims", []),
            "conflicts": values.get("conflicts", []),
        }

    def capture(
        self,
        user_id: str,
        raw_text: str,
        source: str,
        interview_id: str | None = None,
    ) -> dict[str, Any]:
        contribution = self._store.create_contribution(
            user_id, raw_text, source, interview_id
        )
        self._graph.invoke(
            {
                "contribution_id": contribution.id,
                "raw_text": raw_text,
                "revision": contribution.revision,
                "commit_requested": False,
            },
            self._config(contribution.id),
        )
        values = self._values(contribution.id)
        contribution = self._store.save_review(
            contribution.id,
            contribution.revision,
            "claims",
            values.get("summary", ""),
        )
        self._graph.update_state(
            self._config(contribution.id), {"revision": contribution.revision}
        )
        return self._response(contribution)

    def get(self, user_id: str, contribution_id: str) -> dict[str, Any]:
        return self._response(self._owned(user_id, contribution_id))

    def confirm_claims(
        self,
        user_id: str,
        id: str,
        revision: int,
        claims: list[dict[str, Any]],
    ) -> dict[str, Any]:
        contribution = self._owned(user_id, id)
        self._expect_revision(contribution, revision)
        if contribution.stage != "claims":
            raise ReviewStageError(f"contribution is at stage {contribution.stage}")
        current_keys = {item["draft_key"] for item in self._values(id)["claims"]}
        edited = [ClaimDraft.model_validate(item) for item in claims]
        edited_keys = [item.draft_key for item in edited]
        if len(edited_keys) != len(set(edited_keys)) or set(edited_keys) != current_keys:
            raise InvalidReview("claim draft keys must be preserved")
        self._graph.update_state(
            self._config(id),
            {"claims": [item.model_dump() for item in edited]},
            as_node="extract_claims",
        )
        self._graph.invoke(None, self._config(id))
        contribution = self._store.save_review(
            id, revision, "conflicts", contribution.summary
        )
        self._graph.update_state(
            self._config(id), {"revision": contribution.revision}
        )
        return self._response(contribution)

    def resolve_conflicts(
        self,
        user_id: str,
        id: str,
        revision: int,
        resolutions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        contribution = self._owned(user_id, id)
        self._expect_revision(contribution, revision)
        if contribution.stage != "conflicts":
            raise ReviewStageError(f"contribution is at stage {contribution.stage}")
        parsed = [ConflictResolution.model_validate(item) for item in resolutions]
        self._validate_resolutions(parsed, self._values(id).get("conflicts", []))
        self._graph.update_state(
            self._config(id),
            {
                "resolutions": [item.model_dump() for item in parsed],
                "commit_requested": False,
            },
            as_node="find_conflicts",
        )
        self._graph.invoke(None, self._config(id))
        contribution = self._store.save_review(
            id, revision, "commit", contribution.summary
        )
        self._graph.update_state(
            self._config(id), {"revision": contribution.revision}
        )
        return self._response(contribution)

    def commit(
        self, user_id: str, id: str, revision: int
    ) -> dict[str, Any]:
        contribution = self._owned(user_id, id)
        if contribution.stage == "committed" and contribution.revision == revision + 1:
            return self._response(contribution)
        self._expect_revision(contribution, revision)
        if contribution.stage != "commit":
            raise ReviewStageError(f"contribution is at stage {contribution.stage}")
        self._graph.update_state(
            self._config(id),
            {"revision": revision, "commit_requested": True},
            as_node="prepare_commit",
        )
        self._graph.invoke(None, self._config(id))
        return self._response(self._owned(user_id, id))

    def back(
        self, user_id: str, contribution_id: str, revision: int
    ) -> dict[str, Any]:
        contribution = self._owned(user_id, contribution_id)
        self._expect_revision(contribution, revision)
        action = rewind_action(contribution.stage)
        if action == "refuse":
            raise ReviewStageError("committed contributions cannot be rewound")
        if action == "stay":
            return self._response(contribution)
        contribution = self._store.save_review(
            contribution_id, revision, "claims", contribution.summary
        )
        self._graph.update_state(
            self._config(contribution_id),
            {"revision": contribution.revision, "conflicts": [], "resolutions": []},
            as_node="extract_claims",
        )
        return self._response(contribution)
