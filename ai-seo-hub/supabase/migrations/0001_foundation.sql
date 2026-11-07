-- AI SEO HUB — Phase 1 foundation: projects, API usage metering, activity log.
-- All tables are protected by Row Level Security; data is isolated per owner.

create extension if not exists pgcrypto;

-- Generic updated_at trigger ------------------------------------------------
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- Projects --------------------------------------------------------------------
create table public.projects (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references auth.users(id) on delete cascade default auth.uid(),
  name          text not null check (char_length(name) between 1 and 120),
  url           text not null check (url ~* '^https?://'),
  description   text not null default '' check (char_length(description) <= 2000),
  category      text not null default 'other'
                check (category in ('saas','ecommerce','services','content','local','other')),
  market        text not null default '' check (char_length(market) <= 200),
  languages     text[] not null default '{}' check (cardinality(languages) <= 20),
  countries     text[] not null default '{}' check (cardinality(countries) <= 50),
  -- Cost control: hard monthly ceiling for paid AI/API calls, in EUR.
  monthly_budget_eur numeric(10,2) not null default 10 check (monthly_budget_eur >= 0),
  status        text not null default 'active' check (status in ('active','paused','archived')),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (owner_id, url)
);
create index projects_owner_idx on public.projects(owner_id);
create trigger projects_updated_at before update on public.projects
  for each row execute function public.set_updated_at();

-- Ownership helper used by every project-scoped table's policies.
-- SECURITY DEFINER so policies don't recurse through projects' own RLS.
create or replace function public.owns_project(p_project_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.projects
    where id = p_project_id and owner_id = auth.uid()
  );
$$;
revoke all on function public.owns_project(uuid) from public;
grant execute on function public.owns_project(uuid) to authenticated;

alter table public.projects enable row level security;
create policy projects_select on public.projects for select to authenticated
  using (owner_id = auth.uid());
create policy projects_insert on public.projects for insert to authenticated
  with check (owner_id = auth.uid());
create policy projects_update on public.projects for update to authenticated
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy projects_delete on public.projects for delete to authenticated
  using (owner_id = auth.uid());

-- API usage metering (AI tokens, DataForSEO, etc.) ----------------------------
-- Written by server-side code only; users can read, never write.
create table public.api_usage (
  id          bigint generated always as identity primary key,
  project_id  uuid not null references public.projects(id) on delete cascade,
  provider    text not null,              -- 'anthropic' | 'openai' | 'dataforseo' | 'pagespeed' ...
  operation   text not null,              -- 'content.generate', 'keywords.research' ...
  units       numeric not null default 0, -- tokens, requests, tasks
  cost_eur    numeric(12,6) not null default 0 check (cost_eur >= 0),
  is_estimate boolean not null default true,
  created_at  timestamptz not null default now()
);
create index api_usage_project_month_idx on public.api_usage(project_id, created_at desc);

alter table public.api_usage enable row level security;
create policy api_usage_select on public.api_usage for select to authenticated
  using (public.owns_project(project_id));
-- no insert/update/delete policy for 'authenticated': only service role (server) writes.

create or replace function public.month_spend_eur(p_project_id uuid)
returns numeric language sql stable security invoker set search_path = public as $$
  select coalesce(sum(cost_eur), 0) from public.api_usage
  where project_id = p_project_id
    and created_at >= date_trunc('month', now());
$$;

-- Activity log (audit trail of approvals/rejections and system events) --------
create table public.activity_log (
  id          bigint generated always as identity primary key,
  project_id  uuid not null references public.projects(id) on delete cascade,
  actor_id    uuid references auth.users(id) on delete set null default auth.uid(),
  action      text not null,
  details     jsonb not null default '{}',
  created_at  timestamptz not null default now()
);
create index activity_log_project_idx on public.activity_log(project_id, created_at desc);

alter table public.activity_log enable row level security;
create policy activity_select on public.activity_log for select to authenticated
  using (public.owns_project(project_id));
create policy activity_insert on public.activity_log for insert to authenticated
  with check (public.owns_project(project_id) and actor_id = auth.uid());
