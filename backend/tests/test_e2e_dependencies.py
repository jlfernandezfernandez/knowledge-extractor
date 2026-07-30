"""Deterministic model dependencies used only by the Compose E2E override."""


def test_e2e_model_and_embedder_make_the_browser_journey_deterministic():
    from knowli.infrastructure.e2e import E2EEmbedder, E2EModel

    model = E2EModel()
    claims = model.extract_claims("Deploy production on Tuesdays.")

    assert [claim.model_dump() for claim in claims] == [
        {
            "draft_key": "",
            "title": "Deployment policy",
            "statement": "Deploy production on Tuesdays.",
            "tags": ["operations"],
        }
    ]
    assert model.find_conflicts(claims, []) == []
    answer = model.answer("When do we deploy?", [{"id": "claim-1"}])
    assert answer.answer == "The approved contribution says: Deploy production on Tuesdays."
    assert answer.cited_ids == ("claim-1",)
    assert E2EEmbedder().embed(["one", "two"]) == [[1.0] + [0.0] * 383] * 2
