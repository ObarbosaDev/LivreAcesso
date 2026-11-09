-- Historico de chamada (leitura por turma), resumo mensal e arquivamento
-- automatico: sessoes fechadas com mais de 6 meses viram um resumo agregado
-- por matricula/mes e os registros detalhados (marcas + sessao) sao apagados.

begin;

create table public.attendance_monthly_summaries (
    id uuid primary key default gen_random_uuid(),
    class_id uuid not null references public.classes(id),
    enrollment_id uuid not null references public.enrollments(id),
    period date not null,
    total_sessions integer not null default 0,
    present_count integer not null default 0,
    absent_count integer not null default 0,
    justified_count integer not null default 0,
    created_at timestamptz not null default timezone('utc', now()),
    unique (enrollment_id, period)
);

create index attendance_monthly_summaries_class_period_idx
    on public.attendance_monthly_summaries (class_id, period desc);

alter table public.attendance_monthly_summaries enable row level security;
revoke all on public.attendance_monthly_summaries from public, anon, authenticated;

create or replace function public.list_attendance_sessions(
    p_class_id uuid, p_limit integer default 60, p_offset integer default 0
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_items jsonb;
    v_total integer;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role]) then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;
    if p_limit not between 1 and 100 or p_offset < 0 then
        raise exception using errcode = '22023', message = 'invalid_pagination';
    end if;
    if private.has_any_role(array['instructor'::public.user_role]) and not exists (
        select 1 from public.class_instructors ci
         where ci.class_id = p_class_id and ci.instructor_id = auth.uid()
    ) then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;

    select count(*) into v_total from public.attendance_sessions s where s.class_id = p_class_id;
    select coalesce(jsonb_agg(to_jsonb(rows) order by rows.session_date desc), '[]'::jsonb) into v_items
      from (
          select s.id, s.class_id, s.session_date, s.status, s.closed_at
            from public.attendance_sessions s
           where s.class_id = p_class_id
           order by s.session_date desc
           limit p_limit offset p_offset
      ) rows;

    return jsonb_build_object('items', v_items, 'total', v_total);
end;
$$;

create or replace function public.list_attendance_summary(p_class_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_items jsonb;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'instructor'::public.user_role]) then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;
    if private.has_any_role(array['instructor'::public.user_role]) and not exists (
        select 1 from public.class_instructors ci
         where ci.class_id = p_class_id and ci.instructor_id = auth.uid()
    ) then
        raise exception using errcode = '42501', message = 'attendance_forbidden';
    end if;

    select coalesce(jsonb_agg(to_jsonb(rows) order by rows.period desc, rows.enrollment_id), '[]'::jsonb) into v_items
      from (
          select enrollment_id, period, total_sessions, present_count, absent_count, justified_count
            from public.attendance_monthly_summaries
           where class_id = p_class_id
      ) rows;

    return jsonb_build_object('items', v_items);
end;
$$;

-- Interna: so o service_role (job agendado do backend) pode chamar.
create or replace function public.archive_old_attendance_sessions()
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_cutoff date := (current_date - interval '6 months')::date;
    v_archived integer;
begin
    with to_archive as (
        -- Chamadas editaveis (status 'aberta') tambem entram: o corte de 6 meses
        -- e quem decide se a chamada ainda pode ser editada, nao um "fechar" explicito.
        select s.class_id, m.enrollment_id,
               date_trunc('month', s.session_date)::date as period,
               m.status
          from public.attendance_sessions s
          join public.attendance_marks m on m.session_id = s.id
         where s.session_date < v_cutoff
    ),
    aggregated as (
        select class_id, enrollment_id, period,
               count(*) as total_sessions,
               count(*) filter (where status = 'presente') as present_count,
               count(*) filter (where status = 'ausente') as absent_count,
               count(*) filter (where status = 'justificada') as justified_count
          from to_archive
         group by class_id, enrollment_id, period
    ),
    upserted as (
        insert into public.attendance_monthly_summaries
            (class_id, enrollment_id, period, total_sessions, present_count, absent_count, justified_count)
        select class_id, enrollment_id, period, total_sessions, present_count, absent_count, justified_count
          from aggregated
        on conflict (enrollment_id, period) do update
        set total_sessions = public.attendance_monthly_summaries.total_sessions + excluded.total_sessions,
            present_count = public.attendance_monthly_summaries.present_count + excluded.present_count,
            absent_count = public.attendance_monthly_summaries.absent_count + excluded.absent_count,
            justified_count = public.attendance_monthly_summaries.justified_count + excluded.justified_count
        returning 1
    )
    select count(*) into v_archived from upserted;

    -- Sessoes vazias (nunca preenchidas) tambem nao devem se acumular para sempre.
    delete from public.attendance_sessions s
     where s.session_date < v_cutoff
       and not exists (select 1 from public.attendance_marks m where m.session_id = s.id);

    delete from public.attendance_sessions s
     where s.session_date < v_cutoff;

    return coalesce(v_archived, 0);
end;
$$;

revoke all on function public.list_attendance_sessions(uuid, integer, integer) from public, anon;
grant execute on function public.list_attendance_sessions(uuid, integer, integer) to authenticated;
revoke all on function public.list_attendance_summary(uuid) from public, anon;
grant execute on function public.list_attendance_summary(uuid) to authenticated;
revoke all on function public.archive_old_attendance_sessions() from public, anon, authenticated;
grant execute on function public.archive_old_attendance_sessions() to service_role;

commit;
