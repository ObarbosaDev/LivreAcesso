-- BL-06: sessões de aula e marcas de frequência.
-- A frequência referencia matrícula, não o cadastro do estudante diretamente.
-- Assim o histórico permanece correto por turma e modalidade.

begin;

create type public.attendance_session_status as enum ('aberta', 'fechada');
create type public.attendance_status as enum ('presente', 'ausente', 'justificada');

create table public.attendance_sessions (
    id uuid primary key default gen_random_uuid(),
    class_id uuid not null references public.classes(id),
    session_date date not null,
    status public.attendance_session_status not null default 'aberta',
    closed_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    unique (class_id, session_date),
    check ((status = 'aberta' and closed_at is null) or (status = 'fechada' and closed_at is not null))
);

create table public.attendance_marks (
    id uuid primary key default gen_random_uuid(),
    session_id uuid not null references public.attendance_sessions(id) on delete cascade,
    enrollment_id uuid not null references public.enrollments(id),
    status public.attendance_status not null,
    note text,
    created_at timestamptz not null default timezone('utc', now()),
    unique (session_id, enrollment_id),
    check (status <> 'justificada' or nullif(btrim(note), '') is not null),
    check (note is null or char_length(note) <= 500)
);

create index attendance_sessions_class_date_idx
    on public.attendance_sessions (class_id, session_date desc);
create index attendance_marks_enrollment_idx
    on public.attendance_marks (enrollment_id, created_at desc);

alter table public.attendance_sessions enable row level security;
alter table public.attendance_marks enable row level security;

revoke all on public.attendance_sessions from public, anon, authenticated;
revoke all on public.attendance_marks from public, anon, authenticated;

create or replace function public.open_attendance_session(
    p_class_id uuid,
    p_session_date date
)
returns public.attendance_sessions
language plpgsql
security definer
set search_path = ''
as $$
declare
    created_session public.attendance_sessions;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role])) then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;

    insert into public.attendance_sessions (class_id, session_date)
    values (p_class_id, p_session_date)
    returning * into created_session;

    return created_session;
exception
    when unique_violation then
        raise exception using errcode = '23505', message = 'attendance_session_exists';
end;
$$;

create or replace function public.record_attendance(
    p_session_id uuid,
    p_marks jsonb
)
returns public.attendance_sessions
language plpgsql
security definer
set search_path = ''
as $$
declare
    current_session public.attendance_sessions;
    mark jsonb;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role])) then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;

    select *
      into current_session
      from public.attendance_sessions
     where id = p_session_id
     for update;

    if not found then
        raise exception using errcode = 'P0002', message = 'attendance_session_not_found';
    end if;
    if current_session.status = 'fechada' then
        raise exception using errcode = '55000', message = 'attendance_already_closed';
    end if;
    if jsonb_typeof(p_marks) <> 'array' or jsonb_array_length(p_marks) = 0 then
        raise exception using errcode = '22023', message = 'attendance_marks_required';
    end if;

    for mark in select value from jsonb_array_elements(p_marks)
    loop
        insert into public.attendance_marks (session_id, enrollment_id, status, note)
        values (
            p_session_id,
            (mark->>'enrollment_id')::uuid,
            (mark->>'status')::public.attendance_status,
            nullif(btrim(mark->>'note'), '')
        )
        on conflict (session_id, enrollment_id) do update
        set status = excluded.status, note = excluded.note;
    end loop;

    return current_session;
end;
$$;

create or replace function public.close_attendance_session(
    p_session_id uuid
)
returns public.attendance_sessions
language plpgsql
security definer
set search_path = ''
as $$
declare
    closed_session public.attendance_sessions;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role])) then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;

    update public.attendance_sessions
       set status = 'fechada', closed_at = timezone('utc', now())
     where id = p_session_id
       and status = 'aberta'
       and exists (
           select 1 from public.attendance_marks
            where session_id = p_session_id
       )
    returning * into closed_session;

    if not found then
        raise exception using errcode = '55000', message = 'attendance_cannot_close';
    end if;
    return closed_session;
end;
$$;

revoke all on function public.open_attendance_session(uuid, date) from public, anon;
revoke all on function public.record_attendance(uuid, jsonb) from public, anon;
revoke all on function public.close_attendance_session(uuid) from public, anon;
grant execute on function public.open_attendance_session(uuid, date) to authenticated;
grant execute on function public.record_attendance(uuid, jsonb) to authenticated;
grant execute on function public.close_attendance_session(uuid) to authenticated;

commit;
