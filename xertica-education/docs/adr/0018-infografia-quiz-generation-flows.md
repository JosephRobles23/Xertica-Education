# ADR-0018: Flujos de generacion de Infografia y Quiz

- **Estado:** Aceptado
- **Fecha:** 2026-07-09
- **Ambito:** Infografias, quizzes, generacion de assets finales y UI de revision
- **Relaciona:** ADR-0005 de spine completo, ADR-0011 de KB solo-Via-2, ADR-0017 de revision de fuentes

## Contexto

El branch `feature/infographics2` restaura la capacidad de generar y regenerar
infografias y quizzes despues de que el merge de `feature/infographics2` fuera revertido
en `main`. La funcionalidad no debe depender de volver a traer todo el merge original:
solo se portan las piezas necesarias para que los assets `infografia` y `quiz` funcionen
como parte del spine existente.

El dominio ya admite `infografia` y `quiz` en `CONTENT_KINDS`, en el modelo de
componentes y en las migraciones Supabase. En particular,
`supabase/migrations/20260706120000_init_schema.sql` ya permite ambos tipos en los
`CHECK` constraints de `components.tipo` y `assets.tipo`.

La generacion de quiz depende de grounding via `KnowledgeBaseInterface`; si la KB falla,
el servicio degrada con referencias vacias para no bloquear el flujo completo. La
generacion de infografia depende de OpenAI Images (`gpt-image-2`), de `Pillow` para
empaquetar PNG/PDF y de storage local/Supabase para publicar los artefactos.

La UI de detalle de ruta debe permitir revisar y regenerar infografias y quizzes, pero no
debe mostrar el bloque route-level `Gate 1 - Corpus` en esta rama. La aprobacion/revision
de fuentes documentales se mantiene en el panel contextual de fuentes sugeridas, no en un
gate visible superior.

## Decision

1. Restaurar servicios backend dedicados:
   - `services/infographic/interface.py`
   - `services/infographic/service.py`
   - `services/quiz/interface.py`
   - `services/quiz/service.py`
2. Exponer endpoints de regeneracion en `routers/learning_paths.py`:
   - `POST /learning-paths/{route_id}/infographic/regenerate`
   - `POST /learning-paths/{route_id}/modules/{module_id}/quiz/regenerate`
3. Registrar dependencias en `config/dependencies.py`:
   - `get_infographic_service`
   - `get_quiz_service`
   - `QuizService(llm_adapter=OpenRouterLLMAdapter(), kb=_knowledge_base)`
4. Servir artefactos locales desde `/static` mediante `StaticFiles` en `main.py`.
5. Mantener `pillow>=10.2.0` en `requirements.txt`, `pyproject.toml` y `uv.lock`.
6. Mantener el timeout alto de `httpx.AsyncClient(timeout=300.0)` para llamadas de
   imagen con `gpt-image-2`.
7. Mantener el fallback `build_fallback_prompt` cuando OpenAI rechace prompts con marcas
   o logos corporativos.
8. Restaurar la UI y tipos frontend:
   - `InfografiaView.tsx` muestra PNG, descarga PNG/PDF, feedback y selector de aspect
     ratio.
   - `QuizView.tsx` muestra preguntas y soporta regeneracion/descarga.
   - `ContentPreview.tsx`, `types.ts` y `store/index.tsx` transportan `InfografiaContent`,
     `QuizContent`, `QuizQuestion` y estado de assets.
   - `RouteDetail.tsx` pasa `routeId` y `moduleId` a previews/regeneracion.
9. Ocultar el bloque visual `Gate 1 - Corpus` en `RouteDetail.tsx`. La ruta ya no debe
   renderizar `CorpusSection` ni el CTA `Aprobar corpus` en esa posicion.
10. No versionar artefactos generados en `apps/api/static/`; esos PNG/PDF/TXT son outputs
    runtime y deben quedarse fuera del commit.
11. Agregar cobertura enfocada:
    - `apps/api/tests/test_infographic.py`
    - `apps/api/tests/test_quiz.py`

## Consecuencias

- Infografia y Quiz vuelven a ser assets generables dentro del flujo de ruta sin revertir
  manualmente toda la historia de `main`.
- El backend puede regenerar infografias con feedback y formato (`vertical`, `horizontal`,
  `square`, `auto`) y empaquetar resultados como PNG/PDF.
- El backend puede regenerar quizzes por modulo usando grounding KB cuando este
  disponible y producir PDF/TXT locales.
- El frontend puede disparar regeneraciones desde los paneles de revision y refrescar las
  rutas despues de generar nuevos assets.
- La experiencia de detalle de ruta queda enfocada en modulos y assets; el gate de corpus
  no aparece como bloque superior.
- La persistencia completa en Supabase Storage depende de que exista el bucket configurado
  por `storage_bucket` y de que las credenciales de entorno esten presentes.
- `OPENAI_API_KEY` es obligatorio para generacion real de imagenes y para el LLM usado en
  quiz; sin esa variable, los flujos deben degradar o fallar de forma visible.
- Los tests backend requieren que el entorno Python tenga `pytest` instalado; el venv
  local actual puede necesitar sincronizacion antes de ejecutar esa suite.
