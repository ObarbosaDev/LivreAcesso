-- BL-08: operações auditáveis da fila de espera.
-- A oferta e a aceitação são passos separados para preservar decisão humana.

begin;

create or replace function public.join_waiting_list(
    p_student_id uuid,
    p_class_id uuid
)
returns public.waiting_list_entries
language plpgsql
security definer
set search_path = ''
as $$
declare
    created_entry public.waiting_list_entries;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role])) then
        raise exception using errcode = '42501', message = 'waiting_list_forbidden';
    end if;
    insert into public.waiting_list_entries (student_id, class_id, position)
    select p_student_id, p_class_id,
           coalesce(max(position), 0) + 1
      from public.waiting_list_entries
     where class_id = p_class_id
       and status in ('aguardando', 'vaga_ofertada')
    returning * into created_entry;
    return created_entry;
exception
    when unique_violation then
        raise exception using errcode = '23505', message = 'waiting_list_duplicate';
end;
$$;

create or replace function public.offer_waiting_list_entry(p_entry_id uuid)
returns public.waiting_list_entries
language plpgsql
security definer
set search_path = ''
as $$
declare
    offered_entry public.waiting_list_entries;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role])) then
        raise exception using errcode = '42501', message = 'waiting_list_forbidden';
    end if;
    update public.waiting_list_entries
       set status = 'vaga_ofertada', offered_at = timezone('utc', now())
     where id = p_entry_id and status = 'aguardando'
    returning * into offered_entry;
    if not found then
        raise exception using errcode = '55000', message = 'waiting_list_not_waiting';
    end if;
    return offered_entry;
end;
$$;

create or replace function public.accept_waiting_list_entry(p_entry_id uuid)
returns public.waiting_list_entries
language plpgsql
security definer
set search_path = ''
as $$
declare
    accepted_entry public.waiting_list_entries;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role])) then
        raise exception using errcode = '42501', message = 'waiting_list_forbidden';
    end if;
    update public.waiting_list_entries
       set status = 'aceita', decided_at = timezone('utc', now())
     where id = p_entry_id and status = 'vaga_ofertada'
    returning * into accepted_entry;
    if not found then
        raise exception using errcode = '55000', message = 'waiting_list_not_offered';
    end if;
    return accepted_entry;
end;
$$;

revoke all on function public.join_waiting_list(uuid, uuid) from public, anon;
revoke all on function public.offer_waiting_list_entry(uuid) from public, anon;
revoke all on function public.accept_waiting_list_entry(uuid) from public, anon;
grant execute on function public.join_waiting_list(uuid, uuid) to authenticated;
grant execute on function public.offer_waiting_list_entry(uuid) to authenticated;
grant execute on function public.accept_waiting_list_entry(uuid) to authenticated;

commit;
