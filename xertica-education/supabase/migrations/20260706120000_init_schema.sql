-- ADR-0005: Spine completo desde el día 1 (+ ADR-0004 persistencia).
-- Jerarquía del dominio (el "spine" del doc de arquitectura §3):
--   Ruta → Módulo → Componente → Asset → { Source, AssetVersion }
-- Enums como TEXT + CHECK con el vocabulario del documento objetivo.
-- RLS activo SIN políticas en todas: el backend (service_role) bypassa RLS;
-- anon/frontend no accede directamente (patrón API-gateway).

-- ── learning_paths (Ruta) ─────────────────────────────────────────────
-- estado INTERINO: vocab de aprobación que usan hoy el route service y el
-- frontend (ContentStatus). Migra a ciclo de vida (borrador/en_produccion/
-- publicada) en un slice posterior que desacople RouteStatus (ADR-0005).
create table if not exists public.learning_paths (
    id           uuid primary key default gen_random_uuid(),
    titulo       text not null,
    tema         text not null,
    storytelling text,
    industria    text,
    estado       text not null default 'borrador'
                 check (estado in ('borrador', 'generado', 'en-revision', 'aprobado')),
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);

-- ── modules (Módulo) ──────────────────────────────────────────────────
create table if not exists public.modules (
    id                    uuid primary key default gen_random_uuid(),
    learning_path_id      uuid not null references public.learning_paths(id) on delete cascade,
    titulo                text not null,
    descripcion           text,
    tipo                  text not null
                          check (tipo in ('intro', 'capsula', 'lab', 'evaluacion', 'cierre')),
    orden                 integer not null default 0,
    duracion_objetivo_min integer,
    created_at            timestamptz not null default now(),
    updated_at            timestamptz not null default now()
);
create index if not exists idx_modules_learning_path on public.modules(learning_path_id);

-- ── components (Componente) ───────────────────────────────────────────
create table if not exists public.components (
    id         uuid primary key default gen_random_uuid(),
    modulo_id  uuid not null references public.modules(id) on delete cascade,
    titulo     text not null,
    tema       text,
    tipo       text not null
               check (tipo in ('lesson', 'video', 'lab', 'infografia', 'quiz')),
    orden      integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists idx_components_modulo on public.components(modulo_id);

-- ── assets (Asset) ────────────────────────────────────────────────────
-- estado = APROBACIÓN (distinto del estado de la Ruta). Guion bajo en
-- en_revision, alineado con el modelo Asset y el doc §3.
create table if not exists public.assets (
    id            uuid primary key default gen_random_uuid(),
    componente_id uuid not null references public.components(id) on delete cascade,
    tipo          text not null
                  check (tipo in ('lesson', 'video', 'lab', 'infografia', 'quiz')),
    estado        text not null default 'draft'
                  check (estado in ('draft', 'generado', 'en_revision', 'aprobado')),
    storage_path  text,
    word_budget   integer,
    provenance    jsonb,
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);
create index if not exists idx_assets_componente on public.assets(componente_id);

-- ── sources (Source) ──────────────────────────────────────────────────
create table if not exists public.sources (
    id                uuid primary key default gen_random_uuid(),
    asset_id          uuid not null references public.assets(id) on delete cascade,
    url               text not null,
    title             text,
    tipo              text
                      check (tipo in ('youtube', 'google_docs', 'blog_oficial', 'soporte_google')),
    verificada_google boolean not null default false,
    created_at        timestamptz not null default now()
);
create index if not exists idx_sources_asset on public.sources(asset_id);

-- ── asset_versions (AssetVersion) ─────────────────────────────────────
create table if not exists public.asset_versions (
    id         uuid primary key default gen_random_uuid(),
    asset_id   uuid not null references public.assets(id) on delete cascade,
    version    integer not null,
    created_at timestamptz not null default now(),
    unique (asset_id, version)
);
create index if not exists idx_asset_versions_asset on public.asset_versions(asset_id);

-- ── jobs (infra de orquestación · fuera del Spine) ────────────────────
create table if not exists public.jobs (
    id         uuid primary key default gen_random_uuid(),
    type       text not null,
    status     text not null default 'queued'
               check (status in ('queued', 'running', 'rendering', 'completed', 'failed')),
    progress   integer not null default 0 check (progress between 0 and 100),
    result     jsonb,
    error      text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ── RLS: activo, sin políticas públicas ───────────────────────────────
alter table public.learning_paths enable row level security;
alter table public.modules        enable row level security;
alter table public.components     enable row level security;
alter table public.assets         enable row level security;
alter table public.sources        enable row level security;
alter table public.asset_versions enable row level security;
alter table public.jobs           enable row level security;
