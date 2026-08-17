import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

import httpx

from config.settings import settings
from prompts.research import detect_tools_prompt


TOOL_REGISTRY = [
    {
        "tool": "Veo",
        "vendor": "Google",
        "aliases": ["veo", "veo 3", "veo 3.1"],
        "channels": ["Google AI Developers", "Google Cloud Tech", "Google for Developers"],
        "domains": ["ai.google.dev", "cloud.google.com", "developers.google.com"],
        "official_doc": "https://ai.google.dev/gemini-api/docs/video",
        "official_article": "https://deepmind.google/models/veo/",
        "official_video": {
            "title": "Creating in Flow | How to use Google's new AI Filmmaking Tool",
            "url": "https://www.youtube.com/watch?v=9nVEfjmDlVk",
            "youtube_id": "9nVEfjmDlVk",
            "channel": "Google",
            "duration": "06:42",
        },
    },
    {
        "tool": "Nano Banana",
        "vendor": "Google",
        "aliases": ["nano banana"],
        "channels": ["Google AI Developers", "Google Workspace", "Google for Developers"],
        "domains": ["ai.google.dev", "support.google.com", "workspace.google.com"],
        "official_doc": "https://ai.google.dev/gemini-api/docs/image-generation",
        "official_article": "https://developers.googleblog.com/en/introducing-gemini-2-5-flash-image/",
        "official_video": {
            "title": "Meet Nano Banana Pro: Next-Level AI Image Generation & Editing",
            "url": "https://www.youtube.com/watch?v=AeBOzler4nE",
            "youtube_id": "AeBOzler4nE",
            "channel": "Google",
            "duration": "01:54",
        },
    },
    {
        "tool": "Gemini",
        "vendor": "Google",
        "aliases": ["gemini", "ai studio"],
        "channels": ["Google AI Developers", "Google Workspace", "Google Cloud Tech"],
        "domains": ["ai.google.dev", "developers.google.com", "support.google.com"],
        "official_doc": "https://ai.google.dev/gemini-api/docs",
        "official_article": "https://blog.google/technology/ai/google-gemini-ai/",
        "official_video": {
            "title": "Google Gemini: Supercharge your ideas",
            "url": "https://www.youtube.com/@Google/videos",
            "youtube_id": None,
            "channel": "Google",
            "duration": "--:--",
        },
    },
    {
        "tool": "BigQuery",
        "vendor": "Google Cloud",
        "aliases": ["bigquery", "big query"],
        "channels": ["Google Cloud Tech", "Google Cloud"],
        "domains": ["cloud.google.com"],
        "official_doc": "https://cloud.google.com/bigquery/docs",
        "official_article": "https://cloud.google.com/bigquery",
        "official_video": {
            "title": "BigQuery tutorial from Google Cloud",
            "url": "https://www.youtube.com/@googlecloudtech/videos",
            "youtube_id": None,
            "channel": "Google Cloud Tech",
            "duration": "--:--",
        },
    },
    {
        "tool": "Canva",
        "vendor": "Canva",
        "aliases": ["canva"],
        "channels": ["Canva"],
        "domains": ["canva.com"],
        "official_doc": "https://www.canva.com/help/",
        "official_article": "https://www.canva.com/",
        "official_video": {
            "title": "Canva tutorial from Canva",
            "url": "https://www.youtube.com/@canva/videos",
            "youtube_id": None,
            "channel": "Canva",
            "duration": "--:--",
        },
    },
]

APPROVED_DOCUMENTATION_DOMAINS = {
    "cloud.google.com",
    "ai.google.dev",
    "developers.google.com",
    "firebase.google.com",
    "workspace.google.com",
    "support.google.com",
    "platform.openai.com",
    "help.openai.com",
    "docs.anthropic.com",
    "canva.com",
    "developers.canva.com",
}

TECHNOLOGY_ALIASES = {
    "Vertex AI": ["vertex ai", "vertex"],
    "Firebase": ["firebase", "firestore"],
    "Cloud Run": ["cloud run"],
    "OpenAI": ["openai", "chatgpt"],
    "Anthropic": ["anthropic", "claude"],
}


