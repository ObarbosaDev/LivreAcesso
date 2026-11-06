-- Achado do ultrareview sobre a 20261106000100: list_attendance_marks e
-- list_open_attendance_alerts checavam o papel "instructor" mas nao
-- restringiam a turma, ao contrario de list_enrollments/get_enrollment/
-- get_class_enrollment_occupancy, que ja escopam por class_instructors.
-- Um instrutor da turma A conseguia ler presenca e alertas de qualquer
-- outra turma.

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
    if private.has_any_role(array['instructor']::public.user_role[])
       and not exists (
           select 1
             from public.attendance_sessions s
             join public.class_instructors ci on ci.class_id = s.class_id
            where s.id = p_session_id
              and ci.instructor_id = auth.uid()
       )
    then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;
    return query
    select m.enrollment_id, m.status, m.note
      from public.attendance_marks m
     where m.session_id = p_session_id
     order by m.enrollment_id;
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
    if private.has_any_role(array['instructor']::public.user_role[]) then
        return query
        select a.*
          from public.attendance_alerts a
         where a.status = 'aberto'
           and a.class_id is not null
           and exists (
               select 1
                 from public.class_instructors ci
                where ci.class_id = a.class_id
                  and ci.instructor_id = auth.uid()
           )
         order by a.created_at desc;
    else
        return query
        select *
          from public.attendance_alerts
         where status = 'aberto'
         order by created_at desc;
    end if;
end;
$$;

commit;
