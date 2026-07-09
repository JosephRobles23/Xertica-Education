"""Puerto del generador de Estructura Propuesta (Gate 0 · ADR-0014).

Consolida el material ingestado (parsed_docs · material-first) + brief + customerContext
en una estructura curricular: módulos con sus componentes. Devuelve la estructura en la
shape que consume el frontend/route: [{id, num, name, type, status, contents:[...]}].
"""
from abc import ABC, abstractmethod
from typing import Any


class RouteStructurerInterface(ABC):
    @abstractmethod
    async def generate(
        self, brief: str, customer_context: dict, parsed_docs: list[str]
    ) -> dict[str, Any]:
        """Genera la estructura. `parsed_docs` (material-first) es el esqueleto; brief y
        customer_context encuadran/personalizan. Lanza si el LLM falla o el JSON no valida
        (el Job de Gate 0 lo captura y marca failed · ADR-0014).

        Devuelve {"title": str, "tema": str, "objective": str, "modules": [...]}: `title`
        es el nombre visible de la ruta, `tema` la materia central y `objective` el objetivo
        de aprendizaje redactado — los tres derivados/sintetizados del contenido (no el brief
        literal). El job persiste title/tema en learning_paths.titulo/tema y objective en
        details.objective."""
        ...