def _parse_youtube_duration(value: str) -> str:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return "--:--"

    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class YouTubeSearchClient:
    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
    VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and "placeholder" not in self.api_key.lower())

    def search(self, query: str, *, max_results: int = 8) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        with httpx.Client(timeout=10.0) as client:
            search_response = client.get(
                self.SEARCH_URL,
                params={
                    "key": self.api_key,
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": max_results,
                    "safeSearch": "moderate",
                    "videoEmbeddable": "true",
                    "order": "relevance",
                },
            )
            search_response.raise_for_status()
            items = search_response.json().get("items", [])

            video_ids = [
                item.get("id", {}).get("videoId")
                for item in items
                if item.get("id", {}).get("videoId")
            ]
            if not video_ids:
                return []

            details_response = client.get(
                self.VIDEOS_URL,
                params={
                    "key": self.api_key,
                    "part": "contentDetails,statistics",
                    "id": ",".join(video_ids),
                },
            )
            details_response.raise_for_status()
            details_by_id = {
                item["id"]: item
                for item in details_response.json().get("items", [])
                if item.get("id")
            }

        results = []
        for item in items:
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet", {})
            details = details_by_id.get(video_id, {})
            content_details = details.get("contentDetails", {})
            statistics = details.get("statistics", {})

            results.append(
                {
                    "youtube_id": video_id,
                    "title": snippet.get("title") or "Video de YouTube",
                    "channel": snippet.get("channelTitle") or "YouTube",
                    "duration": _parse_youtube_duration(content_details.get("duration", "")),
                    "view_count": int(statistics.get("viewCount") or 0),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )

        return results


class ResearchService:
    def __init__(
        self,
        youtube_client: Optional[YouTubeSearchClient] = None,
        documentation_client=None,
        llm=None,
    ):
        self.youtube_client = youtube_client or YouTubeSearchClient(settings.youtube_api_key)
        self.documentation_client = documentation_client
        self.llm = llm  # rol 'researcher' para la detección abierta (ADR-0024)

    @staticmethod
    def _detection_text(
        route_name: str, brief: str, modules: list, customer_context: Dict[str, Any]
    ) -> str:
        """Texto sobre el que se detectan herramientas. Solo lo que el usuario redactó más
        los campos de contexto textuales: meter todo el customerContext (incluida la URL)
        producía falsos positivos."""
        context_bits = [
            str(customer_context.get(key) or "")
            for key in ("industry", "area", "audienceLevel", "companyName")
        ]
        module_text = " ".join(str(module) for module in modules)
        return " ".join(
            part for part in [route_name, brief, module_text, *context_bits] if part
        )

    def detect_tools(self, text: str) -> List[Dict[str, Any]]:
        """Capa determinista: matchea nombres de producto del registro con límites de
        palabra (evita que 'veo' matchee "veo el problema")."""
        haystack = text.lower()
        return [
            tool
            for tool in TOOL_REGISTRY
            if any(
                re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", haystack)
                for alias in tool["aliases"]
            )
        ]

    async def detect_tools_async(self, text: str) -> List[Dict[str, Any]]:
        """Detección en dos capas (ADR-0024): el LLM identifica las herramientas realmente
        mencionadas (conjunto abierto) y TOOL_REGISTRY verifica las que conoce. Si no hay
        LLM o falla, cae al matching determinista."""
        detected = await self._detect_tools_with_llm(text)
        if detected is None:
            return self.detect_tools(text)
        return [self._resolve_tool(item) for item in detected]

    async def _detect_tools_with_llm(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """Devuelve la lista del LLM, o None si no hay LLM / falla / responde basura."""
        if not self.llm:
            return None
        try:
            raw = await self.llm.chat_completion(
                role="researcher", prompt=detect_tools_prompt(text), timeout=30.0
            )
            match = re.search(r"\[.*\]", raw or "", re.DOTALL)
            if not match:
                return None
            parsed = json.loads(match.group(0))
            if not isinstance(parsed, list):
                return None
            return [
                {"tool": str(item["tool"]).strip(), "vendor": item.get("vendor")}
                for item in parsed
                if isinstance(item, dict) and str(item.get("tool") or "").strip()
            ]
        except Exception as exc:
            print(f"Open tool detection failed, falling back to registry: {exc}")
            return None

    @staticmethod
    def _resolve_tool(detected: Dict[str, Any]) -> Dict[str, Any]:
        """Cruza una herramienta detectada con el registro. Registrada → fuentes oficiales
        verificadas; no registrada → sin canales/dominios, sus fuentes irán a
        'requires-review' (ADR-0017)."""
        name = detected["tool"]
        for entry in TOOL_REGISTRY:
            if entry["tool"].lower() == name.lower() or any(
                alias == name.lower() for alias in entry["aliases"]
            ):
                return entry
        return {
            "tool": name,
            "vendor": detected.get("vendor"),
            "aliases": [name.lower()],
            "channels": [],
            "domains": [],
            "official_doc": None,
            "official_article": None,
            "official_video": None,
        }

    def detect_technologies(self, text: str, tools: List[Dict[str, Any]]) -> list[str]:
        haystack = text.lower()
        names = [tool["tool"] for tool in tools]
        if (
            self.documentation_client
            and self.documentation_client.enabled
            and hasattr(self.documentation_client, "detect_technologies")
        ):
            try:
                for name in self.documentation_client.detect_technologies(text):
                    if name not in names:
                        names.append(name)
            except Exception as exc:
                print(f"Technology detection failed: {exc}")
        for name, aliases in TECHNOLOGY_ALIASES.items():
            if any(alias in haystack for alias in aliases) and name not in names:
                names.append(name)
        return names

    async def _search_youtube(self, query: str) -> List[Dict[str, Any]]:
        """Run a blocking YouTube search off the event loop. Best-effort: [] on failure."""
        if not self.youtube_client.enabled:
            return []
        try:
            return await asyncio.to_thread(self.youtube_client.search, query)
        except Exception as exc:
            print(f"YouTube search failed for {query!r}: {exc}")
            return []

    async def _search_grounded(self, technology: str, context: str) -> List[Dict[str, Any]]:
        """Run a blocking grounded search off the event loop. Best-effort: [] on failure."""
        try:
            return await asyncio.to_thread(self.documentation_client.search, technology, context)
        except Exception as exc:
            print(f"Grounded documentation search failed for {technology}: {exc}")
            return []

    @staticmethod
    def _technology_youtube_query(technology: str, customer_context: Dict[str, Any]) -> str:
        audience = customer_context.get("audienceLevel") or ""
        return f"{technology} tutorial official {audience}".strip()

    def _youtube_sources_for_technology(
        self,
        technology: str,
        videos: List[Dict[str, Any]],
        used_video_ids: set[str],
    ) -> list[dict]:
        trusted_channels = {
            channel.lower()
            for tool in TOOL_REGISTRY
            for channel in tool["channels"]
        }
        sources = []
        for index, video in enumerate(videos):
            youtube_id = video["youtube_id"]
            if youtube_id in used_video_ids:
                continue
            used_video_ids.add(youtube_id)
            verified = video["channel"].strip().lower() in trusted_channels
            sources.append({
                "title": video["title"],
                "plat": "YouTube",
                "kind": "youtube",
                "url": video["url"],
                "verified": verified,
                "status": "approved" if verified else "requires-review",
                "toolName": technology,
                "verificationReason": (
                    f"Video de canal permitido: {video['channel']}"
                    if verified
                    else f"Canal no incluido en allowlist: {video['channel']}"
                ),
                "relevanceScore": max(40, 92 - index * 4),
                "suggestedUse": "video",
                "quote": f"Video encontrado para {technology}.",
                "videoPreview": {
                    "channel": video["channel"],
                    "duration": video["duration"],
                    "gradient": "from-sky-600 via-cyan-500 to-emerald-400",
                    "emoji": "▶",
                    "youtubeId": youtube_id,
                    "videoTitle": video["title"],
                },
            })
        return sources

    @staticmethod
    def _is_verified_document_url(url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in APPROVED_DOCUMENTATION_DOMAINS
        )

    def _grounded_documentation_sources(
        self, results_by_technology: Dict[str, List[Dict[str, Any]]]
    ) -> list[dict]:
        sources = []
        seen_urls: set[str] = set()
        for technology, results in results_by_technology.items():
            for index, result in enumerate(results):
                url = result.get("url", "")
                hostname = (urlparse(url).hostname or "").lower()
                if (
                    not url
                    or url in seen_urls
                    or hostname in {"youtube.com", "www.youtube.com", "youtu.be"}
                ):
                    continue
                seen_urls.add(url)
                verified = self._is_verified_document_url(url)
                sources.append({
                    "title": result.get("title") or f"Documentación de {technology}",
                    "plat": hostname,
                    "kind": "documentation",
                    "url": url,
                    "verified": verified,
                    "status": "approved" if verified else "requires-review",
                    "toolName": technology,
                    "verificationReason": (
                        f"Dominio aprobado: {hostname}"
                        if verified
                        else "Dominio fuera del allowlist; requiere aprobación humana."
                    ),
                    "relevanceScore": max(50, 95 - index * 5),
                    "suggestedUse": "lesson",
                    "quote": "Fuente encontrada con Gemini y Google Search Grounding.",
                    "metadata": result.get("metadata", {}),
                })
        return sources

    def _youtube_query(self, tool: Dict[str, Any], customer_context: Dict[str, Any]) -> str:
        audience = customer_context.get("audienceLevel") or ""
        industry = customer_context.get("industry") or ""
        terms = [tool["tool"], tool["vendor"], "tutorial", "official", audience, industry]
        return " ".join(str(term) for term in terms if term)

    def _is_verified_youtube_channel(self, tool: Dict[str, Any], channel: str) -> bool:
        if not tool["channels"]:
            return False  # herramienta fuera del registro: nada que verificar
        normalized = channel.strip().lower()
        official_video = tool.get("official_video") or {}
        allowed_channels = {
            *(value.lower() for value in tool["channels"]),
            str(official_video.get("channel", "")).lower(),
        }
        return normalized in allowed_channels

    def _youtube_sources_for_tool(
        self,
        tool: Dict[str, Any],
        videos: List[Dict[str, Any]],
        *,
        used_video_ids: set[str],
    ) -> List[Dict[str, Any]]:
        sources = []
        for index, video in enumerate(videos):
            youtube_id = video["youtube_id"]
            if youtube_id in used_video_ids:
                continue
            used_video_ids.add(youtube_id)

            verified = self._is_verified_youtube_channel(tool, video["channel"])
            score = max(40, 96 - index * 4 + min(video["view_count"] // 500000, 8))
            sources.append(
                {
                    "title": video["title"],
                    "plat": "YouTube",
                    "kind": "youtube",
                    "url": video["url"],
                    "verified": verified,
                    "status": "approved" if verified else "requires-review",
                    "toolName": tool["tool"],
                    "vendor": tool["vendor"],
                    "verificationReason": (
                        f"Video de canal permitido para {tool['vendor']}: {video['channel']}"
                        if verified
                        else f"Video específico encontrado en YouTube, pero el canal no está en la lista permitida: {video['channel']}."
                    ),
                    "relevanceScore": score,
                    "suggestedUse": "video",
                    "quote": (
                        f"Video específico encontrado por YouTube Data API para {tool['tool']}."
                    ),
                    "videoPreview": {
                        "channel": video["channel"],
                        "duration": video["duration"],
                        "gradient": "from-sky-600 via-cyan-500 to-emerald-400",
                        "emoji": "▶",
                        "youtubeId": youtube_id,
                        "videoTitle": video["title"],
                    },
                }
            )

        return sources

    def _mock_youtube_source_for_tool(
        self,
        tool: Dict[str, Any],
        index: int,
        area: str,
        industry: str,
        *,
        used_video_ids: set[str],
    ) -> Dict[str, Any]:
        tool_name = tool["tool"]
        vendor = tool["vendor"]
        official_video = tool.get("official_video") or self._search_placeholder_video(tool_name)
        youtube_id = official_video.get("youtube_id")
        has_specific_video = bool(youtube_id and youtube_id not in used_video_ids)
        if youtube_id:
            used_video_ids.add(youtube_id)

        return {
            "title": official_video["title"],
            "plat": "YouTube",
            "kind": "youtube",
            "url": official_video["url"],
            "verified": has_specific_video,
            "status": "approved" if has_specific_video else "requires-review",
            "toolName": tool_name,
            "vendor": vendor,
            "verificationReason": (
                f"Video específico del canal permitido para {vendor}: {official_video['channel']}"
                if has_specific_video
                else f"Canal permitido identificado ({official_video['channel']}), pero falta seleccionar un video específico."
            ),
            "relevanceScore": 94 - index if has_specific_video else 78 - index,
            "suggestedUse": "video",
            "quote": (
                f"Video específico recomendado para introducir {tool_name} con ejemplos de {area} en {industry}."
                if has_specific_video
                else f"Candidato para búsqueda manual: elegir un video concreto de {official_video['channel']} antes de aprobar."
            ),
            "videoPreview": {
                "channel": official_video["channel"],
                "duration": official_video["duration"],
                "gradient": "from-sky-600 via-cyan-500 to-emerald-400",
                "emoji": "▶",
                "youtubeId": youtube_id,
                "videoTitle": official_video["title"],
            },
        }

    def _search_placeholder_video(self, tool_name: str) -> Dict[str, Any]:
        """Candidato de búsqueda para una herramienta sin canal oficial en el registro.
        Nunca se auto-aprueba: sin `youtube_id` la fuente queda en 'requires-review'."""
        query = quote_plus(f"{tool_name} tutorial oficial")
        return {
            "title": f"Buscar videos oficiales de {tool_name}",
            "url": f"https://www.youtube.com/results?search_query={query}",
            "youtube_id": None,
            "channel": f"(sin canal verificado para {tool_name})",
            "duration": "--:--",
        }

    async def _apply_reranking(self, sources: List[Dict[str, Any]], context: str) -> List[Dict[str, Any]]:
        """Replace positional relevanceScore with LLM-judged scores and sort desc.

        No-op (keeps positional scores and order) when the documentation client
        is a mock/disabled or the ranking call fails, so the pipeline never breaks.
        """
        client = self.documentation_client
        if not client or not getattr(client, "enabled", False):
            return sources
        if not hasattr(client, "rank_sources"):
            return sources
        try:
            scores = await asyncio.to_thread(client.rank_sources, sources, context)
        except Exception as exc:
            print(f"Source re-ranking failed: {exc}")
            return sources
        if not scores:
            return sources
        for index, source in enumerate(sources):
            if index in scores:
                source["relevanceScore"] = scores[index]
        return sorted(sources, key=lambda source: source.get("relevanceScore", 0), reverse=True)

    async def _fetch_research_inputs(
        self,
        technologies: list[str],
        tools: List[Dict[str, Any]],
        text: str,
        customer_context: Dict[str, Any],
    ) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
        """Run every external search (grounding + YouTube) concurrently.

        Returns ({technology: grounded results}, {tool/technology name: videos}).
        """
        grounding_enabled = bool(
            self.documentation_client and self.documentation_client.enabled
        )
        grounding_techs = technologies if grounding_enabled else []

        registered_names = {tool["tool"] for tool in tools}
        video_queries: dict[str, str] = {
            tool["tool"]: self._youtube_query(tool, customer_context) for tool in tools
        }
        for technology in technologies:
            if technology not in registered_names:
                video_queries[technology] = self._technology_youtube_query(
                    technology, customer_context
                )

        video_names = list(video_queries)
        results = await asyncio.gather(
            *(self._search_grounded(technology, text) for technology in grounding_techs),
            *(self._search_youtube(video_queries[name]) for name in video_names),
        )
        grounded_by_technology = dict(zip(grounding_techs, results[: len(grounding_techs)]))
        videos_by_name = dict(zip(video_names, results[len(grounding_techs):]))

        if grounding_techs and hasattr(self.documentation_client, "resolve_redirects"):
            urls = [
                result["url"]
                for grounded in grounded_by_technology.values()
                for result in grounded
                if result.get("url")
            ]
            resolved = await self.documentation_client.resolve_redirects(urls)
            for grounded in grounded_by_technology.values():
                for result in grounded:
                    if result.get("url"):
                        result["url"] = resolved.get(result["url"], result["url"])

        return grounded_by_technology, videos_by_name

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        brief = payload.get("brief", "")
        modules = payload.get("modules", [])
        route_name = payload.get("route_name", "")
        customer_context = payload.get("customer_context", {}) or {}
        text = self._detection_text(route_name, brief, modules, customer_context)
        tools = await self.detect_tools_async(text)
        technologies = await asyncio.to_thread(self.detect_technologies, text, tools)
        # Sin herramientas detectadas se sigue con el tema del brief: no se fuerza
        # ningún vendor por defecto (ADR-0024).
        industry = customer_context.get("industry") or "el contexto del cliente"
        area = customer_context.get("area") or "General"
        audience = customer_context.get("audienceLevel") or "la audiencia definida"
        workspace_suffix = ""

        grounded_by_technology, videos_by_name = await self._fetch_research_inputs(
            technologies, tools, text, customer_context
        )
        grounded_sources = self._grounded_documentation_sources(grounded_by_technology)
        sources = []
        used_video_ids: set[str] = set()
        for index, tool in enumerate(tools):
            # Una herramienta detectada fuera del registro (ADR-0024) no trae canal ni
            # dominio oficial: sus fuentes van a revisión humana en vez de inventarlas.
            primary_channel = (tool["channels"] or [None])[0]
            primary_domain = (tool["domains"] or [None])[0]
            tool_name = tool["tool"]
            vendor = tool["vendor"]
            youtube_sources = self._youtube_sources_for_tool(
                tool,
                videos_by_name.get(tool_name, []),
                used_video_ids=used_video_ids,
            )
            if not youtube_sources:
                youtube_sources = [
                    self._mock_youtube_source_for_tool(
                        tool,
                        index,
                        area,
                        industry,
                        used_video_ids=used_video_ids,
                    )
                ]

            legacy_documentation = [] if (grounded_sources or not primary_domain) else [
                {
                    "title": f"Documentación oficial de {tool_name}",
                    "plat": primary_domain,
                    "kind": "documentation",
                    "url": tool["official_doc"],
                    "verified": True,
                    "status": "approved",
                    "toolName": tool_name,
                    "vendor": vendor,
                    "verificationReason": f"Dominio oficial permitido para {vendor}: {primary_domain}",
                    "relevanceScore": 91 - index,
                    "suggestedUse": "lesson",
                    "quote": f"Referencia oficial para aterrizar conceptos, restricciones y buenas prácticas de {tool_name} para {audience}{workspace_suffix}.",
                },
                {
                    "title": f"{tool_name}: referencia oficial del producto",
                    "plat": primary_domain,
                    "kind": "article",
                    "url": tool["official_article"],
                    "verified": True,
                    "status": "approved",
                    "toolName": tool_name,
                    "vendor": vendor,
                    "verificationReason": f"Página oficial permitida para {vendor}: {primary_domain}",
                    "relevanceScore": 87 - index,
                    "suggestedUse": "general",
                    "quote": f"Fuente oficial concreta para contextualizar qué es {tool_name} y cuándo usarlo en {industry}.",
                },
            ]

            sources.extend(
                [
                    *youtube_sources,
                    *legacy_documentation,
                    {
                        "title": f"{tool_name}: ejemplo comunitario para inspiración",
                        "plat": "YouTube",
                        "kind": "youtube",
                        "url": f"https://www.youtube.com/results?search_query={tool_name.replace(' ', '+')}+tips",
                        "verified": False,
                        "status": "requires-review",
                        "toolName": tool_name,
                        "vendor": vendor,
                        "verificationReason": "No coincide con un canal o dominio permitido; requiere revisión humana.",
                        "relevanceScore": 67 - index,
                        "suggestedUse": "general",
                        "quote": "Puede servir para inspiración, pero no debe alimentar el curso sin aprobación explícita.",
                        "videoPreview": {
                            "channel": "Canal no verificado",
                            "duration": "11:03",
                            "gradient": "from-zinc-500 via-slate-500 to-stone-500",
                            "emoji": "?",
                            "videoTitle": f"{tool_name}: trucos y ejemplos",
                        },
                    },
                ]
            )

        registered_names = {tool["tool"] for tool in tools}
        for technology in technologies:
            if technology not in registered_names:
                sources.extend(
                    self._youtube_sources_for_technology(
                        technology,
                        videos_by_name.get(technology, []),
                        used_video_ids,
                    )
                )
        sources.extend(grounded_sources)
        sources = await self._apply_reranking(sources, text)
        return {
            "detected_tools": [
                {
                    "tool": technology,
                    "vendor": next(
                        (tool["vendor"] for tool in tools if tool["tool"] == technology),
                        None,
                    ),
                    "verifiedChannels": next(
                        (tool["channels"] for tool in tools if tool["tool"] == technology),
                        [],
                    ),
                    "verifiedDomains": sorted(APPROVED_DOCUMENTATION_DOMAINS),
                }
                for technology in technologies
            ],
            "sources": sources,
        }
