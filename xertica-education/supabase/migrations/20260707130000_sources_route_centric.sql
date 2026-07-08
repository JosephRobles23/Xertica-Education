-- issue-09 / ADR-0007: sources route-céntrica + puente asset_sources (M:N).
-- Corrige el modelo asset-céntrico de ADR-0005. La tabla sources está vacía → seguro.

-- 1) sources: route-céntrica + estado; se elimina asset_id.
alter table public.sources
    add column if not exists learning_path_id uuid
    references public.learning_paths(id) on delete cascade;

alter table public.sources
    add column if not exists estado text
    check (estado in ('approved', 'requires-review', 'rejected'));

drop index if exists public.idx_sources_asset;
alter table public.sources drop column if exists asset_id;

-- learning_path_id es obligatorio (route-céntrico) una vez migrada la columna.
alter table public.sources alter column learning_path_id set not null;

create index if not exists idx_sources_lp on public.sources(learning_path_id);

-- Idempotencia del sourcing: una URL por ruta (clave del UPSERT · ADR-0007 §4).
create unique index if not exists uq_sources_lp_url
    on public.sources(learning_path_id, url);

-- 2) asset_sources: puente M:N assets <-> sources (citación, Fase 5-6).
create table if not exists public.asset_sources (
    asset_id  uuid not null references public.assets(id)  on delete cascade,
    source_id uuid not null references public.sources(id) on delete cascade,
    primary key (asset_id, source_id)
);
alter table public.asset_sources enable row level security;
