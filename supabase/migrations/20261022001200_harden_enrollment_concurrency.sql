-- BL-05: endurece concorrência, listagem e auditoria das matrículas.
begin;

create or replace function public.register_enrollment(
    p_enrollment_id uuid, p_student_id uuid, p_class_id uuid, p_request_id uuid
)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
    v_capacity integer;
    v_active_count integer;
    v_student_status public.student_status;
    v_row public.enrollments;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    select status into v_student_status from public.students where id = p_student_id;
    if v_student_status is distinct from 'active'::public.student_status then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    -- O bloqueio da linha da turma serializa a contagem e impede duas últimas
    -- vagas de serem concedidas simultaneamente por requisições concorrentes.
    select capacity into v_capacity from public.classes where id = p_class_id and active for update;
    if v_capacity is null then raise exception using errcode = 'P0002', message = 'class_not_found'; end if;
    if exists (select 1 from public.enrollments where student_id = p_student_id and class_id = p_class_id and status = 'ativa') then
        raise exception using errcode = '23505', message = 'duplicate_enrollment';
    end if;
    select count(*) into v_active_count from public.enrollments where class_id = p_class_id and status = 'ativa';
    if v_active_count >= v_capacity then raise exception using errcode = 'P0001', message = 'class_capacity_reached'; end if;
    insert into public.enrollments (id, student_id, class_id) values (p_enrollment_id, p_student_id, p_class_id) returning * into v_row;
    insert into private.enrollment_status_history (enrollment_id, previous_status, current_status, reason, changed_by, request_id)
    values (v_row.id, null, v_row.status, 'Matrícula criada.', auth.uid(), p_request_id);
    return to_jsonb(v_row);
end;
$$;

create or replace function public.list_enrollments(
    p_student_id uuid default null, p_class_id uuid default null,
    p_status text default null, p_limit integer default 25, p_offset integer default 0
)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_items jsonb; v_total integer;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'read_only'::public.user_role, 'instructor'::public.user_role]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if p_limit not between 1 and 100 or p_offset < 0 then raise exception using errcode = '22023', message = 'invalid_pagination'; end if;
    if private.has_any_role(array['instructor'::public.user_role]) and not exists (
        select 1 from public.class_instructors ci where ci.class_id = p_class_id and ci.instructor_id = auth.uid()
    ) then raise exception using errcode = '42501', message = 'forbidden'; end if;
    select count(*) into v_total from public.enrollments e where (p_student_id is null or e.student_id = p_student_id) and (p_class_id is null or e.class_id = p_class_id) and (p_status is null or e.status = p_status);
    select coalesce(jsonb_agg(to_jsonb(rows) order by rows.created_at desc), '[]'::jsonb) into v_items from (
        select e.id, e.student_id, e.class_id, e.status, e.created_at, e.updated_at from public.enrollments e
        where (p_student_id is null or e.student_id = p_student_id) and (p_class_id is null or e.class_id = p_class_id) and (p_status is null or e.status = p_status)
        order by e.created_at desc limit p_limit offset p_offset
    ) rows;
    return jsonb_build_object('items', v_items, 'total', v_total);
end;
$$;

create or replace function public.get_enrollment(p_enrollment_id uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_row public.enrollments;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'read_only'::public.user_role, 'instructor'::public.user_role]) then raise exception using errcode = '42501', message = 'forbidden'; end if;
    select e.* into v_row from public.enrollments e where e.id = p_enrollment_id;
    if not found then raise exception using errcode = 'P0002', message = 'enrollment_not_found'; end if;
    if private.has_any_role(array['instructor'::public.user_role]) and not exists (select 1 from public.class_instructors ci where ci.class_id = v_row.class_id and ci.instructor_id = auth.uid()) then raise exception using errcode = '42501', message = 'forbidden'; end if;
    return to_jsonb(v_row);
end;
$$;

create or replace function public.get_active_enrollment(p_student_id uuid, p_class_id uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_row public.enrollments;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'read_only'::public.user_role, 'instructor'::public.user_role]) then raise exception using errcode = '42501', message = 'forbidden'; end if;
    if private.has_any_role(array['instructor'::public.user_role]) and not exists (select 1 from public.class_instructors ci where ci.class_id = p_class_id and ci.instructor_id = auth.uid()) then raise exception using errcode = '42501', message = 'forbidden'; end if;
    select * into v_row from public.enrollments where student_id = p_student_id and class_id = p_class_id and status = 'ativa';
    return case when found then to_jsonb(v_row) else null end;
end;
$$;

revoke all on function public.list_enrollments(uuid, uuid, text, integer, integer) from public, anon;
grant execute on function public.list_enrollments(uuid, uuid, text, integer, integer) to authenticated;
revoke all on function public.get_enrollment(uuid) from public, anon;
grant execute on function public.get_enrollment(uuid) to authenticated;
revoke all on function public.get_active_enrollment(uuid, uuid) from public, anon;
grant execute on function public.get_active_enrollment(uuid, uuid) to authenticated;

commit;
