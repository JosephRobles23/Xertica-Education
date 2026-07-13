## Notas de Handoff - Xertica Education

### Estructura del Repo

- `apps/api`: backend en FastAPI.
- `apps/web`: frontend en Next.js.
- `supabase/migrations`: schema de base de datos y migraciones de Supabase.
- `docs/adr`: decisiones de arquitectura.
- `apps/api/prompts`: system prompts usados por los servicios de generación.

### Archivos `.env`

Hay dos archivos `.env` y deben vivir exactamente aquí:

- Backend: `apps/api/.env`
- Frontend: `apps/web/.env`

No poner secretos del backend en `apps/web/.env`. Cualquier variable que empiece con `NEXT_PUBLIC_` se expone al navegador.

### Variables del Backend: `apps/api/.env`

Variables requeridas o usadas:

- `SUPABASE_URL`: URL del proyecto de Supabase.
- `SUPABASE_KEY`: service role key de Supabase usada por los repositorios del backend. Nunca exponer en frontend.
- `OPENROUTER_KEY`: key principal para modelos de chat vía OpenRouter.
- `OPENAI_API_KEY`: usada por flujos de OpenAI, especialmente `gpt-image-2` para infografías.
- `VEO_KEY`: placeholder/legacy key de video; el render real de video usa credenciales de Google Vertex.
- `STORAGE_BUCKET`: bucket de Supabase Storage para assets subidos o generados.
- `YOUTUBE_API_KEY`: usada para discovery de fuentes/videos de YouTube.
- `GOOGLE_CLOUD_PROJECT`: proyecto de Google Cloud para Vertex AI.
- `GOOGLE_APPLICATION_CREDENTIALS`: path al JSON de service account para Vertex AI, Imagen y Veo.
- `GOOGLE_DRIVE_CLIENT_ID`: OAuth Web Client ID para Google Drive.
- `GOOGLE_DRIVE_API_KEY`: API key de Google restringida a Google Drive API.
- `GOOGLE_DRIVE_SCOPE`: normalmente `https://www.googleapis.com/auth/drive.file`.

Nota: si existen nombres viejos como `GOOGLE_CLIENT_ID` / `GOOGLE_API_KEY`, conviene alinearlos con `GOOGLE_DRIVE_CLIENT_ID` / `GOOGLE_DRIVE_API_KEY`, que son los que espera `config/settings.py`.

### Variables del Frontend: `apps/web/.env`

Variables requeridas:

- `NEXT_PUBLIC_API_URL`: URL del backend, normalmente `http://localhost:8000`.
- `NEXT_PUBLIC_GOOGLE_DRIVE_CLIENT_ID`: OAuth 2.0 Web Client ID usado por Google Identity Services en el navegador.
- `NEXT_PUBLIC_GOOGLE_DRIVE_API_KEY`: API key pública/restringida usada por Google Picker.
- `NEXT_PUBLIC_GOOGLE_DRIVE_APP_ID`: número del proyecto de Google Cloud. Usualmente es el prefijo numérico antes del guion en el OAuth Client ID.

### Setup de Google Drive

Configurar en Google Cloud:

- Google Drive API habilitada.
- OAuth consent screen configurado.
- OAuth Client ID tipo: `Web application`.
- Authorized JavaScript origin para local dev: `http://localhost:3000`.
- Agregar test users mientras la app OAuth esté en modo testing.
- API key restringida a Google Drive API y al origen del frontend.

Flujo frontend:

- Archivo: `apps/web/src/shared/lib/googleDrive.ts`
- Carga:
  - `https://apis.google.com/js/api.js`
  - `https://accounts.google.com/gsi/client`
- Pide OAuth token con scope `drive.file`.
- Abre Google Picker.
- Envía metadata del archivo seleccionado más `access_token` al backend.

Flujo backend:

