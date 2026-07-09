import asyncio
from uuid import uuid4

from models.domain.approved_research_source import ApprovedResearchSource
from repositories.approved_research_sources.memory import InMemoryApprovedResearchSourceRepository
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


def test_grounded_documents_are_classified_and_youtube_is_excluded():
    result = ResearchService(
        youtube_client=_NoYoutube(),
        documentation_client=_GroundedDocs(),
    ).run({"brief": "Curso de Vertex AI"})

    docs = [source for source in result["sources"] if source["kind"] != "youtube"]
    assert [source["verified"] for source in docs] == [True, False]
    assert all("youtube.com" not in source["url"] for source in docs)


def test_approved_repository_is_idempotent_and_module_scoped():
    route_id = uuid4()
    repo = InMemoryApprovedResearchSourceRepository()
    source = ApprovedResearchSource(
        route_id=route_id,
        module_id="m1",
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
