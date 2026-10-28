-- BL-06/07/08: consultas operacionais, correção auditada e resolução de estados.

begin;

create or replace function public.list_attendance_marks(
    p_session_id uuid
)
returns table (
    enrollment_id uuid,
    status public.attendance_status,
    note text
)
language sql
security definer
set search_path = ''
as $$
    select m.enrollment_id, m.status, m.note
      from public.attendance_marks m
     where m.session_id = p_session_id
     order by m.enrollment_id;
$$;

create or replace function public.list_waiting_list(
    p_class_id uuid
)
returns setof public.waiting_list_entries
language sql
security definer
set search_path = ''
as $$
    select *
      from public.waiting_list_entries
     where class_id = p_class_id
     order by position;
$$;

create or replace function public.withdraw_waiting_list_entry(p_entry_id uuid)
returns public.waiting_list_entries
language plpgsql
security definer
set search_path = ''
as $$
declare
    withdrawn_entry public.waiting_list_entries;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role])) then
        raise exception using errcode = '42501', message = 'waiting_list_forbidden';
    end if;
    update public.waiting_list_entries
       set status = 'retirada', decided_at = timezone('utc', now())
     where id = p_entry_id
       and status in ('aguardando', 'vaga_ofertada')
    returning * into withdrawn_entry;
    if not found then
        raise exception using errcode = '55000', message = 'waiting_list_not_active';
    end if;
    return withdrawn_entry;
end;
$$;

create or replace function public.resolve_attendance_alert(p_alert_id uuid)
returns public.attendance_alerts
language plpgsql
security definer
set search_path = ''
as $$
declare
    resolved_alert public.attendance_alerts;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role])) then
        raise exception using errcode = '42501', message = 'alert_forbidden';
    end if;
    update public.attendance_alerts
       set status = 'resolvido', resolved_at = timezone('utc', now())
     where id = p_alert_id and status = 'aberto'
    returning * into resolved_alert;
    if not found then
        raise exception using errcode = '55000', message = 'alert_not_open';
    end if;
    return resolved_alert;
end;
$$;

revoke all on function public.list_attendance_marks(uuid) from public, anon;
revoke all on function public.list_waiting_list(uuid) from public, anon;
revoke all on function public.withdraw_waiting_list_entry(uuid) from public, anon;
revoke all on function public.resolve_attendance_alert(uuid) from public, anon;
grant execute on function public.list_attendance_marks(uuid) to authenticated;
grant execute on function public.list_waiting_list(uuid) to authenticated;
grant execute on function public.withdraw_waiting_list_entry(uuid) to authenticated;
grant execute on function public.resolve_attendance_alert(uuid) to authenticated;

commit;
