-- Matriz transacional das RPCs de responsáveis e de suas regras de ciclo.
-- Usa somente dados sintéticos e desfaz alunos, contatos, histórico e eventos.

begin;

create temporary table test_guardian_operator on commit drop as
select id
from public.profiles
where role = 'coordinator'
  and active;

grant select on table pg_temp.test_guardian_operator to authenticated;

do $guard$
begin
    if (select count(*) from pg_temp.test_guardian_operator) <> 1 then
        raise exception 'guardian_matrix_requires_one_active_coordinator';
    end if;
end;
$guard$;

-- Os registros existem apenas durante esta transação. Inserção direta prepara
-- o cenário; todas as operações sob teste passam pelas RPCs autenticadas.
insert into public.students (id, full_name, cpf, birth_date, created_by)
values (
    '00000000-0000-4000-8000-000000000301',
    'Aluno Sintético Responsáveis',
    '11144477735',
    date '2015-05-10',
    (select id from pg_temp.test_guardian_operator)
);

insert into public.guardians (id, full_name, phone, email, created_by)
values (
    '00000000-0000-4000-8000-000000000302',
    'Contato Sintético Principal',
    '61999991234',
    'principal@example.test',
    (select id from pg_temp.test_guardian_operator)
);

insert into public.student_guardians (
    student_id,
    guardian_id,
    relationship,
    is_primary,
    receives_communications,
    created_by
)
values (
    '00000000-0000-4000-8000-000000000301',
    '00000000-0000-4000-8000-000000000302',
    'responsible_contact',
    true,
    true,
    (select id from pg_temp.test_guardian_operator)
);

create or replace function pg_temp.expect_guardian_sqlstate(
    p_label text,
    p_statement text,
    p_expected_sqlstate text
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    begin
        execute p_statement;
        if p_expected_sqlstate <> '00000' then
            raise exception 'operation_was_unexpectedly_allowed';
        end if;
    exception
        when others then
            if sqlstate <> p_expected_sqlstate then
                raise exception 'guardian_matrix_failure:%:expected:%:received:%',
                    p_label,
                    p_expected_sqlstate,
                    sqlstate;
            end if;
    end;
end;
$$;

grant execute on function pg_temp.expect_guardian_sqlstate(text, text, text)
to authenticated;

select set_config(
    'request.jwt.claim.sub',
    (select id::text from pg_temp.test_guardian_operator),
    true
);
select set_config('request.jwt.claim.role', 'authenticated', true);

-- Cada papel percorre sete operações. Erros P0002 nos papéis autorizados
-- comprovam que a RPC passou pela autorização e chegou à regra de existência.
update public.profiles
set role = 'coordinator', active = true
where id = (select id from pg_temp.test_guardian_operator);
set local role authenticated;
select pg_temp.expect_guardian_sqlstate(
    'coordinator.list',
    $$select public.list_student_guardians('00000000-0000-4000-8000-000000000301')$$,
    '00000'
);
select pg_temp.expect_guardian_sqlstate(
    'coordinator.detail',
    $$select public.get_student_guardian_detail(
        '00000000-0000-4000-8000-000000000301', gen_random_uuid(), gen_random_uuid()
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'coordinator.add',
    $$select public.add_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), true,
        'Contato Sintético', '61999991234', null, 'other', false, true
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'coordinator.update',
    $$select public.update_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), now(),
        'Contato Sintético', '61999991234', null, 'other', true
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'coordinator.primary',
    $$select public.set_primary_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now()
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'coordinator.unlink',
    $$select public.unlink_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(),
        'Motivo sintético válido'
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'coordinator.student_update',
    $$select public.update_student(
        gen_random_uuid(), gen_random_uuid(), now(), 'Aluno Sintético', date '2015-05-10'
    )$$,
    'P0002'
);
reset role;

