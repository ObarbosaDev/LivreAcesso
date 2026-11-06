-- create_agenda_event e cancel_agenda_event inseriam em private.audit_entries
-- usando uma coluna "metadata" que a tabela nunca teve (só tem changed_fields
-- text[], de propósito, pra nunca guardar o valor alterado, só o nome do
-- campo). Isso quebrava o insert com "column metadata does not exist" e
-- desfazia a transação inteira: todo compromisso de agenda criado ou
-- cancelado falhava, sempre, em qualquer ambiente, desde que a agenda foi
-- escrita.

begin;

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
  insert into private.audit_entries(actor_id, action, entity_type, entity_id, changed_fields, request_id)
  values (auth.uid(), 'agenda_event_created', 'agenda_event', created.id, array['event_type'], p_request_id);
  return to_jsonb(created);
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
  insert into private.audit_entries(actor_id, action, entity_type, entity_id, changed_fields, request_id)
  values (auth.uid(), 'agenda_event_cancelled', 'agenda_event', updated.id, array['status'], p_request_id);
  return to_jsonb(updated);
end;
$$;

commit;
