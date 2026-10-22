-- Retorna timestamps autoritativos no cadastro para a primeira edição otimista.
-- A função anterior permanece interna para preservar a transação já testada.

begin;

create or replace function public.register_student_with_guardian_v2(
    p_student_id uuid,
    p_guardian_id uuid,
    p_request_id uuid,
    p_full_name text,
    p_cpf text,
    p_birth_date date,
    p_guardian_full_name text,
    p_guardian_phone text,
    p_guardian_email text default null,
    p_relationship public.guardian_relationship default 'responsible_contact'
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_student_id uuid;
    v_created_at timestamptz;
    v_updated_at timestamptz;
begin
    v_student_id := public.register_student_with_guardian(
        p_student_id,
        p_guardian_id,
        p_request_id,
        p_full_name,
        p_cpf,
        p_birth_date,
        p_guardian_full_name,
        p_guardian_phone,
        p_guardian_email,
        p_relationship
    );

    select created_at, updated_at
    into v_created_at, v_updated_at
    from public.students
    where id = v_student_id;

    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found_after_insert';
    end if;

    return jsonb_build_object(
        'id', v_student_id,
        'created_at', v_created_at,
        'updated_at', v_updated_at
    );
end;
$$;

comment on function public.register_student_with_guardian_v2(
    uuid, uuid, uuid, text, text, date, text, text, text, public.guardian_relationship
) is 'Cadastra aluno e devolve UUID e timestamps gerados pelo PostgreSQL.';

revoke all on function public.register_student_with_guardian_v2(
    uuid, uuid, uuid, text, text, date, text, text, text, public.guardian_relationship
) from public, anon;
grant execute on function public.register_student_with_guardian_v2(
    uuid, uuid, uuid, text, text, date, text, text, text, public.guardian_relationship
) to authenticated;

-- Chamadas externas devem usar a versão que devolve timestamps. A wrapper
-- continua conseguindo executar a função anterior como proprietária.
revoke all on function public.register_student_with_guardian(
    uuid, uuid, uuid, text, text, date, text, text, text, public.guardian_relationship
) from authenticated;

commit;