- Archivo: `apps/api/routers/google_drive.py`
- `POST /learning-paths/{route_id}/drive-documents`
  - recibe `file_id`, `name`, `mime_type`, `web_view_link`, `access_token`.
  - descarga o exporta el archivo de Drive.
  - lo sube a Supabase Storage.
  - lo parsea con `SimpleParserAdapter`.
  - lo guarda como `Document`.
  - opcionalmente lo registra como `Source` aprobada.
- `POST /learning-paths/{route_id}/export/google-drive`
  - genera markdown final de la ruta.
  - lo sube al Google Drive del usuario autenticado.
  - regresa `webViewLink`.

### Backend

Entry point:

- `apps/api/main.py`

Routers montados:

- `routers/jobs.py`
- `routers/learning_paths.py`
- `routers/kb.py`
- `routers/documents.py`
- `routers/google_drive.py`
- `routers/video.py`

Archivos estáticos:

- Carpeta local: `apps/api/static`
- URL pública: `/static`

Los assets runtime generados, como PDFs, TXT, quizzes, lessons, labs e infografías, no deberían commitearse.

### Servicios Principales del Backend

Se instancian en `apps/api/config/dependencies.py`.

- `RouteService`: CRUD y persistencia de rutas.
- `JobsService`: orquestación de jobs/background tasks.
- `ResearchService`: Deep Research y discovery de fuentes.
- `KBService`: ingestión y consulta de Knowledge Base/RAG.
- `VideoService`: storyboard y render de video.
- `InfographicService`: generación de infografías PNG/PDF.
- `QuizService`: generación de quizzes.
- `LessonService`: generación de lecciones.
- `LabService`: generación de laboratorios listos para Google Classroom.
- `RouteStructurer`: creación de estructura de ruta/módulos/componentes.
- `Linker`: vinculación de fuentes aprobadas con módulos.
- `StorageAdapter`: storage en Supabase o fallback en memoria.

### Modelos y Persistencia

Modelos principales:

- `LearningPath`: ruta. Guarda `titulo`, `tema`, `estado` y `details` como JSON.
- `Module`: módulo de ruta con tipo `intro`, `capsula`, `lab`, `evaluacion`, `cierre`.
- `Component`: componente del módulo con tipo `lesson`, `video`, `lab`, `infografia`, `quiz`.
- `Asset`: asset generado para un componente.
- `Document`: archivo subido localmente o importado desde Drive.
- `Source`: fuente URL/upload/Drive.
- `ApprovedResearchSource`: fuente revisada y aprobada.
- `GroundedChunk`: resultado de KB/RAG.

Tablas importantes en Supabase:

- `learning_paths`
- `modules`
- `components`
- `assets`
- `asset_versions`
- `sources`
- `documents`
- `kb_chunks`
- `source_module_links`
- `approved_research_sources`
- `jobs`

Migraciones:

- Viven en `supabase/migrations`.

### Proveedores y Modelos de IA

Abstracción principal de chat:

- `apps/api/adapters/llm/openrouter.py`
- Interfaz: `BaseLLMAdapter.chat_completion(role, prompt)`
- Usa `OPENROUTER_KEY`.
- Si la key está vacía o tiene `placeholder`, regresa contenido mock.

Mapeo role -> modelo en `apps/api/config/settings.py`:

- `route_structurer`: `gpt-4o-mini`
- `scriptwriter`: `gemini-2.5-pro`
- `infographic_design`: `claude-sonnet`
- `researcher`: `gemini-2.5-pro`

Mapeo interno de nombres para OpenRouter:

- `gemini-2.5-pro` -> `google/gemini-2.5-pro`
- `gemini-2.5-flash` -> `google/gemini-2.5-flash`
- `claude-sonnet` -> `anthropic/claude-3.5-sonnet`
- `claude-haiku-4.5` -> `anthropic/claude-haiku-4.5`
- `gpt-4o-mini` -> `openai/gpt-4o-mini`

Otros modelos/proveedores:

