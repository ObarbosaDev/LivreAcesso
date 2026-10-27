-- BL-05: consulta explícita da matrícula ativa de um estudante em uma turma.
-- Mantemos esta leitura em RPC para que o cliente nunca receba acesso direto à tabela.
begin;

create or replace function public.get_active_enrollment(
    p_student_id uuid,
    p_class_id uuid
)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_row public.enrollments;
begin
    if not private.has_any_role(array[
        'coordinator'::public.user_role,
        'receptionist'::public.user_role,
        'read_only'::public.user_role,
        'instructor'::public.user_role
    ]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    select * into v_row
    from public.enrollments
    where student_id = p_student_id
      and class_id = p_class_id
      and status = 'ativa';
    if not found then
        return null;
    end if;
    return to_jsonb(v_row);
end;
$$;

revoke all on function public.get_active_enrollment(uuid, uuid) from public, anon;
grant execute on function public.get_active_enrollment(uuid, uuid) to authenticated;

commit;
