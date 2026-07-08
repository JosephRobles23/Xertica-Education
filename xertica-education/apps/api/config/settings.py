import os
import sys
import json
from pathlib import Path
from typing import Dict, Optional
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
    # Google Cloud settings for Vertex AI (Imagen 3 + Veo 3.1)
    google_cloud_project: str = "placeholder-project"
    google_cloud_location: str = "us-central1"
    imagen_model: str = "gemini-2.5-flash-image"
    veo_model: str = "veo-3.1-generate-001"
    google_application_credentials: Optional[str] = None

    # OpenMontage integration (ADR-0010)
    pixabay_api_key: str = ""  # Free API key from pixabay.com — used for background music
    remotion_composer_path: str = ""  # Path to remotion-composer directory (defaults to apps/api/remotion/)

    # Roles funcionales → modelo comercial (ver doc de arquitectura §7).
    # Se puede sobreescribir con la env var MODEL_NAMES como JSON.
    model_names: Dict[str, str] = {
        "route_structurer": "gemini-2.5-pro",
        "scriptwriter": "gemini-2.5-pro",
        "infographic_design": "claude-sonnet",
        "researcher": "gemini-2.5-flash",
    }


settings = Settings()

# Post-load configuration for Google Application Credentials and Project ID
if settings.google_application_credentials:
    cand = settings.google_application_credentials
    # Resolve relative path if it doesn't exist from current CWD
    if not os.path.isabs(cand) and not os.path.exists(cand):
        # Check relative to apps/api/ (where settings.py lives)
        alt_cand = os.path.join(os.path.dirname(os.path.dirname(__file__)), cand)
        if os.path.exists(alt_cand):
            cand = alt_cand

    abs_path = os.path.abspath(cand)
    if os.path.exists(abs_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_path
        # Auto-extract project_id from service account json to overwrite default placeholder
        try:
            with open(abs_path, "r") as f:
                cred_data = json.load(f)
                if "project_id" in cred_data:
                    settings.google_cloud_project = cred_data["project_id"]
        except Exception as e:
            print(f"Warning: Failed to parse service account JSON at {abs_path}: {e}")
    else:
        print(f"Warning: GOOGLE_APPLICATION_CREDENTIALS file not found at {abs_path}")

# OpenMontage path setup (ADR-0010)
_openmontage_root = Path(__file__).resolve().parent.parent.parent.parent / "openmontage"
if _openmontage_root.exists():
    sys.path.insert(0, str(_openmontage_root))

# Remotion composer path
_openmontage_remotion = _openmontage_root / "remotion-composer"
if _openmontage_remotion.exists() and not settings.remotion_composer_path:
    settings.remotion_composer_path = str(_openmontage_remotion)

if not settings.remotion_composer_path:
    _api_remotion = Path(__file__).resolve().parent.parent / "remotion"
    if _api_remotion.exists():
        settings.remotion_composer_path = str(_api_remotion)

