-- Corrige tres funcoes que retornavam dados sensiveis (presenca, lista de
-- espera e alertas abertos) para qualquer conta autenticada, inclusive
-- pending/nao aprovada, sem checar papel. As demais funcoes do dominio ja
-- usam private.has_any_role(); estas ficaram de fora por descuido.

begin;

create or replace function public.list_attendance_marks(
    p_session_id uuid
)
returns table (
    enrollment_id uuid,
    status public.attendance_status,
    note text
)
language plpgsql
security definer
set search_path = ''
as $$
begin
    if not (
        select private.has_any_role(
            array['coordinator', 'receptionist', 'instructor']::public.user_role[]
        )
    ) then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;
    return query
    select m.enrollment_id, m.status, m.note
      from public.attendance_marks m
     where m.session_id = p_session_id
     order by m.enrollment_id;
end;
$$;

create or replace function public.list_waiting_list(
    p_class_id uuid
)
returns setof public.waiting_list_entries
language plpgsql
security definer
set search_path = ''
as $$
begin
    if not (
        select private.has_any_role(
            array['coordinator', 'receptionist']::public.user_role[]
        )
    ) then
        raise exception using errcode = '42501', message = 'waiting_list_forbidden';
    end if;
    return query
    select *
      from public.waiting_list_entries
     where class_id = p_class_id
     order by position;
end;
$$;

create or replace function public.list_open_attendance_alerts()
returns setof public.attendance_alerts
language plpgsql
security definer
set search_path = ''
as $$
begin
    if not (
        select private.has_any_role(
            array['coordinator', 'receptionist', 'instructor']::public.user_role[]
        )
    ) then
        raise exception using errcode = '42501', message = 'alert_forbidden';
    end if;
    return query
    select * from public.attendance_alerts
     where status = 'aberto'
     order by created_at desc;
end;
$$;

commit;
