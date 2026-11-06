-- Instrutor e consulta conseguem listar matriculas da propria turma, mas
-- get_student_detail (nome + CPF + contato do responsavel) e restrito a
-- coordenacao/recepcao de proposito. Isso deixava a tela de matriculas sem
-- nome nenhum pra esses dois papeis: toda matricula virava "Estudante nao
-- encontrado". Esta funcao devolve so o nome, por id, pros quatro papeis
-- operacionais - ids sao UUID, nao adivinhaveis, e nome sozinho nao e dado
-- sensivel como CPF ou telefone do responsavel.

begin;

create or replace function public.get_student_names(p_student_ids uuid[])
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_result jsonb;
begin
    if not private.has_any_role(
        array['coordinator', 'receptionist', 'instructor', 'read_only']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if p_student_ids is null or array_length(p_student_ids, 1) is null then
        return '{}'::jsonb;
    end if;
    if array_length(p_student_ids, 1) > 200 then
        raise exception using errcode = '22023', message = 'too_many_ids';
    end if;

    select coalesce(jsonb_object_agg(student.id, student.full_name), '{}'::jsonb)
    into v_result
    from public.students as student
    where student.id = any(p_student_ids);

    return v_result;
end;
$$;

revoke all on function public.get_student_names(uuid[]) from public, anon;
grant execute on function public.get_student_names(uuid[]) to authenticated;

commit;
