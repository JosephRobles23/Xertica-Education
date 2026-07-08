from typing import Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la API cargada desde variables de entorno / apps/api/.env.

    Los valores por defecto son *placeholders* a propósito: los repositorios
    detectan la cadena ``placeholder`` para decidir si usan Supabase real o el
    fallback in-memory (regla de oro #1 del MVP · ADR-0004).
    """

    # env_file relativo al CWD del proceso (apps/api al correr `uv run uvicorn ...`).
    # protected_namespaces=() para permitir el campo `model_names` (pydantic v2
    # reserva el prefijo `model_`). extra="ignore" para no romper con vars
    # ajenas presentes en el entorno.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    supabase_url: str = "https://placeholder-project.supabase.co"
    supabase_key: str = "placeholder-key"
    openrouter_key: str = "placeholder-key"
    openai_key: str = "placeholder-key"
    veo_key: str = "placeholder-key"
    storage_bucket: str = "xertica-education-assets"

    # Embeddings de la KB (ADR-0006). Se sirven vía OpenRouter (OpenAI-compatible)
    # con openrouter_key; con placeholder → MockEmbedder.
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dimension: int = 1536

    # Roles funcionales → modelo comercial (ver doc de arquitectura §7).
    # Se puede sobreescribir con la env var MODEL_NAMES como JSON.
    model_names: Dict[str, str] = {
        "route_structurer": "gemini-2.5-pro",
        "scriptwriter": "gemini-2.5-pro",
        "infographic_design": "claude-sonnet",
        "researcher": "gemini-2.5-flash",
    }


settings = Settings()
