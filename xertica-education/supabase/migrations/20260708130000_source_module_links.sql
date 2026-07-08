-- ADR-0012: vinculación Source↔Módulo. Qué fuente (típicamente un video de Vía 1)
-- corresponde a qué módulo de la ruta. `origin` distingue la heurística (frontend) del
-- linker LLM (Job on-demand); hoy solo el linker LLM persiste filas.

create table if not exists public.source_module_links (
    id                uuid primary key default gen_random_uuid(),
    learning_path_id  uuid not null references public.learning_paths(id) on delete cascade,
    source_id         uuid not null references public.sources(id) on delete cascade,
    module_id         text not null,  -- id de módulo dentro de la ruta (route["modules"][].id)
    score             real,
    origin            text not null default 'llm' check (origin in ('heuristic', 'llm')),
    created_at        timestamptz not null default now(),
    unique (source_id, module_id)
);
create index if not exists idx_source_module_links_lp on public.source_module_links(learning_path_id);
alter table public.source_module_links enable row level security;
