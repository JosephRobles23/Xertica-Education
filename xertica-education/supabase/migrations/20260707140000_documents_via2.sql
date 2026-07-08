-- ADR-0008: documentos del usuario (Vía 2) + sources con origin/document_id.

create table if not exists public.documents (
    id                uuid primary key default gen_random_uuid(),
    learning_path_id  uuid not null references public.learning_paths(id) on delete cascade,
    storage_path      text not null,
    filename          text not null,
    mime              text,
    use_as_source     boolean not null default false,
    created_at        timestamptz not null default now()
);
create index if not exists idx_documents_lp on public.documents(learning_path_id);
alter table public.documents enable row level security;

-- sources: origen (Vía 1 url / Vía 2 upload) + enlace al documento.
alter table public.sources
    add column if not exists origin text not null default 'deep_research'
    check (origin in ('deep_research', 'upload'));
alter table public.sources
    add column if not exists document_id uuid references public.documents(id) on delete cascade;
-- los uploads no tienen url.
alter table public.sources alter column url drop not null;
-- idempotencia de uploads (los NULL múltiples no colisionan en Postgres).
create unique index if not exists uq_sources_lp_document
    on public.sources(learning_path_id, document_id);
