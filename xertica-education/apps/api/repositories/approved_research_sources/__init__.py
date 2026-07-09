from config.settings import settings


def get_approved_research_source_repository():
    if "placeholder" in settings.supabase_url or "placeholder" in settings.supabase_key:
        from .memory import InMemoryApprovedResearchSourceRepository

        return InMemoryApprovedResearchSourceRepository()
    from .repository import SupabaseApprovedResearchSourceRepository

    return SupabaseApprovedResearchSourceRepository()


__all__ = ["get_approved_research_source_repository"]
