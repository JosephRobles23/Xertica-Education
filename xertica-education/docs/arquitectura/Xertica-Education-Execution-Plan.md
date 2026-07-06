# Xertica Education — Execution Plan

> **Ventana:** Viernes 3 de Julio → Viernes 10 de Julio 2026 (7 días naturales / 5 días hábiles)
> **Hito de entrada:** Mockup End-to-end (hoy, viernes 3) → validación del cliente → arranque del MVP el lunes 6.
> **Hito de salida:** Demo del MVP (Ruta 1 · 1 módulo end-to-end) para Change Management, viernes 10.
> **Equipo:** Joseph (Knowledge Base / Backend spine), Arantza (Sourcing / Deep Research), Sebas (Video), Santiago (Infografía) + Diseño Instruccional compartido (Lesson/Lab/Quiz).

---

## Cómo leer este plan

- **Fase 0 es la puerta de entrada.** Nada de la fase 1 en adelante empieza si el cliente no valida el Mockup end-to-end hoy.
- **Fases 1→2→3→4 son estrictamente secuenciales** (cada una depende del artefacto que produce la anterior: spine → estructura de ruta → fuentes → KB).
- **Fase 5 es el primer punto de paralelismo real**: Lesson/Quiz/Lab, guion de Video y HTML de Infografía se generan en paralelo, todos leyendo de la misma KB (fase 4).
- **Fase 6 vuelve a converger** en el Gate 3 antes del demo final.

---

## Tabla de referencia

| Fase | Actividad | Resultado | Owner | Depende de | Timeline |
|---|---|---|---|---|---|
| **0. Mockup End-to-end** <br>`[COMPLETADA]` | Cerrar y presentar el mockup navegable que ejercita las 4 features (Sourcing, KB, Video, Infografía) contra el mismo spine, usando Ruta 1 / 1 módulo como caso de referencia. | Mockup validado por el cliente → luz verde para iniciar el MVP real. | Equipo completo | — | **Hoy, Vie 3 Jul** |
| **1. Spine + Infra Setup** <br>`[COMPLETADA]` | Crear el schema en Supabase (`RUTA, MODULO, COMPONENTE, ASSET, SOURCE, ASSET_VERSION`), esqueleto del monorepo (Turborepo: `apps/web`, `apps/api`), y el factory `get_llm(role)` + `models.yaml`. | Spine completo en Postgres/pgvector, listo para que los 4 devs trabajen en paralelo. | Joseph (Ejecutado por Sebas) | Fase 0 (validación del cliente) | **Lun 6 Jul — AM** |
| **2. Gate 0 · Route Builder** <br>`[COMPLETADA]` | `route_structurer` (LLM) propone la estructura de Ruta 1 / Módulo 1 sobre el spine; editor tipo árbol para curar (reordenar, editar, refinamiento granular por nodo); aprobación humana. | Ruta + Módulo + Componente creados con `estado = borrador` → "Spec de Ruta/Módulo" que arranca el DAG. | Joseph (+ frontend) (Ejecutado por Sebas) | Fase 1 | **Lun 6 Jul — PM** |
| **3. Sourcing (2 vías) · Gate 1** <br>`[COMPLETADA]` | Vía 1: deep research automatizado (YouTube + plataformas oficiales Google). Vía 2: ingesta de archivos del usuario (PDF/Word/Excel/PPT) vía adapter MinerU. Aprobación humana del corpus. | `SOURCE[]` verificadas y/o propias, aprobadas y listas para la KB. | Arantza (Ejecutado por Sebas) | Fase 2 (necesita el Spec de Ruta/Módulo) | **Mar 7 Jul — AM** (Completada antes de tiempo) |
| **4. Knowledge Base (RAG)** | Ingesta + chunking + embeddings del corpus aprobado en Gate 1; carga en pgvector (Supabase); expone `query grounded con citas` vía puerto `KnowledgeBase`. | Capa de grounding lista — todos los componentes (Lesson, Video, Infografía, Quiz, Lab) pueden consultarla. | Joseph | Fase 3 (corpus aprobado) | **Mar 7 Jul — PM** |
| **5. Generación paralela · Gate 2 (guion)** | En paralelo, todo grounded desde la KB: (a) Lesson + Quiz + Lab (Diseño Instruccional), (b) guion/storyboard de Video con word budget (Sebas) → Gate 2 aprobación de guion, (c) HTML de Infografía (Santiago). | Guion de video aprobado; HTML de infografía listo; Lesson/Quiz/Lab en borrador para revisión. | Diseño Instruccional / Sebas / Santiago | Fase 4 (KB con grounding) | **Mié 8 Jul** |
| **6. Render final** | Video: render híbrido (Veo 3.1 para el segmento conceptual + Playwright para walkthrough) + concat ffmpeg/TTS. Infografía: HTML → PDF. Cierre de Lesson/Quiz/Lab. | Cápsula de video (~2 min), PDF de infografía, y assets de texto completos — todos con `sources[]` y `provenance`. | Sebas / Santiago | Fase 5 (guion y HTML aprobados) | **Jue 9 Jul — AM** |
| **7. Gate 3 · Aprobación final** | Revisión humana del módulo completo (los 5 assets) antes de marcarlo listo para Classroom. | Módulo Ruta 1 aprobado end-to-end, `estado = aprobado`. | Joseph (product owner del spine) | Fase 6 | **Jue 9 Jul — PM** |
| **8. Demo Change Management** | Presentación del MVP (Ruta 1, 1 módulo, las 4 features contra el mismo spine) al comité de Change Management. | Sign-off del MVP / definición de siguientes pasos (Fase 2 del roadmap). | Equipo completo | Fase 7 | **Vie 10 Jul** |

---

## Dependencias críticas (resumen)

```
Fase 0 (Mockup, hoy)
   └─▶ Fase 1 (Spine + Infra)
          └─▶ Fase 2 (Gate 0 · Route Builder)
                 └─▶ Fase 3 (Sourcing · Gate 1)
                        └─▶ Fase 4 (Knowledge Base)
                               └─▶ Fase 5 (Generación paralela · Gate 2)
                                      ├─ Lesson/Quiz/Lab
                                      ├─ Guion Video (Sebas)
                                      └─ HTML Infografía (Santiago)
                                      └─▶ Fase 6 (Render final)
                                             └─▶ Fase 7 (Gate 3 · aprobación)
                                                    └─▶ Fase 8 (Demo)
```

**Riesgo de ruta crítica:** las fases 1→4 son 100% secuenciales — un bloqueo en cualquiera de ellas (p. ej. el spike de MinerU aún "en evaluación" según la arquitectura) corre directamente el resto de la semana. Si MinerU no está listo el martes, usar solo Vía 1 (deep research de Arantza) para no detener el Gate 1.

**Nota sobre el fin de semana:** no hay actividad planeada Sáb 4 / Dom 5 — el plan asume que el cliente valida el mockup el mismo viernes o a más tardar el lunes temprano, para no correr la fase 1.
