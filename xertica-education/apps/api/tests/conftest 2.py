"""Aísla la suite de tests de credenciales reales.

Se ejecuta ANTES de importar los módulos de test (y por lo tanto antes de que
config.dependencies construya sus singletons), forzando placeholders: los
repositorios caen a sus fallbacks in-memory (ADR-0004) y ningún test puede
escribir al Supabase de producción ni llamar APIs pagadas, aunque apps/api/.env
tenga credenciales reales.
"""
from config.settings import settings

settings.supabase_url = "https://placeholder-project.supabase.co"
settings.supabase_key = "placeholder-key"
settings.openrouter_key = "placeholder-key"
settings.openai_key = "placeholder-key"
settings.openai_api_key = "placeholder-key"
settings.youtube_api_key = "placeholder-key"
settings.tavily_api_key = "placeholder-key"
settings.google_cloud_project = "placeholder-project"