- Embeddings: `openai/text-embedding-3-small`, vía adapter compatible con OpenRouter.
- Ranking de research: `openai/gpt-4o-mini`.
- Research grounding: Gemini/Google Search Grounding o Tavily si `TAVILY_API_KEY` está configurada.
- Infografías: OpenAI Images `gpt-image-2`.
- Imagen/ilustración: `gemini-3.1-flash-image` vía Google Vertex/Gemini image adapter.
- Video generativo: `veo-3.1-generate-001` vía Google Vertex.

### System Prompts

Los prompts viven en `apps/api/prompts`.

#### `route_structurer.py`

Genera la estructura de una ruta:

- título;
- tema;
- objetivo;
- 3 a 8 módulos;
- 2 a 4 componentes por módulo.

Responde JSON estricto.

#### `lesson.py`

Genera una lección didáctica:

- 3 o 4 secciones concisas;
- cada sección incluye ejemplo práctico o ejemplo de código;
- genera glosario de 3 a 5 términos.

Responde JSON con:

- `sections`
- `terms`

#### `quiz.py`

Genera un quiz:

- exactamente 5 preguntas;
- 4 opciones por pregunta;
- una sola respuesta correcta;
- explicación breve por pregunta;
- dificultad fácil a media.

Responde JSON con:

- `questions`

#### `lab.py`

Genera laboratorios prácticos listos para Google Classroom.

El campo principal es:

- `classroomText`

Este texto debe poder copiarse y pegarse directamente en Google Classroom.

El laboratorio debe usar:

- información general de la ruta;
- título, descripción y objetivo del módulo;
- Customer Context;
- Knowledge Base/RAG;
- fuentes aprobadas;
- herramientas o tecnologías detectadas.

Reglas clave:

- no generar laboratorios genéricos;
- si el módulo enseña Gemini, Canva, BigQuery u otra herramienta, el lab debe pedir aplicar esa herramienta;
- si el módulo es conceptual, puede generar simulación, caso guiado o actividad de toma de decisiones;
- debe ser compacto, dinámico y accionable.

También devuelve estructura interna:

- `title`
- `objective`
- `scenario`
- `estimatedTimeMinutes`
- `difficulty`
- `tools`
- `prerequisites`
- `instructions`
- `deliverable`
- `reflectionQuestions`
- `sourceReferences`
- `safetyNotes`

#### `video.py`

Genera storyboards para videos de explicación conceptual.

Reglas:

- usar el objetivo pedagógico del módulo como columna vertebral;
- usar KB como soporte, no como reemplazo del objetivo;
- generar 5 a 7 escenas para 90-120 segundos;
- cada escena incluye intención pedagógica, patrón didáctico, racional visual y grounding.

Tipos visuales soportados:

- `text_card`
- `hero_title`
- `stat_card`
- `callout`
- `comparison`
- `bar_chart`
- `line_chart`
- `pie_chart`
- `kpi_grid`
- `progress_bar`
- `terminal_scene`
- `screenshot_scene`
- `ai_video`
- `ai_illustration`

#### `linker.py`

Asigna fuentes a módulos.

Reglas:

- no inventar fuentes;
- no inventar módulos;
- responder JSON estricto;
- incluir score entre 0 y 1.

#### `research.py`

Prompts de Deep Research.

Funciones:

- detectar tecnologías;
- buscar fuentes;
- rankear fuentes;
- priorizar documentación oficial del vendor correspondiente;
- complementar con terceros solo si agregan valor.

### Frontend

Cliente API:

- `apps/web/src/shared/lib/api.ts`

Usa:

- `NEXT_PUBLIC_API_URL`

Métodos principales:

- `api.request`
- upload local de documentos;
- upload/import desde Google Drive;
- export final a Google Drive;
- creación y polling de jobs;
- Deep Research.

Google Drive frontend:

- `apps/web/src/shared/lib/googleDrive.ts`

Módulos importantes:

