# ADR-0011: La KB se alimenta solo de Vía 2; las fuentes de Vía 1 se vinculan por módulo, no se ingestan

- **Estado:** Aceptado
- **Fecha:** 2026-07-08
- **Deciden:** Galo (contacto@soygalo.com) · sesión `/grill-with-docs`
- **Ámbito:** `routers/learning_paths.py` (Gate 1), `services/kb/ingestion.py`, frontend `routes/RouteDetail.tsx`
- **Relación:** **revisa** [ADR-0008 §6-§7](0008-document-parsing-via2-ingestion.md) (filtro de corpus); habilitada por [ADR-0012](0012-vinculacion-source-modulo-hibrida.md) (linking source↔módulo).

## Contexto

[ADR-0008 §6](0008-document-parsing-via2-ingestion.md) definió el corpus de ingesta como `verificada_google OR (origin='upload' AND use_as_source)`. Eso mete al KB también las fuentes de **Vía 1** (deep research), que hoy son **URLs de YouTube**. En el código, `RealDocumentProvider.fetch` para `origin != 'upload'` devuelve `_mock_markdown` — **solo título + URL + texto de relleno**: sin transcript no hay texto fiel que trocear ni citar. Resultado: `kb_chunks` se ensucia con huellas de contenido sintético que no aporta grounding.

En paralelo, `main` incorporó un **RouteDetail module-centric** cuyo `findRecommendedYoutubeSource` ya resuelve *qué video de YouTube va en qué módulo* por relevancia — **sin tocar la KB**. Es decir: el valor de una fuente de Vía 1 no es *ser consultada por significado* (RAG), sino *quedar asignada a su módulo*.

## Decisión

1. **El corpus de ingesta RAG se restringe a `origin == 'upload'`** (Vía 2). Las fuentes de Vía 1 **no** entran a `kb_chunks`.

   ```python
   # routers/learning_paths.py · approve_sourcing (Gate 1)
   corpus = [s for s in all_sources if s.origin == "upload"]
   ```

2. **`RealDocumentProvider` deja de sintetizar Markdown para URLs.** El proveedor solo maneja el camino `upload` (lee el binario/`parsed_md`); si llega una fuente sin documento, la ignora en vez de rellenar. `MockDocumentProvider` se conserva solo para tests.

3. **Las fuentes de Vía 1 se aprovechan por vinculación a módulo**, no por ingesta — ver [ADR-0012](0012-vinculacion-source-modulo-hibrida.md). `verificada_google` sigue siendo **metadato de provenance** de la fuente (lo consume el panel Provenance y el scoring de `RouteDetail`), no un gate de ingesta.

## Consecuencias

- **+** El KB solo contiene texto **fiel** (documentos Vía 2 parseados verbatim). Se elimina la clase de chunks-basura y se respeta la regla de oro (nada inventado).
- **+** Menos trabajo en Gate 1: no se ingestan N videos por ruta que no aportaban grounding.
- **+** Separa responsabilidades: la KB *responde con citas*; la vinculación source↔módulo *asigna material de apoyo*. Cada una con su mecanismo.
- **−** Si algún día la Vía 1 trae **transcripts reales** de YouTube, habrá que reabrir el corpus para incluirlos (condicionado, no incondicional como en ADR-0008 §6). Queda como puerta explícita.
- **−** El grounding de la generación depende exclusivamente de que el cliente suba material (Vía 2). Sin uploads, la KB queda vacía y los generadores caen a su comportamiento sin-contexto.
- **Supersesión parcial:** este ADR reemplaza el filtro de [ADR-0008 §6](0008-document-parsing-via2-ingestion.md); el resto de ADR-0008 sigue vigente salvo lo revisado por [ADR-0013](0013-parse-at-upload-parsed-md.md).
