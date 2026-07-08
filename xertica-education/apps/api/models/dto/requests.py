from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Literal
from uuid import UUID

VisualType = Literal[
    "text_card",
    "hero_title",
    "stat_card",
    "callout",
    "comparison",
    "bar_chart",
    "line_chart",
    "pie_chart",
    "kpi_grid",
    "progress_bar",
    "terminal_scene",
    "screenshot_scene",
    "ai_video",
    "ai_illustration",
]

class CreateLearningPathRequest(BaseModel):
    titulo: str
    tema: str
    brief: Optional[str] = None
    document_urls: Optional[List[HttpUrl]] = None

class CreateJobRequest(BaseModel):
    type: str  # e.g., "video_generation", "sourcing"
    payload: dict

class KbQueryRequest(BaseModel):
    """Consulta grounded a la KB (ADR-0006 §6). Aislada por ruta."""
    learning_path_id: UUID
    query: str
    k: int = 8
    verified_only: bool = False
class VideoScene(BaseModel):
    scene_number: int
    narration: str
    visual_type: VisualType
    """Tipo visual alineado con los 14 escenarios de Remotion (ADR-0009).

    Remotion-native (12):
      - text_card       — Large typography beat with spring animation
      - hero_title      — Per-character spring animation for intros
      - stat_card       — Big number with subtitle (e.g., "8.1B people")
      - callout         — Boxed message (info/warning/tip/quote)
      - comparison      — Side-by-side comparison ("before vs after")
      - bar_chart       — Animated bar chart for data comparisons
      - line_chart      — Animated line chart for trends over time
      - pie_chart       — Pie/donut chart for proportions
      - kpi_grid        — 2-4 column KPI grid for dashboards
      - progress_bar    — Animated progress bar for process flows
      - terminal_scene  — Synthetic terminal with typing animation (CLI demos)
      - screenshot_scene — Synthetic UI recording with cursor/click/typing overlays

    Asset-based (2):
      - ai_video        — Veo 3.1 generative video clip (play MP4 directly)
      - ai_illustration — Imagen 3 diagram/illustration with Ken Burns
    """
    visual_config: dict

class StoryboardRequest(BaseModel):
    title: str
    total_word_budget: Optional[int] = 150
    scenes: List[VideoScene]

class GenerateVideoRequest(BaseModel):
    component_id: Optional[UUID] = None
    route_id: Optional[str] = None
    module_id: Optional[str] = None
    component_kind: Optional[str] = None
    custom_storyboard: Optional[StoryboardRequest] = None
    use_mock: Optional[bool] = False
