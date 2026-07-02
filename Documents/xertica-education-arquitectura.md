# Xertica Education — Arquitectura Objetivo

> **Versión:** 0.1 (borrador para revisión de equipo)
> **Alcance:** Arquitectura objetivo completa, con la rebanada **MVP** resaltada en cada sección.
> **Equipo:** Sebas (Video), Santiago (Infografía), Joseph (Knowledge Base), Arantza (Sourcing/Deep Research).
> **Runtime:** Google Cloud Run + Supabase Cloud.

---

## 1. Resumen ejecutivo

**Qué es.** Xertica Education es un **estudio interno de autoría de contenido**: toma la especificación de una ruta de aprendizaje y produce los *assets crudos* (cápsula de video, infografía, base de conocimiento, tutoriales con fuente) con **humano en el loop** en los puntos de decisión caros.

**Qué NO es.** No es un LMS. No reemplaza a Google Classroom: la entrevista es explícita en mantener el control de inscripciones, seguimiento de avance y registros de entrega en Classroom. El output de Xertica Education **alimenta** a Classroom, no compite con él.

**Por qué existe.** Ataca el cuello de botella real de la iniciativa Impulso: hoy la generación de contenido es lo más pesado — ~2 h por cápsula de video, 3–4 h por infografía, más laboratorios y dependencias externas. Ahí está el ROI del piloto.

**MVP (rebanada vertical).** Ruta 1 — *Inteligencia avanzada (Gemini + API Network)*, una de las rápidas — produciendo **un módulo completo end-to-end**: lesson + 1 cápsula de video (~2 min) + 1 infografía + 1 quiz + tutoriales con fuente verificada, pasando por los tres gates HITL. La KB se alimenta por **dos vías**: el deep research de Arantza y el aporte de archivos del propio usuario (estilo NotebookLM). Objetivo: algo demo-able para la 2.ª reunión con Change Management que ejercite las 4 features contra el mismo spine.

---

## 2. Principios de arquitectura

Estos principios gobiernan todas las decisiones y se aplican transversalmente a las 4 features:

1. **Fuente Google verificable como requisito duro.** La información debe ser acreditada y verificable (fuentes Google), nunca de wikis abiertas. Cada asset lleva su `sources[]` como campo de primera clase.
2. **HITL en los puntos caros.** Interrupciones durables antes de gastar: aprobar corpus de fuentes, aprobar guion/storyboard antes del render de Veo, aprobar el asset final antes de marcarlo listo para Classroom.
3. **Duración como restricción, no como recorte posterior.** La longitud fluye como *word budget* desde el frontend hasta el agente de diseño instruccional; el contenido se construye acotado, no se poda después.
4. **Adapters pluggables en todo proveedor.** LLMs, renderizadores de escena y bases de conocimiento se acceden vía puertos intercambiables (`get_llm(role)`, `get_scene_renderer()`, `KnowledgeBase`).
5. **Cost-aware + dry-run.** Todo pipeline tiene modo dry-run de costo cero para validar prompts antes de comprometer gasto de API; el costo se registra por decisión en `provenance`.
6. **Sistemas OSS como servicios, no como código del monorepo.** OpenMontage y similares tienen su propio runtime y datastore; se referencian o se orquestan como servicios externos, no se vendorizan.

---

## 3. Vista de dominio — el *spine* que conecta a los 4 devs

Antes de repartir features, se fija el modelo que las 4 leen y escriben. Sin este spine compartido no hay producto, hay 4 demos sueltas.

`Ruta → Módulo (4–5) → Componente (Lesson | Video | Lab | Infografía | Quiz) → Asset`

