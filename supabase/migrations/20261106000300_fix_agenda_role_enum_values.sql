-- Achado testando o app de ponta a ponta: toda a agenda institucional
-- estava quebrada. As checagens de papel usavam valores em portugues
-- ('recepcao', 'instrutor', 'consulta') que nao existem no enum
-- public.user_role (que e em ingles: coordinator, receptionist,
-- instructor, read_only). list_agenda_events falhava para QUALQUER
-- chamador, inclusive coordenacao, porque o array malformado nao
-- parseia antes mesmo de checar quem esta chamando.

begin;

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
  if not private.has_any_role(array['coordinator','receptionist','instructor','read_only']::public.user_role[]) then
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
      and (private.has_any_role(array['coordinator','receptionist','read_only']::public.user_role[])
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
  if not private.has_any_role(array['coordinator','receptionist']::public.user_role[]) then
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

create or replace function public.update_agenda_event(
  p_event_id uuid, p_expected_updated_at timestamptz, p_title text,
  p_description text, p_event_type public.agenda_event_type,
  p_starts_at timestamptz, p_ends_at timestamptz, p_all_day boolean,
  p_location text, p_class_id uuid, p_assigned_to uuid, p_request_id uuid
)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare updated public.agenda_events;
begin
  if not private.has_any_role(array['coordinator','receptionist']::public.user_role[]) then
    raise exception using errcode = '42501', message = 'forbidden';
  end if;
  update public.agenda_events
  set title = btrim(p_title), description = nullif(btrim(p_description), ''),
      event_type = p_event_type, starts_at = p_starts_at, ends_at = p_ends_at,
      all_day = p_all_day, location = nullif(btrim(p_location), ''),
      class_id = p_class_id, assigned_to = p_assigned_to
  where id = p_event_id and status = 'agendado' and updated_at = p_expected_updated_at
  returning * into updated;
  if updated.id is null then
    if exists (select 1 from public.agenda_events where id = p_event_id) then
      raise exception using errcode = 'P0001', message = 'agenda_event_version_conflict';
    end if;
    raise exception using errcode = 'P0001', message = 'agenda_event_not_found';
  end if;
  insert into private.audit_entries(actor_id, action, entity_type, entity_id, request_id)
  values (auth.uid(), 'agenda_event_updated', 'agenda_event', updated.id, p_request_id);
  return to_jsonb(updated);
end;
$$;

create or replace function public.cancel_agenda_event(
  p_event_id uuid, p_expected_updated_at timestamptz, p_reason text, p_request_id uuid
)
returns jsonb
language plpgsql security definer set search_path = '' as $$
declare updated public.agenda_events;
begin
  if not private.has_any_role(array['coordinator','receptionist']::public.user_role[]) then
    raise exception using errcode = '42501', message = 'forbidden';
  end if;
  if length(btrim(p_reason)) < 10 then
    raise exception using errcode = '22023', message = 'invalid_cancellation_reason';
  end if;
  update public.agenda_events set status = 'cancelado'
  where id = p_event_id and status = 'agendado' and updated_at = p_expected_updated_at
  returning * into updated;
  if updated.id is null then
    if exists (select 1 from public.agenda_events where id = p_event_id) then
      raise exception using errcode = 'P0001', message = 'agenda_event_version_conflict';
    end if;
    raise exception using errcode = 'P0001', message = 'agenda_event_not_found';
  end if;
  insert into private.audit_entries(actor_id, action, entity_type, entity_id, request_id, metadata)
  values (auth.uid(), 'agenda_event_cancelled', 'agenda_event', updated.id, p_request_id, jsonb_build_object('reason', p_reason));
  return to_jsonb(updated);
end;
$$;

commit;
