-- Seed de desarrollo · paridad con el fallback in-memory de SupabaseLearningPathRepository.
-- Nota: seed.sql solo corre en `supabase db reset` / stack local, NO en `supabase db push`.
-- Para sembrar el proyecto cloud, ejecutar este SQL en el SQL Editor del dashboard.

insert into public.learning_paths (id, titulo, tema, estado) values
    ('00000000-0000-0000-0000-000000000001', 'Inteligencia avanzada', 'Razonamiento', 'en-revision'),
    ('00000000-0000-0000-0000-000000000002', 'El lado creativo',      'Creatividad',  'generado')
on conflict (id) do nothing;
