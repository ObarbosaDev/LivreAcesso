-- BL-07: alertas e resumo de frequência consumíveis pela API.

begin;

create or replace function public.list_open_attendance_alerts()
returns setof public.attendance_alerts
language sql
security definer
set search_path = ''
as $$
    select * from public.attendance_alerts
     where status = 'aberto'
     order by created_at desc;
$$;

create or replace function public.upsert_attendance_alert(
    p_student_id uuid,
    p_class_id uuid,
    p_alert_type text,
    p_title text,
    p_detail text,
    p_threshold integer
)
returns public.attendance_alerts
language plpgsql
security definer
set search_path = ''
as $$
declare
    created_alert public.attendance_alerts;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role])) then
        raise exception using errcode = '42501', message = 'alert_forbidden';
    end if;
    insert into public.attendance_alerts (student_id, class_id, alert_type, title, detail, threshold)
    values (p_student_id, p_class_id, p_alert_type, p_title, p_detail, p_threshold)
    on conflict (student_id, class_id, alert_type, status) do update
        set detail = excluded.detail
    returning * into created_alert;
    return created_alert;
end;
$$;

revoke all on function public.list_open_attendance_alerts() from public, anon;
revoke all on function public.upsert_attendance_alert(uuid, uuid, text, text, text, integer) from public, anon;
grant execute on function public.list_open_attendance_alerts() to authenticated;
grant execute on function public.upsert_attendance_alert(uuid, uuid, text, text, text, integer) to authenticated;

commit;
