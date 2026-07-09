-- Seed de desarrollo · paridad con el fallback in-memory de SupabaseLearningPathRepository.
-- Nota: seed.sql solo corre en `supabase db reset` / stack local, NO en `supabase db push`.
-- Para sembrar el proyecto cloud, ejecutar este SQL en el SQL Editor del dashboard.
-- (El backfill de details para filas ya existentes lo hace la migración
--  20260708140000_learning_path_details.sql.)

insert into public.learning_paths (id, titulo, tema, estado, details) values
    ('00000000-0000-0000-0000-000000000001', 'Inteligencia avanzada', 'Razonamiento', 'en-revision', '{
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
    }'::jsonb),
    ('00000000-0000-0000-0000-000000000002', 'El lado creativo',      'Creatividad',  'generado', '{
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
    }'::jsonb)
on conflict (id) do nothing;
