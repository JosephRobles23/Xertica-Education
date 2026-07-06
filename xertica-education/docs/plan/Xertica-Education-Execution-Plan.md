# Xertica Education — Execution Plan

> **Ventana:** Viernes 3 de Julio → Viernes 10 de Julio 2026 (7 días naturales / 5 días hábiles)
> **Hito de entrada:** Mockup End-to-end (hoy, viernes 3) → validación del cliente → arranque del MVP el lunes 6.
> **Hito de salida:** Demo del MVP (Ruta 1 · 1 módulo end-to-end) para Change Management, viernes 10.
> **Equipo:** Joseph (Knowledge Base / Backend spine), Arantza (Sourcing / Deep Research), Sebas (Video), Santiago (Infografía) + Diseño Instruccional compartido (Lesson/Lab/Quiz).

---

## Cómo leer este plan y trabajar en paralelo

- **Desarrollo en paralelo desde el Día 1:** Aunque las fases lógicas del pipeline son secuenciales en ejecución (brief → estructura → fuentes → RAG → generación), **el desarrollo del código es 100% paralelo**. Cada programador trabaja de forma autónoma en su servicio mockeando las entradas/salidas según los contratos establecidos.
- **Uso de Contratos Estables:** Si un servicio aguas arriba no está terminado, los servicios dependientes deben consumir datos mockeados que sigan el esquema estándar (conforme a la regla de oro: *"ningún feature bloquea a otro"*).
- **Gate 0, 1, 2 y 3** actúan como puntos de validación de negocio, pero no bloquean la construcción técnica de otros componentes.

---

## Tabla de referencia

| Fase | Actividad | Resultado | Owner | Depende de | Timeline |
|---|---|---|---|---|---|
| **0. Mockup End-to-end** <br>`[COMPLETADA]` | Cerrar y presentar el mockup navegable que ejercita las 4 features (Sourcing, KB, Video, Infografía) contra el mismo spine, usando Ruta 1 / 1 módulo como caso de referencia. | Mockup validado por el cliente → luz verde para iniciar el MVP real. | Equipo completo | — | **Hoy, Vie 3 Jul** |
| **1. Spine + Infra Setup** <br>`[COMPLETADA]` | Crear el schema en Supabase (`RUTA, MODULO, COMPONENTE, ASSET, SOURCE, ASSET_VERSION`), esqueleto del monorepo (Turborepo: `apps/web`, `apps/api`), y el factory `get_llm(role)` + `models.yaml`. | Spine completo en Postgres/pgvector, listo para que los 4 devs trabajen en paralelo. | Joseph (Ejecutado por Sebas) | Fase 0 (validación del cliente) | **Lun 6 Jul — AM** |
| **2. Gate 0 · Route Builder** <br>`[COMPLETADA]` | `route_structurer` (LLM) propone la estructura de Ruta 1 / Módulo 1 sobre el spine; editor tipo árbol para curar (reordenar, editar, refinamiento granular por nodo); aprobación humana. | Ruta + Módulo + Componente creados con `estado = borrador` → "Spec de Ruta/Módulo" que arranca el DAG. | Joseph (+ frontend) (Ejecutado por Sebas) | Fase 1 | **Lun 6 Jul — PM** |
| **3. Sourcing (2 vías) · Gate 1** <br>`[EN PROGRESO]` | Vía 1: deep research automatizado (YouTube + plataformas oficiales Google). Vía 2: ingesta de archivos del usuario (PDF/Word/Excel/PPT) vía adapter MinerU. Aprobación humana del corpus. | `SOURCE[]` verificadas y/o propias, aprobadas y listas para la KB. | Arantza | Fase 2 (necesita el Spec de Ruta/Módulo) | **Mar 7 Jul — AM** (Gate 1 endpoints e interfaz listos; crawlers de búsqueda y MinerU en desarrollo) |
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

**Riesgo de ruta crítica:** Aunque el desarrollo del código está desacoplado mediante mocks, la ruta crítica de validación de negocio depende de la integración de pgvector (Fase 4). Si la ingesta de MinerU se retrasa, se prioriza el uso de la Vía 1 (deep research de YouTube de Arantza) como fuente principal para no bloquear la validación del RAG.

**Nota sobre el fin de semana:** no hay actividad planeada Sáb 4 / Dom 5 — el plan asume que el cliente valida el mockup el mismo viernes o a más tardar el lunes temprano, para no correr la fase 1.

---

## Guía de Carpetas y Trabajo por Desarrollador

Para evitar conflictos y trabajar de forma simultánea, cada programador tiene asignado su alcance dentro del monorepo y un flujo de mocking claro:

### 1. Arantza (Sourcing & Deep Research)
* **Carpetas de Trabajo:**
  * [apps/api/services/sourcing/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/services/sourcing/) — Lógica del motor de búsqueda (YouTube y Google).
  * [apps/api/adapters/parser/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/adapters/parser/) — Adapter para MinerU.
* **Flujo de Mocking:**
  * Lee el `brief` o estructura de la ruta.
  * Produce objetos `Source`. Mientras programa los crawlers reales, puede alimentar el sistema con un array mock de fuentes en su `mock.py`.

### 2. Joseph (Knowledge Base & Spine DB)
* **Carpetas de Trabajo:**
  * [apps/api/services/kb/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/services/kb/) — Lógica del RAG (embeddings, chunking).
  * [apps/api/repositories/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/repositories/) — Consultas directas a tablas Supabase.
* **Flujo de Mocking:**
  * Consume la lista de `Source` generadas. Mientras Arantza desarrolla la ingesta real, Joseph indexa fragmentos estáticos de prueba para exponer la API RAG.

### 3. Santiago (Lessons & Infographics)
* **Carpetas de Trabajo:**
  * [apps/api/services/lesson/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/services/lesson/) / [apps/api/services/quiz/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/services/quiz/) / [apps/api/services/lab/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/services/lab/) — Prompting y generación.
  * [apps/api/services/infographic/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/services/infographic/) — Renderizador HTML to PDF.
  * [apps/web/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/web/) — Componentes de UI comunes.
* **Flujo de Mocking:**
  * Consume citas de la KB (usando respuestas mock de Joseph si pgvector no está listo) y produce el contenido HTML/Markdown del lesson.

### 4. Sebas (Workflows & Video Capsule)
* **Carpetas de Trabajo:**
  * [apps/api/services/video/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/services/video/) — Storyboards y prompts visuales.
  * [apps/api/adapters/renderer/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/adapters/renderer/) — Render de Google Veo.
  * [apps/api/workflows/](file:///Users/sebastianmoseres/Desktop/All%20Folders/Xertica/Xertica%20Education/xertica-education/apps/api/workflows/) — Orquestadores de pipelines.
* **Flujo de Mocking & Independencia:**
  * El servicio de video se expone de forma aislada a través del router `/videos` con un endpoint dual:
    1. Permite pasar un `component_id` (vía base de datos) para integrarse con la ruta general.
    2. Permite pasar un storyboard JSON de manera directa para desarrollo y pruebas 100% independientes, sin depender de que la base de datos o los servicios de los demás compañeros estén listos.
  * Lee el texto del lesson de Santiago (usando lessons mock si Santiago no ha terminado) y orquesta el pipeline de renderizado de video MP4 final.

