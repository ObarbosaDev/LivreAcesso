-- Gestão segura de compromissos: edição e cancelamento com versão esperada.
begin;

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
  if not private.has_any_role(array['coordinator','recepcao']::public.user_role[]) then
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
  if not private.has_any_role(array['coordinator','recepcao']::public.user_role[]) then
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

revoke all on function public.update_agenda_event(uuid, timestamptz, text, text, public.agenda_event_type, timestamptz, timestamptz, boolean, text, uuid, uuid, uuid) from public, anon;
revoke all on function public.cancel_agenda_event(uuid, timestamptz, text, uuid) from public, anon;
grant execute on function public.update_agenda_event(uuid, timestamptz, text, text, public.agenda_event_type, timestamptz, timestamptz, boolean, text, uuid, uuid, uuid) to authenticated;
grant execute on function public.cancel_agenda_event(uuid, timestamptz, text, uuid) to authenticated;

commit;
