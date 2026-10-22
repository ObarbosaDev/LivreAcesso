-- Homologação transacional da matriz de acesso às RPCs de alunos.
-- Nenhuma mudança persiste: o script termina em ROLLBACK e não insere dados reais.

begin;

create temporary table test_operator on commit drop as
select id
from public.profiles
where role = 'coordinator'
  and active;

do $guard$
begin
    if (select count(*) from pg_temp.test_operator) <> 1 then
        raise exception 'role_matrix_requires_one_active_coordinator';
    end if;
end;
$guard$;

-- A função executa com os privilégios do papel testado. Cada chamada precisa
-- terminar no SQLSTATE esperado; qualquer divergência aborta toda a transação.
create or replace function pg_temp.expect_sqlstate(
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
                raise exception 'role_matrix_failure:%:expected:%:received:%',
                    p_label,
                    p_expected_sqlstate,
                    sqlstate;
            end if;
    end;
end;
$$;

grant execute on function pg_temp.expect_sqlstate(text, text, text) to authenticated;

select set_config(
    'request.jwt.claim.sub',
    (select id::text from pg_temp.test_operator),
    true
);
select set_config('request.jwt.claim.role', 'authenticated', true);

-- Coordenação pode consultar, cadastrar, editar e mudar o ciclo cadastral.
update public.profiles
set role = 'coordinator', active = true
where id = (select id from pg_temp.test_operator);
set local role authenticated;
select pg_temp.expect_sqlstate(
    'coordinator.list',
    'select public.list_students(null, null, 25, 0)',
    '00000'
);
select pg_temp.expect_sqlstate(
    'coordinator.detail',
    'select public.get_student_detail(gen_random_uuid(), gen_random_uuid())',
    'P0002'
);
select pg_temp.expect_sqlstate(
    'coordinator.register',
    $$select public.register_student_with_guardian_v2(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(),
        'x', '52998224725', date '2015-05-10',
        'Responsável Teste', '61999991234', null, 'responsible_contact'
    )$$,
    '22023'
);
select pg_temp.expect_sqlstate(
    'coordinator.update',
    $$select public.update_student_with_guardian(
        gen_random_uuid(), gen_random_uuid(), now(),
        'x', date '2015-05-10', 'Responsável Teste', '61999991234', null
    )$$,
    '22023'
);
select pg_temp.expect_sqlstate(
    'coordinator.status',
    $$select public.change_student_status(
        gen_random_uuid(), gen_random_uuid(), now(), 'inactive', 'curto'
    )$$,
    '22023'
);
reset role;

-- Recepção opera cadastro, detalhe e edição, mas não ativa/desativa pessoas.
update public.profiles
set role = 'receptionist', active = true
where id = (select id from pg_temp.test_operator);
set local role authenticated;
select pg_temp.expect_sqlstate(
    'receptionist.list',
    'select public.list_students(null, null, 25, 0)',
    '00000'
);
select pg_temp.expect_sqlstate(
    'receptionist.detail',
    'select public.get_student_detail(gen_random_uuid(), gen_random_uuid())',
    'P0002'
);
select pg_temp.expect_sqlstate(
    'receptionist.register',
    $$select public.register_student_with_guardian_v2(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(),
        'x', '52998224725', date '2015-05-10',
        'Responsável Teste', '61999991234', null, 'responsible_contact'
    )$$,
    '22023'
);
select pg_temp.expect_sqlstate(
    'receptionist.update',
    $$select public.update_student_with_guardian(
        gen_random_uuid(), gen_random_uuid(), now(),
        'x', date '2015-05-10', 'Responsável Teste', '61999991234', null
    )$$,
    '22023'
);
select pg_temp.expect_sqlstate(
    'receptionist.status',
    $$select public.change_student_status(
        gen_random_uuid(), gen_random_uuid(), now(), 'inactive', 'curto'
    )$$,
    '42501'
);
reset role;

-- Consulta pode ver apenas a projeção mascarada e paginada.
update public.profiles
set role = 'read_only', active = true
where id = (select id from pg_temp.test_operator);
set local role authenticated;
select pg_temp.expect_sqlstate(
    'read_only.list',
    'select public.list_students(null, null, 25, 0)',
    '00000'
);
select pg_temp.expect_sqlstate(
    'read_only.detail',
    'select public.get_student_detail(gen_random_uuid(), gen_random_uuid())',
    '42501'
);
select pg_temp.expect_sqlstate(
    'read_only.register',
    $$select public.register_student_with_guardian_v2(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(),
        'x', '52998224725', date '2015-05-10',
        'Responsável Teste', '61999991234', null, 'responsible_contact'
    )$$,
    '42501'
);
select pg_temp.expect_sqlstate(
    'read_only.update',
    $$select public.update_student_with_guardian(
        gen_random_uuid(), gen_random_uuid(), now(),
        'x', date '2015-05-10', 'Responsável Teste', '61999991234', null
    )$$,
    '42501'
);
select pg_temp.expect_sqlstate(
    'read_only.status',
    $$select public.change_student_status(
        gen_random_uuid(), gen_random_uuid(), now(), 'inactive', 'curto'
    )$$,
    '42501'
);
reset role;

-- Instrutor ainda não possui finalidade para consultar cadastros gerais.
update public.profiles
set role = 'instructor', active = true
where id = (select id from pg_temp.test_operator);
set local role authenticated;
select pg_temp.expect_sqlstate(
    'instructor.list',
    'select public.list_students(null, null, 25, 0)',
    '42501'
);
select pg_temp.expect_sqlstate(
    'instructor.detail',
    'select public.get_student_detail(gen_random_uuid(), gen_random_uuid())',
    '42501'
);
select pg_temp.expect_sqlstate(
    'instructor.register',
    $$select public.register_student_with_guardian_v2(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(),
        'x', '52998224725', date '2015-05-10',
        'Responsável Teste', '61999991234', null, 'responsible_contact'
    )$$,
    '42501'
);
select pg_temp.expect_sqlstate(
    'instructor.update',
    $$select public.update_student_with_guardian(
        gen_random_uuid(), gen_random_uuid(), now(),
        'x', date '2015-05-10', 'Responsável Teste', '61999991234', null
    )$$,
    '42501'
);
select pg_temp.expect_sqlstate(
    'instructor.status',
    $$select public.change_student_status(
        gen_random_uuid(), gen_random_uuid(), now(), 'inactive', 'curto'
    )$$,
    '42501'
);
reset role;

-- Perfil pendente e inativo não acessa nenhuma operação.
update public.profiles
set role = 'pending', active = false
where id = (select id from pg_temp.test_operator);
set local role authenticated;
select pg_temp.expect_sqlstate(
    'pending.list',
    'select public.list_students(null, null, 25, 0)',
    '42501'
);
select pg_temp.expect_sqlstate(
    'pending.detail',
    'select public.get_student_detail(gen_random_uuid(), gen_random_uuid())',
    '42501'
);
select pg_temp.expect_sqlstate(
    'pending.register',
    $$select public.register_student_with_guardian_v2(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(),
        'x', '52998224725', date '2015-05-10',
        'Responsável Teste', '61999991234', null, 'responsible_contact'
    )$$,
    '42501'
);
select pg_temp.expect_sqlstate(
    'pending.update',
    $$select public.update_student_with_guardian(
        gen_random_uuid(), gen_random_uuid(), now(),
        'x', date '2015-05-10', 'Responsável Teste', '61999991234', null
    )$$,
    '42501'
);
select pg_temp.expect_sqlstate(
    'pending.status',
    $$select public.change_student_status(
        gen_random_uuid(), gen_random_uuid(), now(), 'inactive', 'curto'
    )$$,
    '42501'
);
reset role;

rollback;

-- Se qualquer expectativa falhar, o script aborta antes deste resultado.
select '25/25 permission checks passed; transaction rolled back' as result;
