import asyncio
from uuid import uuid4

from models.domain.approved_research_source import ApprovedResearchSource
from repositories.approved_research_sources.memory import InMemoryApprovedResearchSourceRepository
from routers.learning_paths import _prepare_research_sources_for_route
from services.research.service import ResearchService


class _GroundedDocs:
    enabled = True

    def search(self, technology: str, context: str):
        return [
            {"title": "Vertex AI docs", "url": "https://cloud.google.com/vertex-ai/docs"},
            {"title": "Community guide", "url": "https://example.org/vertex-guide"},
            {"title": "Video", "url": "https://youtube.com/watch?v=abc"},
        ]


class _NoYoutube:
    enabled = False


class _RankingDocs:
    """Grounded client that also re-ranks: forces the community URL above the official one."""

    enabled = True

    def search(self, technology: str, context: str):
        return [
            {"title": "Vertex AI docs", "url": "https://cloud.google.com/vertex-ai/docs"},
            {"title": "Community guide", "url": "https://example.org/vertex-guide"},
        ]

    def rank_sources(self, sources, context):
        return {
            index: (95 if "example.org" in source.get("url", "") else 20)
            for index, source in enumerate(sources)
        }


def test_grounded_documents_are_classified_and_youtube_is_excluded():
    result = ResearchService(
        youtube_client=_NoYoutube(),
        documentation_client=_GroundedDocs(),
    ).run({"brief": "Curso de Vertex AI"})

    docs = [source for source in result["sources"] if source["kind"] != "youtube"]
    assert [source["verified"] for source in docs] == [True, False]
    assert all("youtube.com" not in source["url"] for source in docs)


def test_llm_reranking_overrides_positional_scores_and_sorts():
    result = ResearchService(
        youtube_client=_NoYoutube(),
        documentation_client=_RankingDocs(),
    ).run({"brief": "Curso de Vertex AI"})

    docs = [source for source in result["sources"] if source["kind"] != "youtube"]
    # The re-ranker scored the community guide highest, so it sorts first.
    assert docs[0]["url"] == "https://example.org/vertex-guide"
    assert docs[0]["relevanceScore"] == 95


def test_reranking_is_noop_without_rank_sources():
    # A grounded client lacking rank_sources must keep positional order untouched.
    result = ResearchService(
        youtube_client=_NoYoutube(),
        documentation_client=_GroundedDocs(),
    ).run({"brief": "Curso de Vertex AI"})
    docs = [source for source in result["sources"] if source["kind"] != "youtube"]
    assert docs[0]["url"] == "https://cloud.google.com/vertex-ai/docs"


def test_research_source_review_policy_auto_approves_discards_and_caps_manual_review():
    sources = [
        {
            "title": "Excellent community doc",
            "url": "https://example.org/excellent",
            "kind": "documentation",
            "verified": False,
            "relevanceScore": 91,
        },
        {
            "title": "Weak community doc",
            "url": "https://example.org/weak",
            "kind": "documentation",
            "verified": False,
            "relevanceScore": 69,
        },
        *[
            {
                "title": f"Candidate {index}",
                "url": f"https://example.org/candidate-{index}",
                "kind": "article",
                "verified": False,
                "relevanceScore": 70 + index,
            }
            for index in range(12)
        ],
        {
            "title": "Video",
            "url": "https://youtube.com/watch?v=abc",
            "kind": "youtube",
            "verified": False,
            "relevanceScore": 95,
        },
    ]

    route_sources, automatic = _prepare_research_sources_for_route(sources)
    manual = [
        source
        for source in route_sources
        if source.get("kind") in {"documentation", "article"}
        and source.get("status") == "requires-review"
    ]

    assert [source["url"] for source in automatic] == ["https://example.org/excellent"]
    assert next(source for source in route_sources if source["url"].endswith("/weak"))["status"] == "rejected"
    assert len(manual) == 5
    assert [source["relevanceScore"] for source in manual] == list(range(81, 76, -1))
    assert any(source["kind"] == "youtube" for source in route_sources)


def test_approved_repository_is_idempotent_and_route_scoped():
    route_id = uuid4()
    repo = InMemoryApprovedResearchSourceRepository()
    source = ApprovedResearchSource(
        route_id=route_id,
        module_id=None,
        tool_name="Vertex AI",
        title="Vertex AI docs",
        url="https://cloud.google.com/vertex-ai/docs",
        domain="cloud.google.com",
        source_type="documentation",
        is_verified=True,
        approval_source="automatic",
    )

    first = asyncio.run(repo.upsert([source]))
    second = asyncio.run(repo.upsert([source]))

    assert first[0].id == second[0].id
    assert asyncio.run(repo.list_by_route(route_id, module_id="m1")) == second
    assert asyncio.run(repo.list_by_route(route_id, module_id="m2")) == second