- `modules/new-route/NuevaRuta.tsx`: creación de nueva ruta, contexto inicial y uploads.
- `modules/curriculum/EstructuraPropuesta.tsx`: aprobación/edición de estructura propuesta.
- `modules/routes/RouteDetail.tsx`: detalle de ruta, revisión, regeneración y aprobación de fuentes.
- `modules/assets/AssetFinal.tsx`: vista/export del asset final.
- `shared/content/*View.tsx`: previews de lesson, quiz, lab, infographic y video.

### Endpoints Principales

Rutas/contenido:

- `POST /learning-paths/`
- `GET /learning-paths/`
- `GET /learning-paths/{route_id}`
- `PATCH /learning-paths/{route_id}`
- `POST /learning-paths/{route_id}/generate-structure`
- `POST /learning-paths/{route_id}/approve`

Research/fuentes:

- `POST /learning-paths/{route_id}/deep-research`
- `GET /learning-paths/{route_id}/approved-research-sources`
- `POST /learning-paths/{route_id}/research-sources/review`
- `POST /learning-paths/{route_id}/link-sources`
- `GET /learning-paths/{route_id}/source-links`

Regeneración de componentes:

- `POST /learning-paths/{route_id}/modules/{module_id}/lesson/regenerate`
- `POST /learning-paths/{route_id}/modules/{module_id}/lab/regenerate`
- `POST /learning-paths/{route_id}/modules/{module_id}/quiz/regenerate`
- `POST /learning-paths/{route_id}/modules/{module_id}/infographic/regenerate`
- `POST /learning-paths/{route_id}/infographic/regenerate`

Google Drive:

- `POST /learning-paths/{route_id}/drive-documents`
- `POST /learning-paths/{route_id}/export/google-drive`

Video:

- `POST /videos/storyboard`
- `POST /videos/generate`
- `GET /videos/jobs/{job_id}`
- `GET /videos/assets`

Jobs:

- `POST /jobs/`
- `GET /jobs/{job_id}`

KB:

- `POST /kb/query`

## Cómo Correr Localmente

### Backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

URLs por default:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## Validación

### Backend

```bash
cd apps/api
./.venv/bin/python -m unittest
```

### Frontend

```bash
cd apps/web
npm run typecheck
```

## Dependencias

### Backend

Archivo:

- `apps/api/requirements.txt`

Dependencias principales:

- `fastapi`
- `uvicorn`
- `pydantic`
- `pydantic-settings`
- `supabase`
- `httpx`
- `python-multipart`
- `pillow`

### Frontend

Archivo:

- `apps/web/package.json`

Dependencias principales:

- `next`
- `react`
- `react-dom`
- `lucide-react`
- `@radix-ui/*`
- `@dnd-kit/*`
- `class-variance-authority`
- `clsx`
- `tailwind-merge`
- `tailwindcss`
- `sonner`

## Advertencias Importantes para Handoff

- Nunca exponer `SUPABASE_KEY`, `OPENROUTER_KEY`, `OPENAI_API_KEY` ni service-account JSON en frontend.
- Solo variables `NEXT_PUBLIC_*` van en `apps/web/.env`.
- Google Drive necesita OAuth `access_token` del usuario. La API key sola no permite leer/escribir archivos privados.
- Archivos generados bajo `apps/api/static` son runtime outputs y no deberían commitearse.
- Si `OPENROUTER_KEY` es placeholder, muchos flujos regresan mocks.
- Si las credenciales de Supabase son placeholder, repositorios/adapters pueden caer a modo memoria/mock.
- Si `GOOGLE_APPLICATION_CREDENTIALS` falta o apunta mal, fallan Imagen/Veo/Vertex.
- Si `OPENAI_API_KEY` falta, falla la generación de infografías con `gpt-image-2`.
- Si el OAuth consent screen está en testing, hay que agregar manualmente cada usuario de prueba.
- En producción, CORS en `apps/api/main.py` no debería quedarse como `allow_origins=["*"]`.
- El bucket `STORAGE_BUCKET` debe existir en Supabase Storage.
- Las tablas expuestas por Supabase deben tener RLS habilitado y policies correctas.
