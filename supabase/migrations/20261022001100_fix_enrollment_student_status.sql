-- Corrige a integração do BL-05 com o ciclo cadastral real do estudante.
-- Students usa o enum status; a RPC não deve inventar uma coluna booleana paralela.
begin;

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

commit;