```mermaid
erDiagram
    RUTA ||--o{ MODULO : contiene
    MODULO ||--o{ COMPONENTE : agrupa
    COMPONENTE ||--|| ASSET : materializa
    ASSET ||--o{ SOURCE : cita
    ASSET ||--o{ ASSET_VERSION : versiona

    RUTA {
        uuid id PK
        string titulo
        string tema
        text storytelling
        string industria "futuro: banca/retail/etc"
        enum estado "borrador|en_produccion|publicada"
    }
    MODULO {
        uuid id PK
        uuid ruta_id FK
        enum tipo "intro|capsula|lab|evaluacion|cierre"
        int orden
    }
    COMPONENTE {
        uuid id PK
        uuid modulo_id FK
        enum tipo "lesson|video|lab|infografia|quiz"
        int orden
    }
    ASSET {
        uuid id PK
        uuid componente_id FK
        enum tipo
        enum estado "draft|generado|en_revision|aprobado"
        string storage_path
        int word_budget
        jsonb provenance "modelo|pipeline|costo|tiempo"
    }
    SOURCE {
        uuid id PK
        uuid asset_id FK
        string url
        enum tipo "youtube|google_docs|blog_oficial|soporte_google"
        bool verificada_google
    }
    ASSET_VERSION {
        uuid id PK
        uuid asset_id FK
        int version
        timestamp created_at
    }
```

**Tres campos que no son opcionales en `ASSET`:**

- `estado` — habilita los gates HITL.
- `sources[]` (relación `SOURCE`) — links **verificables de Google**; sin esto, el contenido no puede pasar a un cliente.
- `provenance` — qué pipeline/modelo lo generó, costo y tiempo; alimenta la trazabilidad de gasto.

> **Nota MVP:** el spine se implementa completo desde el día 1 (es barato y desbloquea a los 4 devs en paralelo), aunque el MVP solo cargue Ruta 1 con un módulo.

---

## 4. Vista de flujo — el DAG de las 4 features

El requisito de "fuente verificable" reordena al equipo: **el sourcing es la capa de arriba, no una tool suelta.** Hay **dos vías de ingesta** que alimentan la misma KB — (1) el deep research automatizado de Arantza y (2) el aporte del propio usuario (subida de archivos estilo NotebookLM) — y ambas convergen en el Gate 1 y en la KB de Joseph, que es el hub.

```mermaid
flowchart TD
    A[Spec de Ruta / Módulo] --> B
    A --> U

    subgraph Arantza["Vía 1 · Arantza — Deep Research"]
        B[Búsqueda en YouTube y plataformas oficiales Google] --> C[Fuentes verificadas]
    end

    subgraph Upload["Vía 2 · Aporte del usuario (estilo NotebookLM)"]
        U[Subida: PDF · Word · Excel · PPT · imágenes · texto · URL] --> P[Parsing: MinerU + loaders simples]
        P --> C2[Documentos estructurados Markdown/JSON]
    end

    C -.->|Gate 1: aprobar corpus| D
    C2 -.->|Gate 1: aprobar corpus| D

    subgraph Joseph["Joseph — Knowledge Base RAG"]
        D[Ingesta + chunking + embeddings] --> E[(pgvector en Supabase)]
        E --> F[query grounded con citas]
    end

    F --> G[Sebas — Video]
    F --> H[Santiago — Infografía]
    F --> ID[Shared Instructional Designer Graph ??]
    ID --> I[Quiz]
    ID --> L[Lesson & Lab]

    subgraph Sebas["Sebas — Video"]
        G[Guion + storyboard con word budget] -.->|Gate 2: aprobar guion| G2[Render híbrido]
        G2 --> G3[Concat ffmpeg + TTS]
    end

    subgraph Santiago["Santiago — Infografía"]
        H[HTML grounded] --> H2[HTML a PDF]
    end

    subgraph Quiz["Quiz"]
        I[Generación desde KB]
    end

    subgraph LessonLab["Lesson & Lab"]
        L[Generación de estructura Schema-driven]
    end

    G3 --> Z
    H2 --> Z
    I --> Z
    L --> Z
    Z[/Gate 3: aprobar asset final/] --> ZZ[Asset aprobado -> Classroom]
```