update public.profiles
set role = 'receptionist', active = true
where id = (select id from pg_temp.test_guardian_operator);
set local role authenticated;
select pg_temp.expect_guardian_sqlstate(
    'receptionist.list',
    $$select public.list_student_guardians('00000000-0000-4000-8000-000000000301')$$,
    '00000'
);
select pg_temp.expect_guardian_sqlstate(
    'receptionist.detail',
    $$select public.get_student_guardian_detail(
        '00000000-0000-4000-8000-000000000301', gen_random_uuid(), gen_random_uuid()
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'receptionist.add',
    $$select public.add_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), true,
        'Contato Sintético', '61999991234', null, 'other', false, true
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'receptionist.update',
    $$select public.update_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), now(),
        'Contato Sintético', '61999991234', null, 'other', true
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'receptionist.primary',
    $$select public.set_primary_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now()
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'receptionist.unlink',
    $$select public.unlink_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(),
        'Motivo sintético válido'
    )$$,
    'P0002'
);
select pg_temp.expect_guardian_sqlstate(
    'receptionist.student_update',
    $$select public.update_student(
        gen_random_uuid(), gen_random_uuid(), now(), 'Aluno Sintético', date '2015-05-10'
    )$$,
    'P0002'
);
reset role;

update public.profiles
set role = 'read_only', active = true
where id = (select id from pg_temp.test_guardian_operator);
set local role authenticated;
select pg_temp.expect_guardian_sqlstate(
    'read_only.list',
    $$select public.list_student_guardians('00000000-0000-4000-8000-000000000301')$$,
    '00000'
);
select pg_temp.expect_guardian_sqlstate(
    'read_only.detail',
    $$select public.get_student_guardian_detail(
        '00000000-0000-4000-8000-000000000301', gen_random_uuid(), gen_random_uuid()
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'read_only.add',
    $$select public.add_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), true,
        'Contato Sintético', '61999991234', null, 'other', false, true
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'read_only.update',
    $$select public.update_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), now(),
        'Contato Sintético', '61999991234', null, 'other', true
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'read_only.primary',
    $$select public.set_primary_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now()
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'read_only.unlink',
    $$select public.unlink_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(),
        'Motivo sintético válido'
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'read_only.student_update',
    $$select public.update_student(
        gen_random_uuid(), gen_random_uuid(), now(), 'Aluno Sintético', date '2015-05-10'
    )$$,
    '42501'
);
reset role;

update public.profiles
set role = 'instructor', active = true
where id = (select id from pg_temp.test_guardian_operator);
set local role authenticated;
select pg_temp.expect_guardian_sqlstate(
    'instructor.list',
    $$select public.list_student_guardians('00000000-0000-4000-8000-000000000301')$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'instructor.detail',
    $$select public.get_student_guardian_detail(
        '00000000-0000-4000-8000-000000000301', gen_random_uuid(), gen_random_uuid()
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'instructor.add',
    $$select public.add_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), true,
        'Contato Sintético', '61999991234', null, 'other', false, true
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'instructor.update',
    $$select public.update_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), now(),
        'Contato Sintético', '61999991234', null, 'other', true
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'instructor.primary',
    $$select public.set_primary_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now()
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'instructor.unlink',
    $$select public.unlink_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(),
        'Motivo sintético válido'
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'instructor.student_update',
    $$select public.update_student(
        gen_random_uuid(), gen_random_uuid(), now(), 'Aluno Sintético', date '2015-05-10'
    )$$,
    '42501'
);
reset role;

update public.profiles
set role = 'pending', active = false
where id = (select id from pg_temp.test_guardian_operator);
set local role authenticated;
select pg_temp.expect_guardian_sqlstate(
    'pending.list',
    $$select public.list_student_guardians('00000000-0000-4000-8000-000000000301')$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'pending.detail',
    $$select public.get_student_guardian_detail(
        '00000000-0000-4000-8000-000000000301', gen_random_uuid(), gen_random_uuid()
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'pending.add',
    $$select public.add_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), true,
        'Contato Sintético', '61999991234', null, 'other', false, true
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'pending.update',
    $$select public.update_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(), now(),
        'Contato Sintético', '61999991234', null, 'other', true
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'pending.primary',
    $$select public.set_primary_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now()
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'pending.unlink',
    $$select public.unlink_student_guardian(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), now(),
        'Motivo sintético válido'
    )$$,
    '42501'
);
select pg_temp.expect_guardian_sqlstate(
    'pending.student_update',
    $$select public.update_student(
        gen_random_uuid(), gen_random_uuid(), now(), 'Aluno Sintético', date '2015-05-10'
    )$$,
    '42501'
);
reset role;

