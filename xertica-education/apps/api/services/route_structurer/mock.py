"""Mock determinista de la Estructura Propuesta (regla de oro #1 · ADR-0014).

Se usa cuando la key del LLM es placeholder (dev). Réplica de la estructura que producía
el router antes de esta feature, parametrizada por customerContext.
"""
from .interface import RouteStructurerInterface
from .normalize import to_route_modules
from .service import _fallback_title, _fallback_tema, _fallback_objective


class MockRouteStructurer(RouteStructurerInterface):
    async def generate(
        self, brief: str, customer_context: dict, parsed_docs: list[str]
    ) -> dict:
        area = customer_context.get("area") or "General"
        industry = customer_context.get("industry") or "contexto del cliente"
        audience = customer_context.get("audienceLevel") or "la audiencia objetivo"
        ws = " con Google Workspace" if customer_context.get("usesGoogleWorkspace") == "yes" else ""
        docs_note = f" · {len(parsed_docs)} doc(s) de referencia" if parsed_docs else ""

        modules = to_route_modules([
            {
                "name": f"Fundamentos aplicados para {area} ({industry})",
                "description": f"Conceptos base adaptados a {industry} y {audience}{docs_note}.",
                "type": "intro",
                "target_minutes": 12,
                "components": [
                    {"kind": "lesson", "summary": f"Conceptos base adaptados a {industry} y {audience}{docs_note}."},
                    {"kind": "video", "summary": f"Cápsula con ejemplos del área {area}{ws}."},
                    {"kind": "quiz", "summary": "Evaluación breve con situaciones del cliente."},
                ],
            },
            {
                "name": f"Laboratorio contextualizado para {area}",
                "description": f"Actividad práctica y visual adaptada a la industria {industry} para comprender el flujo de trabajo.",
                "type": "lab",
                "target_minutes": 21,
                "components": [
                    {"kind": "lesson", "summary": "Buenas prácticas y criterios de adopción."},
                    {"kind": "infografia", "summary": f"Mapa visual de casos de uso en {industry}."},
                    {"kind": "lab", "summary": f"Actividad práctica basada en el material del cliente{ws}."},
                ],
            },
        ])
        return {
            "title": _fallback_title(brief),
            "tema": _fallback_tema(brief, customer_context),
            "objective": (
                f"Al finalizar la ruta, {audience} podrá aplicar los conceptos en {area} "
                f"({industry}){docs_note}."
            ),
            "modules": modules,
        }