**Lectura del DAG:** hay dos vías de ingesta — Arantza (deep research automatizado) y el aporte del usuario (archivos subidos y parseados con MinerU) — que convergen en el Gate 1. Joseph convierte ese corpus aprobado en la capa de grounding (`F`). De esta capa consumen directamente Sebas (Video) y Santiago (Infografía) para que su contenido multimedia esté debidamente grounded, y en paralelo, el **Shared Instructional Designer Graph** consume de `F` para estructurar los borradores de Lessons, Labs y Quizzes usando esquemas definidos. Todo confluye en el Gate 3 para aprobación final antes de Classroom.

> **Nota sobre verificación:** las fuentes de la Vía 1 (Arantza) llegan con el sello *verificable Google*; las de la Vía 2 (aporte del usuario) son responsabilidad de quien las sube y se marcan como *fuente propia* en el Gate 1, con su provenance registrada.

### Render híbrido por tipo de segmento (feature de Sebas)

Cada segmento de video exige una estrategia distinta — este es un aprendizaje clave, no un detalle:

| Segmento | Estrategia | Herramienta | Por qué |
|---|---|---|---|
| Conceptual / cinemático | Generativo | **Veo 3.1** (metáforas visuales, sin rostros) | Veo brilla en lo abstracto; evita *avatar drift* |
| Walkthrough de plataforma | Screenshots reales + Ken Burns + overlays | Playwright + compositor | Veo **alucina** UI real; nunca reproduce producto fielmente |
| Onboarding interactivo | Captura anotada + highlighting | Playwright + overlays | Requiere precisión sobre elementos reales |

> Continuidad del instructor entre segmentos: **voz TTS fija (voice ID)**, no una identidad de avatar persistente.

---

### 4.1. Shared Instructional Designer & Asset Schemas

El subgrafo **Shared Instructional Designer** es un paso de orquestación centralizado que consume las consultas grounded de la base de conocimientos (`KnowledgeBase`) y genera los borradores de lecciones, laboratorios y evaluaciones de forma estructurada para asegurar consistencia pedagógica.

#### Schema: Lesson (Text Asset)

Representa el material teórico de estudio. Estructura del JSON:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LessonAsset",
  "type": "object",
  "properties": {
    "title": { "type": "string" },
    "summary": { "type": "string" },
    "concepts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": { "type": "string" },
          "description": { "type": "string" },
          "key_takeaways": {
            "type": "array",
            "items": { "type": "string" }
          }
        },
        "required": ["name", "description", "key_takeaways"]
      }
    },
    "sections": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "title": { "type": "string" },
          "content_markdown": { "type": "string" },
          "diagram_mermaid": { "type": ["string", "null"] }
        },
        "required": ["title", "content_markdown"]
      }
    },
    "sources": {
      "type": "array",
      "items": { "type": "string" }
    }
  },
  "required": ["title", "summary", "concepts", "sections", "sources"]
}
```

#### Schema: Lab (Practical Exercise)

Representa el laboratorio práctico guiado. Estructura del JSON:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "LabAsset",
  "type": "object",
  "properties": {
    "title": { "type": "string" },
    "objective": { "type": "string" },
    "duration_minutes": { "type": "integer" },
    "requirements": {
      "type": "array",
      "items": { "type": "string" }
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "step_number": { "type": "integer" },
          "title": { "type": "string" },
          "instructions_markdown": { "type": "string" },
          "starter_code": { "type": ["string", "null"] },
          "expected_output": { "type": ["string", "null"] }
        },
        "required": ["step_number", "title", "instructions_markdown"]
      }
    },
    "verification_step": { "type": "string" }
  },
  "required": ["title", "objective", "duration_minutes", "requirements", "steps", "verification_step"]
}
```

---

## 5. Mapa conceptual

