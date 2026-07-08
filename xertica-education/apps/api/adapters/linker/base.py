"""Puerto del linker Source↔Módulo (ADR-0012).

Dado el árbol de módulos de una ruta y su pool de fuentes ya recolectadas, asigna cada
módulo a la fuente más pertinente. NO re-busca (eso es deep-research); solo re-rankea lo
que ya hay. Devuelve `SourceModuleLink`s con `score` y `why` (justificación transitoria).
"""
from abc import ABC, abstractmethod

from models.domain.source import Source
from models.domain.source_module_link import SourceModuleLink


class BaseLinker(ABC):
    @abstractmethod
    async def link(
        self, learning_path_id, modules: list[dict], sources: list[Source]
    ) -> list[SourceModuleLink]:
        ...
