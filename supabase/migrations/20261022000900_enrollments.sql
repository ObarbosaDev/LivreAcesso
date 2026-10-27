-- BL-05: matrículas, capacidade e histórico de status.
begin;

create table public.enrollments (
    id uuid primary key,
    student_id uuid not null references public.students (id) on delete restrict,
    class_id uuid not null references public.classes (id) on delete restrict,
    status text not null default 'ativa',
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    constraint enrollments_status_check check (status in ('ativa', 'cancelada'))
);

create unique index enrollments_one_active_per_student_class
    on public.enrollments (student_id, class_id)
    where status = 'ativa';
create index enrollments_class_status_idx on public.enrollments (class_id, status);
create index enrollments_student_status_idx on public.enrollments (student_id, status);

create table private.enrollment_status_history (
    id bigint generated always as identity primary key,
    enrollment_id uuid not null references public.enrollments (id) on delete restrict,
    previous_status text,
    current_status text not null,
    reason text not null,
    changed_by uuid not null references auth.users (id) on delete restrict,
    request_id uuid not null,
    occurred_at timestamptz not null default timezone('utc', now())
);

create or replace function private.enrollments_set_updated_at()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
    new.updated_at := timezone('utc', now());
    return new;
end;
$$;

create trigger enrollments_set_updated_at
before update on public.enrollments
for each row execute function private.enrollments_set_updated_at();

alter table public.enrollments enable row level security;
revoke all on table public.enrollments from public, anon, authenticated;
revoke all on all tables in schema private from public, anon, authenticated;
revoke all on table private.enrollment_status_history from public, anon, authenticated;
revoke all on function private.enrollments_set_updated_at() from public, anon, authenticated;

create or replace function public.register_enrollment(
    p_enrollment_id uuid,
    p_student_id uuid,
    p_class_id uuid,
    p_request_id uuid
)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
    v_capacity integer;
    v_active_count integer;
    v_student_active boolean;
    v_row public.enrollments;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    select active into v_student_active from public.students where id = p_student_id;
    if coalesce(not v_student_active, true) then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    select capacity into v_capacity from public.classes where id = p_class_id and active;
    if v_capacity is null then
        raise exception using errcode = 'P0002', message = 'class_not_found';
    end if;
    if exists (select 1 from public.enrollments where student_id = p_student_id and class_id = p_class_id and status = 'ativa') then
        raise exception using errcode = '23505', message = 'duplicate_enrollment';
    end if;
    select count(*) into v_active_count from public.enrollments where class_id = p_class_id and status = 'ativa';
    if v_active_count >= v_capacity then
        raise exception using errcode = 'P0001', message = 'class_capacity_reached';
    end if;
    insert into public.enrollments (id, student_id, class_id) values (p_enrollment_id, p_student_id, p_class_id)
    returning * into v_row;
    return jsonb_build_object('id', v_row.id, 'student_id', v_row.student_id, 'class_id', v_row.class_id, 'status', v_row.status, 'created_at', v_row.created_at, 'updated_at', v_row.updated_at);
end;
$$;

create or replace function public.get_enrollment(p_enrollment_id uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_row public.enrollments;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'read_only'::public.user_role, 'instructor'::public.user_role]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    select * into v_row from public.enrollments where id = p_enrollment_id;
    if not found then raise exception using errcode = 'P0002', message = 'enrollment_not_found'; end if;
    return to_jsonb(v_row);
end;
$$;

create or replace function public.change_enrollment_status(
    p_enrollment_id uuid,
    p_target_status text,
    p_expected_updated_at timestamptz,
    p_reason text,
    p_request_id uuid
)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_row public.enrollments; v_previous text;
begin
    if not private.has_any_role(array['coordinator'::public.user_role]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if char_length(btrim(p_reason)) not between 10 and 500 then raise exception using errcode = '22023', message = 'invalid_reason'; end if;
    select * into v_row from public.enrollments where id = p_enrollment_id for update;
    if not found then raise exception using errcode = 'P0002', message = 'enrollment_not_found'; end if;
    if v_row.updated_at <> p_expected_updated_at then raise exception using errcode = '40001', message = 'enrollment_version_conflict'; end if;
    v_previous := v_row.status;
    update public.enrollments set status = p_target_status where id = p_enrollment_id returning * into v_row;
    insert into private.enrollment_status_history (enrollment_id, previous_status, current_status, reason, changed_by, request_id)
    values (v_row.id, v_previous, v_row.status, btrim(p_reason), auth.uid(), p_request_id);
    return to_jsonb(v_row);
end;
$$;

revoke all on function public.register_enrollment(uuid, uuid, uuid, uuid) from public, anon;
revoke all on function public.get_enrollment(uuid) from public, anon;
revoke all on function public.change_enrollment_status(uuid, text, timestamptz, text, uuid) from public, anon;
grant execute on function public.register_enrollment(uuid, uuid, uuid, uuid) to authenticated;
grant execute on function public.get_enrollment(uuid) to authenticated;
grant execute on function public.change_enrollment_status(uuid, text, timestamptz, text, uuid) to authenticated;

commit;
