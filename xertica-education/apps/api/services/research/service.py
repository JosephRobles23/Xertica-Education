from typing import Any, Dict, List


TOOL_REGISTRY = [
    {
        "tool": "Veo",
        "vendor": "Google",
        "aliases": ["veo", "veo 3", "teaser", "video generation", "multimedia"],
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
        "aliases": ["nano banana", "identidad visual", "imagen", "foto", "image generation"],
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
        "aliases": ["gemini", "prompt", "razonamiento", "ai studio"],
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
        "aliases": ["bigquery", "datos", "data", "analytics"],
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
        "aliases": ["canva", "diseño", "design"],
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


class ResearchService:
    def detect_tools(self, text: str) -> List[Dict[str, Any]]:
        haystack = text.lower()
        detected = [
            tool
            for tool in TOOL_REGISTRY
            if any(alias in haystack for alias in tool["aliases"])
        ]
        return detected or [TOOL_REGISTRY[2]]

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        brief = payload.get("brief", "")
        modules = payload.get("modules", [])
        route_name = payload.get("route_name", "")
        customer_context = payload.get("customer_context", {}) or {}
        context_text = " ".join(str(value) for value in customer_context.values())
        text = " ".join([route_name, brief, context_text, " ".join(str(module) for module in modules)])
        tools = self.detect_tools(text)
        industry = customer_context.get("industry") or "el contexto del cliente"
        area = customer_context.get("area") or "General"
        audience = customer_context.get("audienceLevel") or "la audiencia definida"
        workspace_suffix = (
            " y flujos de Google Workspace"
            if customer_context.get("usesGoogleWorkspace") == "yes"
            else ""
        )

        sources = []
        for index, tool in enumerate(tools):
            primary_channel = tool["channels"][0]
            primary_domain = tool["domains"][0]
            tool_name = tool["tool"]
            vendor = tool["vendor"]
            official_video = tool["official_video"]
            has_specific_video = bool(official_video.get("youtube_id"))

            sources.extend(
                [
                    {
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
                            "youtubeId": official_video.get("youtube_id"),
                            "videoTitle": official_video["title"],
                        },
                    },
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

        return {
            "detected_tools": [
                {
                    "tool": tool["tool"],
                    "vendor": tool["vendor"],
                    "verifiedChannels": tool["channels"],
                    "verifiedDomains": tool["domains"],
                }
                for tool in tools
            ],
            "sources": sources,
        }