```mermaid
mindmap
  root((Xertica Education))
    Producto
      Fábrica de contenido
      Alimenta Classroom
      No es un LMS
    Spine de dominio
      Ruta
      Modulo
      Componente
      Asset con sources y provenance
    Features
      Arantza Sourcing
        Via 1 deep research
        Via 2 uploads del usuario
      Ingesta MinerU
        PDF Word Excel PPT imagenes
        parsing a Markdown JSON
      Joseph KB RAG
      Sebas Video
      Santiago Infografia
    Plataforma
      Turborepo monorepo
      Next.js shadcn radix
      FastAPI uv
      Supabase auth storage postgres
      LangGraph orquestacion
    Capa IA
      get_llm por rol
      OpenRouter ahora LiteLLM fase 2
      pgvector grounding
      Veo REST predictLongRunning
    Principios
      HITL gates
      Fuente Google verificable
      Duracion igual word budget
      Adapters pluggables
      Cost aware y dry run
```

---

## 6. Arquitectura de sistema y despliegue

**Runtime:** Google Cloud Run (contenedores serverless para web y API) + Supabase Cloud (auth, Postgres+pgvector, storage). Los sistemas OSS pesados quedan como servicios/referencia, fuera del monorepo.

```mermaid
flowchart LR
    User[Equipo de contenido<br/>Iran, Katy, etc.] --> Web[Next.js App Router<br/>Cloud Run]
    Web --> API[FastAPI + LangGraph<br/>Cloud Run]

    API --> SB[(Supabase Cloud)]
    SB --> Auth[Supabase Auth<br/>interno Xertica]
    SB --> PG[(Postgres + pgvector<br/>checkpointer LangGraph durable)]
    SB --> Store[Storage<br/>video / pdf / img]

    API --> GW[Gateway LLM<br/>OpenRouter -> LiteLLM fase 2]
    GW --> Prov[Gemini / OpenAI / OpenRouter]

    API --> Veo[Veo 3.1 REST API<br/>predictLongRunning + polling]
    API --> PW[Playwright<br/>screenshots con perfil Google auth]

    API -. patrones de referencia .-> OM[OpenMontage<br/>stage-gates, skills]
```

### Monorepo (Turborepo)

```
xertica-education/
├── apps/
│   ├── web/          # Next.js 15 App Router + Tailwind + shadcn/radix
│   └── api/          # FastAPI + uv  (turbo lo corre vía script -> uv)
├── packages/
│   ├── types/        # tipos TS generados del schema Supabase
│   ├── ui/           # componentes compartidos
│   └── config/       # eslint, tsconfig, tailwind
├── supabase/         # migraciones, RLS, seed, buckets de storage
└── services/         # (fase 2) contenedores auxiliares / compositor Remotion
```

> **Fricción conocida:** Turborepo es JS/TS-nativo. `apps/api` (Python + uv) vive en el monorepo pero se orquesta con un `package.json` que shellea a `uv`. No se pelea por meter Python "puro" al grafo de tareas de Turbo.

---

## 7. Orquestación y HITL

Cada feature es un **subgrafo LangGraph**; un grafo padre *"ruta builder"* hace fan-out. El checkpointer durable vive en **Postgres/Supabase** (reemplaza el in-memory), lo que da persistencia de sesión entre reinicios de Cloud Run.

**Trabajos largos (Veo, deep research) — enfoque MVP ligero:** LangGraph durable + **polling desde FastAPI**. Sin cola dedicada por ahora. Pub/Sub o Cloud Tasks + workers quedan marcados como **fase 2** cuando el volumen lo justifique.

```mermaid
sequenceDiagram
    actor U as Autor
    participant API as FastAPI
    participant LG as LangGraph (durable)
    participant KB as pgvector

    U->>API: Crear ruta / módulo
    API->>LG: start(graph, thread_id)
    LG->>LG: Arantza — sourcing
    LG-->>API: interrupt (Gate 1: corpus)
    API-->>U: Revisar fuentes (polling)
    U->>API: Aprobar corpus
    API->>LG: resume
    LG->>KB: ingesta + grounding
    LG->>LG: Sebas — guion / storyboard
    LG-->>API: interrupt (Gate 2: guion)
    API-->>U: Revisar guion (polling)
    U->>API: Aprobar guion
    API->>LG: resume
    LG->>LG: Render Veo + concat (COSTO REAL)
    LG-->>API: interrupt (Gate 3: asset final)
    U->>API: Aprobar asset
    API->>LG: resume -> marcar listo para Classroom
```

