-- Agenda institucional: compromissos, horários e comunicação operacional.
-- A agenda é separada do catálogo de turmas para também registrar reuniões,
-- atendimentos, eventos e bloqueios de espaço sem duplicar estudantes.
begin;

create type public.agenda_event_type as enum (
  'turma', 'reuniao', 'atendimento', 'evento', 'bloqueio', 'outro'
);

create type public.agenda_event_status as enum ('agendado', 'cancelado');

create table public.agenda_events (
  id uuid primary key default gen_random_uuid(),
  title text not null check (length(btrim(title)) between 3 and 160),
  description text check (description is null or length(description) <= 4000),
  event_type public.agenda_event_type not null,
  status public.agenda_event_status not null default 'agendado',
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  all_day boolean not null default false,
  location text check (location is null or length(btrim(location)) between 2 and 200),
  class_id uuid references public.classes(id) on delete set null,
  assigned_to uuid references auth.users(id) on delete set null,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint agenda_events_valid_period check (ends_at > starts_at),
  constraint agenda_events_all_day_period check (not all_day or starts_at::date < ends_at::date)
);

create index agenda_events_period_idx on public.agenda_events (starts_at, ends_at)
  where status = 'agendado';
create index agenda_events_assigned_idx on public.agenda_events (assigned_to, starts_at)
  where status = 'agendado';
create index agenda_events_class_idx on public.agenda_events (class_id, starts_at)
  where class_id is not null;

alter table public.agenda_events enable row level security;
revoke all on public.agenda_events from public, anon, authenticated;

create or replace function private.set_agenda_event_updated_at()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create trigger agenda_events_set_updated_at
before update on public.agenda_events
for each row execute function private.set_agenda_event_updated_at();

create or replace function public.list_agenda_events(
  p_starts_at timestamptz,
  p_ends_at timestamptz,
  p_event_type public.agenda_event_type default null,
  p_assigned_to uuid default null
)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare result jsonb;
begin
  if p_ends_at <= p_starts_at then raise exception using errcode = '22023', message = 'invalid_period'; end if;
  if not private.has_any_role(array['coordinator','recepcao','instrutor','consulta']::public.user_role[]) then
    raise exception using errcode = '42501', message = 'forbidden';
  end if;
  select coalesce(jsonb_agg(to_jsonb(item) order by item.starts_at), '[]'::jsonb)
  into result
  from (
    select e.id, e.title, e.description, e.event_type, e.status, e.starts_at,
      e.ends_at, e.all_day, e.location, e.class_id, e.assigned_to,
      e.created_by, e.created_at, e.updated_at
    from public.agenda_events e
    where e.status = 'agendado'
      and e.starts_at < p_ends_at and e.ends_at > p_starts_at
      and (p_event_type is null or e.event_type = p_event_type)
      and (p_assigned_to is null or e.assigned_to = p_assigned_to)
      and (private.has_any_role(array['coordinator','recepcao','consulta']::public.user_role[])
        or e.assigned_to = auth.uid())
  ) item;
  return result;
end;
$$;

create or replace function public.create_agenda_event(
  p_title text, p_description text, p_event_type public.agenda_event_type,
  p_starts_at timestamptz, p_ends_at timestamptz, p_all_day boolean,
  p_location text, p_class_id uuid, p_assigned_to uuid, p_request_id uuid
)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare created public.agenda_events;
begin
  if not private.has_any_role(array['coordinator','recepcao']::public.user_role[]) then
    raise exception using errcode = '42501', message = 'forbidden';
  end if;
  insert into public.agenda_events(title, description, event_type, starts_at, ends_at, all_day, location, class_id, assigned_to, created_by)
  values (btrim(p_title), nullif(btrim(p_description), ''), p_event_type, p_starts_at, p_ends_at, p_all_day, nullif(btrim(p_location), ''), p_class_id, p_assigned_to, auth.uid())
  returning * into created;
  insert into private.audit_entries(actor_id, action, entity_type, entity_id, request_id, metadata)
  values (auth.uid(), 'agenda_event_created', 'agenda_event', created.id, p_request_id, jsonb_build_object('event_type', created.event_type));
  return to_jsonb(created);
end;
$$;

revoke all on function public.list_agenda_events(timestamptz, timestamptz, public.agenda_event_type, uuid) from public, anon;
revoke all on function public.create_agenda_event(text, text, public.agenda_event_type, timestamptz, timestamptz, boolean, text, uuid, uuid, uuid) from public, anon;
grant execute on function public.list_agenda_events(timestamptz, timestamptz, public.agenda_event_type, uuid) to authenticated;
grant execute on function public.create_agenda_event(text, text, public.agenda_event_type, timestamptz, timestamptz, boolean, text, uuid, uuid, uuid) to authenticated;

commit;
