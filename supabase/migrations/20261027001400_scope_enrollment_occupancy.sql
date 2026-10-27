-- Restringe o resumo de ocupação ao escopo do instrutor autenticado.
--
-- Coordenação, recepção e consulta podem acompanhar qualquer turma permitida.
-- Instrutor só recebe o resumo de uma turma em que possui vínculo ativo; isso
-- evita transformar um endpoint estatístico em uma forma de enumerar turmas.

begin;

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
    if private.has_any_role(array['instructor'::public.user_role])
       and not exists (
           select 1
             from public.class_instructors ci
            where ci.class_id = p_class_id
              and ci.instructor_id = auth.uid()
       ) then
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

revoke all on function public.get_class_enrollment_occupancy(uuid) from public, anon;
grant execute on function public.get_class_enrollment_occupancy(uuid) to authenticated;

commit;