---

## 8. Estrategia de desacople de LLM

Dos capas, y no se confunden entre sí:

**Capa de aplicación — factory por rol, dirigido por config.** El código nunca hardcodea un modelo; pide un rol. Cambiar de modelo = editar YAML, cero código.

```yaml
# models.yaml — única fuente de verdad para elegir modelo
scriptwriter:        gemini-2.5-pro       # Sebas: guion
infographic_design:  claude-sonnet        # Santiago
researcher:          gemini-2.5-flash     # Arantza
quiz_generator:      gpt-4.1-mini
orchestrator:        gemini-2.5-flash
embeddings:          text-embedding-google
```

```python
# get_llm("scriptwriter") -> init_chat_model apuntando al gateway
llm = get_llm("scriptwriter")
```

**Capa operativa — gateway único.**
- **MVP:** OpenRouter directo detrás del factory (ya en uso, ~$20 de crédito).
- **Fase 2:** LiteLLM proxy self-hosted como única salida, con OpenRouter, Vertex/Gemini directo y OpenAI como *upstreams*. Centraliza keys, **budgets por dev/feature**, fallbacks, caché y logging de costo.

---

## 9. Responsabilidades por dev (todas contra el mismo spine)

| Dev | Feature | Entrada | Salida | Notas clave |
|---|---|---|---|---|
| **Arantza** | Sourcing (2 vías) | Spec de ruta · archivos del usuario | `SOURCE[]` (verificados / propios) | **Vía 1:** deep research automatizado (fase 2: apoyarse en el **Deep Research agent** de Google vía Interactions API / A2A). **Vía 2:** ingesta de archivos del usuario (PDF/Word/Excel/PPT/imágenes/texto/URL), estilo NotebookLM. |
| **Joseph** | Knowledge Base (RAG) + parsing | Corpus aprobado + archivos | Grounding + citas | **MVP: pgvector en Supabase.** Parsing de archivos vía adapter **MinerU** (PDF/Office/imágenes → Markdown/JSON), en evaluación. Puerto `KnowledgeBase` con adapter **Gemini Enterprise / NotebookLM** como fase 2 (bloqueado por permisos de licencia). |
| **Shared (ID Graph)** | Instructional Designer | Grounding + citas | `Lesson` (JSON), `Lab` (JSON), `Quiz` (JSON) | Generación paralela utilizando esquemas estructurados de diseño instruccional; actúa como anclaje pedagógico para videos e infografías. |
| **Sebas** | Video | Contenido grounded | Cápsula ~2 min | Pipeline propio (Python + Veo 3.1 REST); **OpenMontage solo como referencia** de patrones (stage-gates, instruction-driven). Render híbrido por segmento. |
| **Santiago** | Infografía | Contenido grounded | PDF | HTML grounded → PDF vía LLM. |

---

## 10. Registro de decisiones (ADR resumido)