-- Além da matriz de acesso, o cenário completo confirma versões, principal
-- único, mascaramento, histórico privado e desvinculação sem DELETE.
update public.profiles
set role = 'coordinator', active = true
where id = (select id from pg_temp.test_guardian_operator);

-- As chamadas ainda validam auth.uid() internamente. O bloco administrativo
-- consulta tabelas privadas somente para provar invariantes antes do rollback.
do $lifecycle$
declare
    v_student_id constant uuid := '00000000-0000-4000-8000-000000000301';
    v_old_guardian_id constant uuid := '00000000-0000-4000-8000-000000000302';
    v_new_guardian_id constant uuid := '00000000-0000-4000-8000-000000000303';
    v_student_version timestamptz;
    v_guardian_version timestamptz;
    v_result jsonb;
begin
    select updated_at into v_student_version
    from public.students where id = v_student_id;

    v_result := public.add_student_guardian(
        v_student_id,
        v_new_guardian_id,
        gen_random_uuid(),
        v_student_version,
        true,
        'Novo Contato Sintético',
        '61988881234',
        'novo@example.test',
        'legal_guardian',
        false,
        true
    );
    if not (v_result ->> 'changed')::boolean then
        raise exception 'guardian_add_did_not_change';
    end if;
    v_student_version := (v_result ->> 'student_updated_at')::timestamptz;
    v_guardian_version := (v_result ->> 'guardian_updated_at')::timestamptz;

    v_result := public.update_student_guardian(
        v_student_id,
        v_new_guardian_id,
        gen_random_uuid(),
        v_student_version,
        v_guardian_version,
        'Novo Contato Sintético Atualizado',
        '61977774321',
        'atualizado@example.test',
        'parent',
        true
    );
    v_student_version := (v_result ->> 'student_updated_at')::timestamptz;

    v_result := public.set_primary_student_guardian(
        v_student_id,
        v_new_guardian_id,
        gen_random_uuid(),
        v_student_version
    );
    if not (v_result ->> 'is_primary')::boolean then
        raise exception 'guardian_primary_was_not_changed';
    end if;
    v_student_version := (v_result ->> 'student_updated_at')::timestamptz;

    v_result := public.unlink_student_guardian(
        v_student_id,
        v_old_guardian_id,
        gen_random_uuid(),
        v_student_version,
        'Vínculo sintético removido pela matriz'
    );

    if jsonb_array_length(public.list_student_guardians(v_student_id) -> 'items') <> 1 then
        raise exception 'guardian_masked_list_has_unexpected_size';
    end if;
    if (public.list_student_guardians(v_student_id) -> 'items' -> 0 ->> 'phone_masked')
       <> '(61) *****-4321' then
        raise exception 'guardian_phone_was_not_masked';
    end if;
    if (select count(*) from private.guardian_change_history where student_id = v_student_id) <> 4 then
        raise exception 'guardian_history_has_unexpected_size';
    end if;
    if (select count(*) from public.student_guardians where student_id = v_student_id and active and is_primary) <> 1 then
        raise exception 'guardian_primary_invariant_failed';
    end if;

    begin
        perform public.unlink_student_guardian(
            v_student_id,
            v_new_guardian_id,
            gen_random_uuid(),
            (v_result ->> 'student_updated_at')::timestamptz,
            'Tentativa sintética contra o principal'
        );
        raise exception 'primary_guardian_was_unexpectedly_unlinked';
    exception
        when check_violation then
            null;
    end;
end;
$lifecycle$;

reset role;

rollback;

select '35/35 guardian permission checks passed; lifecycle assertions passed; transaction rolled back' as result;
