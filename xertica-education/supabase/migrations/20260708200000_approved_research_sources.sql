create table if not exists public.approved_research_sources (
  id uuid primary key default gen_random_uuid(),
  route_id uuid not null references public.learning_paths(id) on delete cascade,
  module_id text,
  tool_name text,
  title text not null,
  url text not null,
  domain text not null,
  source_type text not null default 'documentation',
  is_verified boolean not null default false,
  approval_source text not null check (approval_source in ('automatic', 'manual')),
  approved_by uuid,
  approved_at timestamptz not null default now(),
  status text not null default 'approved' check (status in ('approved', 'rejected')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique nulls not distinct (route_id, module_id, url)
);

create index if not exists idx_approved_research_sources_route
  on public.approved_research_sources(route_id, module_id);

alter table public.approved_research_sources enable row level security;
