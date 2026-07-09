-- Detalles de la Ruta (objective, customerContext, sources, pack, modules)
-- que antes vivían solo en memoria (RouteService._details) y se perdían en
-- cada restart del API. JSONB único INTERINO: el shape lo define el route
-- service; se normalizará al spine (modules/components/assets) en un slice
-- posterior (ADR-0005).
alter table public.learning_paths
    add column if not exists details jsonb;

-- Backfill de las rutas demo 01/02 (paridad con el fallback in-memory y
-- seed.sql). Idempotente: solo si la fila existe y aún no tiene details.
update public.learning_paths set details = '{
    "objective": "Formar a los equipos para diseñar, evaluar y desplegar sistemas de razonamiento avanzado con criterio.",
    "customerContext": {},
    "sources": [
        { "title": "Cómo razonan los modelos de última generación", "plat": "YouTube", "verified": true, "quote": "El razonamiento en cadena permite..." },
        { "title": "Gemini para educadores", "plat": "Google Docs", "verified": true, "quote": "..." }
    ],
    "pack": {
        "lesson": { "sections": [], "terms": [] },
        "video": { "duration": "02:04", "caption": "", "gradient": "", "emoji": "", "segments": [] },
        "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
        "quiz": { "questions": [] },
        "lab": { "steps": [], "console": [] }
    },
    "modules": [
        { "id": "r1m1", "num": "01", "name": "Introducción", "type": "intro", "status": "aprobado", "contents": [] }
    ]
}'::jsonb
where id = '00000000-0000-0000-0000-000000000001' and details is null;

update public.learning_paths set details = '{
    "objective": "Explorar la generación creativa con criterio.",
    "customerContext": {},
    "sources": [],
    "pack": {
        "lesson": { "sections": [], "terms": [] },
        "video": { "duration": "01:48", "caption": "", "gradient": "", "emoji": "", "segments": [] },
        "infografia": { "title": "", "bullets": [], "footer": ["", ""] },
        "quiz": { "questions": [] },
        "lab": { "steps": [], "console": [] }
    },
    "modules": []
}'::jsonb
where id = '00000000-0000-0000-0000-000000000002' and details is null;