| # | Decisión | Razón | Estado |
|---|---|---|---|
| 1 | OpenMontage como **referencia**, no dependencia | Licencia **AGPLv3** (riesgo si se productiza para clientes) + paradigma agent-driven que no encaja como librería en FastAPI. | ✅ Cerrada |
| 2 | KB con **pgvector en Supabase** (no open-notebook, no Gemini Enterprise aún) | open-notebook usa SurrealDB (choca con el estándar Supabase). No hay permisos para habilitar licencia de Gemini Enterprise / NotebookLM Enterprise hoy. | ✅ Cerrada |
| 3 | KB detrás de puerto `KnowledgeBase` | Permite migrar a Gemini Enterprise (grounding + citas nativas Google) sin reescribir consumidores. | ✅ Cerrada |
| 4 | MVP = **rebanada vertical** (Ruta 1, 1 módulo) | Ejercita las 4 features contra el spine y produce demo para Change Management. | ✅ Cerrada |
| 5 | Jobs largos: **LangGraph durable + polling** (sin cola) | Suficiente para el volumen del MVP; cola dedicada = fase 2. | ✅ Cerrada |
| 6 | Gateway LLM: OpenRouter ahora, **LiteLLM fase 2** | Empezar simple; centralizar budgets/fallbacks cuando haya varios devs consumiendo. | ✅ Cerrada |
| 7 | **Segunda vía de ingesta**: aporte de archivos del usuario (estilo NotebookLM) | Dar control al usuario para alimentar la KB con material propio (PDF/Word/Excel/PPT/imágenes/texto/URL), además del deep research automatizado. Ambas vías convergen en el Gate 1. | ✅ Cerrada |
| 8 | **MinerU** como adapter de parsing/OCR de la vía de uploads | Soporta PDF/Office/imágenes nativo, tiene **loader LangChain nativo** y su licencia **ya no es AGPL** (custom basada en Apache 2.0). Correrlo como servicio separado, modo flash/CPU en MVP; precision+GPU en fase 2. | 🔬 En evaluación (spike de 1 día en Cloud Run pendiente) |

---

## 11. Roadmap por fases

**Fase 1 — MVP (rebanada vertical)**
Spine completo · Ruta 1 / 1 módulo end-to-end · **dos vías de ingesta** (Arantza deep research + uploads del usuario con MinerU en modo flash/CPU) → KB(pgvector) → Sebas/Santiago/Quiz · 3 gates HITL · OpenRouter + `get_llm(role)` · Veo generativo (segmento conceptual) + screenshots Playwright · deploy en Cloud Run + Supabase Cloud.

**Fase 2 — Robustez y escala**
LiteLLM proxy con budgets · adapter `KnowledgeBase` → Gemini Enterprise (si se consiguen licencias) · Deep Research agent gestionado para Arantza · **MinerU en modo precision + GPU** (servicio dedicado) · cola dedicada (Pub/Sub / Cloud Tasks) · compositor **Remotion** para segmentos screenshot y overlays animados.

**Fase 3 — Producto**
Rutas 2–7 · videos hasta ~10 min · rutas personalizadas por industria (banca, retail, finanzas) · métrica de adopción de herramientas antes/después vía consola de admin.

---

## 12. Supuestos y preguntas abiertas

**Supuestos vigentes (corregir si aplica):**
- Auth: Supabase Auth, uso interno (empleados Xertica).
- Storage binario: Supabase Storage.
- Playwright con perfil Google autenticado persistente para screenshots de rutas técnicas.
- Modelo de embeddings vía el mismo gateway; pgvector como store.
- El pipeline de video de Sebas se construye desde cero (Python + Veo 3.1 REST con `predictLongRunning` y polling asíncrono).

**Abiertas:**
- ¿Cómo se entrega el asset aprobado a Classroom hoy? (¿Apps Script de Andrés Lazo, subida manual, API?) — define la frontera "listo para Classroom".
- ¿La verificación "fuente Google" es automática (dominios permitidos) o requiere validación humana en el Gate 1? ¿Cómo se marcan las *fuentes propias* de la Vía 2?
- ¿Límite de costo por ruta/módulo para el dry-run vs. run real?
- **MinerU (spike pendiente):** validar en Cloud Run despliegue, latencia y calidad con un PDF/Word/Excel real; revisar las *condiciones adicionales* de su licencia (basada en Apache 2.0) antes de comprometerlo. ¿Self-host (recomendado, la data no sale) o su Open API hospedado?
- ¿Qué formatos de la Vía 2 pasan por MinerU (PDF/Office/imágenes) vs. por loaders simples (texto/URL)?