-- Endurece o ciclo de matrícula sem alterar registros existentes.
--
-- A matrícula só pode voltar a ativa se ainda houver vaga. O bloqueio da
-- turma acontece dentro da mesma transação da mudança de status, evitando
-- que duas reativações concorrentes ultrapassem a capacidade configurada.
-- A segunda função fornece ocupação para telas de coordenação sem expor
-- diretamente as tabelas de matrícula.

begin;

create or replace function public.change_enrollment_status(
    p_enrollment_id uuid,
    p_target_status text,
    p_expected_updated_at timestamptz,
    p_reason text,
    p_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_row public.enrollments;
    v_previous text;
    v_capacity integer;
    v_active_count integer;
begin
    if not private.has_any_role(array['coordinator'::public.user_role]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if p_target_status not in ('ativa', 'cancelada') then
        raise exception using errcode = '22023', message = 'invalid_enrollment_status';
    end if;
    if char_length(btrim(p_reason)) not between 10 and 500 then
        raise exception using errcode = '22023', message = 'invalid_reason';
    end if;

    select * into v_row
      from public.enrollments
     where id = p_enrollment_id
     for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'enrollment_not_found';
    end if;
    if v_row.updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'enrollment_version_conflict';
    end if;

    if p_target_status = 'ativa' and v_row.status <> 'ativa' then
        select capacity into v_capacity
          from public.classes
         where id = v_row.class_id and active
         for update;
        if v_capacity is null then
            raise exception using errcode = 'P0002', message = 'class_not_found';
        end if;
        select count(*)::integer into v_active_count
          from public.enrollments
         where class_id = v_row.class_id and status = 'ativa';
        if v_active_count >= v_capacity then
            raise exception using errcode = 'P0001', message = 'class_capacity_reached';
        end if;
    end if;

    v_previous := v_row.status;
    update public.enrollments
       set status = p_target_status
     where id = p_enrollment_id
     returning * into v_row;
    insert into private.enrollment_status_history
        (enrollment_id, previous_status, current_status, reason, changed_by, request_id)
    values
        (v_row.id, v_previous, v_row.status, btrim(p_reason), auth.uid(), p_request_id);
    return to_jsonb(v_row);
end;
$$;

create or replace function public.get_class_enrollment_occupancy(p_class_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_capacity integer;
    v_enrolled integer;
begin
    if not private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role, 'read_only'::public.user_role, 'instructor'::public.user_role]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    select capacity into v_capacity from public.classes where id = p_class_id and active;
    if v_capacity is null then
        raise exception using errcode = 'P0002', message = 'class_not_found';
    end if;
    select count(*)::integer into v_enrolled
      from public.enrollments
     where class_id = p_class_id and status = 'ativa';
    return jsonb_build_object(
        'class_id', p_class_id,
        'capacity', v_capacity,
        'enrolled', v_enrolled,
        'available', greatest(v_capacity - v_enrolled, 0)
    );
end;
$$;

revoke all on function public.change_enrollment_status(uuid, text, timestamptz, text, uuid) from public, anon;
grant execute on function public.change_enrollment_status(uuid, text, timestamptz, text, uuid) to authenticated;
revoke all on function public.get_class_enrollment_occupancy(uuid) from public, anon;
grant execute on function public.get_class_enrollment_occupancy(uuid) to authenticated;

commit;
