-- KB / RAG: tabla de chunks vectoriales (ADR-0006).
-- Store de grounding con citas sobre pgvector (ADR-0001). RLS on sin políticas (ADR-0004).

create extension if not exists vector;

create table if not exists public.kb_chunks (
    id                uuid primary key default gen_random_uuid(),
    source_id         uuid not null references public.sources(id) on delete cascade,
    learning_path_id  uuid not null references public.learning_paths(id) on delete cascade,
    content           text not null,
    embedding         vector(1536),
    metadata          jsonb not null default '{}'::jsonb,
    token_count       integer not null default 0,
    created_at        timestamptz not null default now()
);

create index if not exists kb_chunks_lp_idx
    on public.kb_chunks (learning_path_id);

-- HNSW coseno: embeddings normalizados → distancia coseno (ADR-0006 §4/§5).
create index if not exists kb_chunks_embedding_idx
    on public.kb_chunks using hnsw (embedding vector_cosine_ops);

alter table public.kb_chunks enable row level security;

-- Búsqueda por similitud filtrada por ruta. Se ejecuta con service_role desde el
-- backend; score = 1 - distancia_coseno (mayor = más similar).
create or replace function public.match_kb_chunks(
    query_embedding    vector(1536),
    p_learning_path_id uuid,
    match_count        int default 8,
    verified_only      boolean default false
) returns table (
    id        uuid,
    source_id uuid,
    content   text,
    metadata  jsonb,
    score     float
) language sql stable as $$
    select c.id, c.source_id, c.content, c.metadata,
           1 - (c.embedding <=> query_embedding) as score
    from public.kb_chunks c
    where c.learning_path_id = p_learning_path_id
      and c.embedding is not null
      and (not verified_only
           or coalesce((c.metadata->>'verificada_google')::boolean, false))
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
