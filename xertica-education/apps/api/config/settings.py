import os
import json
from pydantic import BaseModel
from typing import Dict

class Settings(BaseModel):
    supabase_url: str = os.getenv("SUPABASE_URL", "https://placeholder-project.supabase.co")
    supabase_key: str = os.getenv("SUPABASE_KEY", "placeholder-key")
    openrouter_key: str = os.getenv("OPENROUTER_KEY", "placeholder-key")
    veo_key: str = os.getenv("VEO_KEY", "placeholder-key")
    storage_bucket: str = os.getenv("STORAGE_BUCKET", "xertica-education-assets")
    
    # Load model_names dict, fallback to standard defaults if env var not set or invalid
    model_names: Dict[str, str] = {
        "route_structurer": "gemini-2.5-pro",
        "scriptwriter": "gemini-2.5-pro",
        "infographic_design": "claude-sonnet",
        "researcher": "gemini-2.5-flash",
    }

    def __init__(self, **data):
        super().__init__(**data)
        env_model_names = os.getenv("MODEL_NAMES")
        if env_model_names:
            try:
                self.model_names = json.loads(env_model_names)
            except Exception:
                pass

settings = Settings()
