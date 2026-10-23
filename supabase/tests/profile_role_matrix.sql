-- Matriz transacional das RPCs de perfis operacionais.
-- Usa a única coordenação ativa e desfaz toda troca de papel ao final.

begin;

create temporary table test_profile_operator on commit drop as
select id, updated_at
from public.profiles
where role = 'coordinator'
  and active;

grant select on table pg_temp.test_profile_operator to authenticated;

do $guard$
begin
    if (select count(*) from pg_temp.test_profile_operator) <> 1 then
        raise exception 'profile_matrix_requires_one_active_coordinator';
    end if;
end;
$guard$;

create or replace function pg_temp.expect_profile_sqlstate(
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
                raise exception 'profile_matrix_failure:%:expected:%:received:%',
                    p_label,
                    p_expected_sqlstate,
                    sqlstate;
            end if;
    end;
end;
$$;

grant execute on function pg_temp.expect_profile_sqlstate(text, text, text)
to authenticated;

select set_config(
    'request.jwt.claim.sub',
    (select id::text from pg_temp.test_profile_operator),
    true
);
select set_config('request.jwt.claim.role', 'authenticated', true);

-- Coordenação acessa leitura e administração; o último coordenador não pode sair.
update public.profiles
set role = 'coordinator', active = true
where id = (select id from pg_temp.test_profile_operator);
set local role authenticated;
select pg_temp.expect_profile_sqlstate(
    'coordinator.me',
    'select public.get_my_profile()',
    '00000'
);
select pg_temp.expect_profile_sqlstate(
    'coordinator.rename',
    $$select public.update_my_profile_name(now(), 'x', gen_random_uuid())$$,
    '22023'
);
select pg_temp.expect_profile_sqlstate(
    'coordinator.list',
    'select public.list_profiles(null, null, null, 25, 0)',
    '00000'
);
select pg_temp.expect_profile_sqlstate(
    'coordinator.detail',
    'select public.get_profile_detail(gen_random_uuid())',
    'P0002'
);
select pg_temp.expect_profile_sqlstate(
    'coordinator.role',
    $$select public.change_profile_role(
        gen_random_uuid(), 'pending', 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '22023'
);
select pg_temp.expect_profile_sqlstate(
    'coordinator.activation',
    $$select public.change_profile_activation(
        gen_random_uuid(), true, 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    'P0002'
);
select pg_temp.expect_profile_sqlstate(
    'coordinator.last_active',
    format(
        $$select public.change_profile_activation(
            %L::uuid, false, 'Teste do último coordenador', %L::timestamptz, gen_random_uuid()
        )$$,
        (select id from pg_temp.test_profile_operator),
        (select updated_at from public.profiles where id = (
            select id from pg_temp.test_profile_operator
        ))
    ),
    'P0001'
);
reset role;

-- Recepção consulta o próprio perfil e nome, mas não administra terceiros.
update public.profiles
set role = 'receptionist', active = true
where id = (select id from pg_temp.test_profile_operator);
set local role authenticated;
select pg_temp.expect_profile_sqlstate('receptionist.me', 'select public.get_my_profile()', '00000');
select pg_temp.expect_profile_sqlstate(
    'receptionist.rename',
    $$select public.update_my_profile_name(now(), 'x', gen_random_uuid())$$,
    '22023'
);
select pg_temp.expect_profile_sqlstate(
    'receptionist.list',
    'select public.list_profiles(null, null, null, 25, 0)',
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'receptionist.detail',
    'select public.get_profile_detail(gen_random_uuid())',
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'receptionist.role',
    $$select public.change_profile_role(
        gen_random_uuid(), 'pending', 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'receptionist.activation',
    $$select public.change_profile_activation(
        gen_random_uuid(), true, 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '42501'
);
reset role;

-- Consulta enxerga o próprio perfil, sem poder administrar a equipe.
update public.profiles
set role = 'read_only', active = true
where id = (select id from pg_temp.test_profile_operator);
set local role authenticated;
select pg_temp.expect_profile_sqlstate('read_only.me', 'select public.get_my_profile()', '00000');
select pg_temp.expect_profile_sqlstate(
    'read_only.rename',
    $$select public.update_my_profile_name(now(), 'x', gen_random_uuid())$$,
    '22023'
);
select pg_temp.expect_profile_sqlstate(
    'read_only.list',
    'select public.list_profiles(null, null, null, 25, 0)',
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'read_only.detail',
    'select public.get_profile_detail(gen_random_uuid())',
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'read_only.role',
    $$select public.change_profile_role(
        gen_random_uuid(), 'pending', 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'read_only.activation',
    $$select public.change_profile_activation(
        gen_random_uuid(), true, 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '42501'
);
reset role;

-- Instrutor tem o próprio contexto, mas perfis de terceiros não são sua finalidade.
update public.profiles
set role = 'instructor', active = true
where id = (select id from pg_temp.test_profile_operator);
set local role authenticated;
select pg_temp.expect_profile_sqlstate('instructor.me', 'select public.get_my_profile()', '00000');
select pg_temp.expect_profile_sqlstate(
    'instructor.rename',
    $$select public.update_my_profile_name(now(), 'x', gen_random_uuid())$$,
    '22023'
);
select pg_temp.expect_profile_sqlstate(
    'instructor.list',
    'select public.list_profiles(null, null, null, 25, 0)',
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'instructor.detail',
    'select public.get_profile_detail(gen_random_uuid())',
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'instructor.role',
    $$select public.change_profile_role(
        gen_random_uuid(), 'pending', 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'instructor.activation',
    $$select public.change_profile_activation(
        gen_random_uuid(), true, 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '42501'
);
reset role;

-- Conta pendente/inativa ainda consulta e corrige o próprio nome, mas não opera.
update public.profiles
set role = 'pending', active = false
where id = (select id from pg_temp.test_profile_operator);
set local role authenticated;
select pg_temp.expect_profile_sqlstate('pending.me', 'select public.get_my_profile()', '00000');
select pg_temp.expect_profile_sqlstate(
    'pending.rename',
    $$select public.update_my_profile_name(now(), 'x', gen_random_uuid())$$,
    '22023'
);
select pg_temp.expect_profile_sqlstate(
    'pending.list',
    'select public.list_profiles(null, null, null, 25, 0)',
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'pending.detail',
    'select public.get_profile_detail(gen_random_uuid())',
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'pending.role',
    $$select public.change_profile_role(
        gen_random_uuid(), 'pending', 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '42501'
);
select pg_temp.expect_profile_sqlstate(
    'pending.activation',
    $$select public.change_profile_activation(
        gen_random_uuid(), true, 'Motivo sintético válido', now(), gen_random_uuid()
    )$$,
    '42501'
);
reset role;

rollback;

select '31/31 profile permission checks passed; transaction rolled back' as result;
