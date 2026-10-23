-- Matriz transacional de modalidades, turmas e isolamento de instrutores.
-- Cria somente registros sintéticos e reverte inclusive o usuário Auth auxiliar.

begin;

create temporary table test_class_operator on commit drop as
select id
from public.profiles
where role = 'coordinator'
  and active;

grant select on table pg_temp.test_class_operator to authenticated;

do $guard$
begin
    if (select count(*) from pg_temp.test_class_operator) <> 1 then
        raise exception 'class_matrix_requires_one_active_coordinator';
    end if;
end;
$guard$;

-- O instrutor auxiliar existe apenas na transação. O trigger normal cria seu
-- perfil pendente; a matriz então o promove para testar as mesmas constraints.
insert into auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at
)
values (
    '00000000-0000-0000-0000-000000000000',
    '00000000-0000-4000-8000-000000000409',
    'authenticated',
    'authenticated',
    'instrutor.bl04@livreacesso.test',
    '',
    now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{"full_name":"Instrutora Sintética BL-04"}'::jsonb,
    now(),
    now()
);

update public.profiles
set role = 'instructor', active = true
where id = '00000000-0000-4000-8000-000000000409';

select set_config(
    'request.jwt.claim.sub',
    (select id::text from pg_temp.test_class_operator),
    true
);
select set_config('request.jwt.claim.role', 'authenticated', true);

-- Primeiro exercitamos CRUD real sob coordenação. Falhas esperadas usam
-- subtransações PL/pgSQL e não deixam escrita parcial no cenário principal.
set local role authenticated;
do $lifecycle$
declare
    v_modality_id constant uuid := '00000000-0000-4000-8000-000000000401';
    v_class_id constant uuid := '00000000-0000-4000-8000-000000000402';
    v_second_class_id constant uuid := '00000000-0000-4000-8000-000000000403';
    v_instructor_id constant uuid := '00000000-0000-4000-8000-000000000409';
    v_modality_version timestamptz;
    v_class_version timestamptz;
    v_result jsonb;
begin
    v_result := public.create_modality(
        v_modality_id,
        gen_random_uuid(),
        'Capoeira',
        'Atividade corporal e cultural'
    );
    v_modality_version := (v_result ->> 'updated_at')::timestamptz;

    begin
        perform public.create_modality(
            gen_random_uuid(),
            gen_random_uuid(),
            'capoeíra',
            null
        );
        raise exception 'normalized_modality_duplicate_was_allowed';
    exception
        when unique_violation then
            null;
    end;

    v_result := public.create_class(
        v_class_id,
        gen_random_uuid(),
        v_modality_id,
        'Turma Infantil A',
        20,
        'Sala 1',
        7,
        12,
        '[{"weekday":"monday","starts_at":"14:00","ends_at":"15:00"},
          {"weekday":"wednesday","starts_at":"14:00","ends_at":"15:00"}]'::jsonb,
        array[v_instructor_id]
    );
    v_class_version := (v_result ->> 'updated_at')::timestamptz;
    if jsonb_array_length(v_result -> 'schedules') <> 2
       or jsonb_array_length(v_result -> 'instructors') <> 1 then
        raise exception 'created_class_contract_is_invalid';
    end if;

    begin
        perform public.create_class(
            gen_random_uuid(),
            gen_random_uuid(),
            v_modality_id,
            'turma infantil á',
            20,
            'Sala 2',
            null,
            null,
            '[{"weekday":"friday","starts_at":"09:00","ends_at":"10:00"}]'::jsonb,
            array[v_instructor_id]
        );
        raise exception 'normalized_class_duplicate_was_allowed';
    exception
        when unique_violation then
            null;
    end;

    begin
        perform public.update_class(
            v_class_id,
            gen_random_uuid(),
            v_class_version,
            v_modality_id,
            'Turma Infantil A',
            24,
            'Quadra coberta',
            7,
            12,
            '[{"weekday":"monday","starts_at":"14:00","ends_at":"15:30"},
              {"weekday":"monday","starts_at":"15:00","ends_at":"16:00"}]'::jsonb,
            array[v_instructor_id]
        );
        raise exception 'overlapping_schedule_was_allowed';
    exception
        when check_violation then
            null;
    end;

    v_result := public.update_class(
        v_class_id,
        gen_random_uuid(),
        v_class_version,
        v_modality_id,
        'Turma Infantil A',
        24,
        'Quadra coberta',
        7,
        12,
        '[{"weekday":"monday","starts_at":"14:00","ends_at":"15:00"},
          {"weekday":"wednesday","starts_at":"14:00","ends_at":"15:00"}]'::jsonb,
        array[v_instructor_id]
    );
    v_class_version := (v_result ->> 'updated_at')::timestamptz;

    begin
        perform public.change_modality_activation(
            v_modality_id,
            gen_random_uuid(),
            v_modality_version,
            false,
            'Pausa sintética confirmada pela coordenação'
        );
        raise exception 'active_modality_was_deactivated';
    exception
        when check_violation then
            null;
    end;

    v_result := public.change_class_activation(
        v_class_id,
        gen_random_uuid(),
        v_class_version,
        false,
        'Pausa sintética confirmada pela coordenação'
    );
    v_class_version := (v_result ->> 'updated_at')::timestamptz;
    v_result := public.change_modality_activation(
        v_modality_id,
        gen_random_uuid(),
        v_modality_version,
        false,
        'Pausa sintética confirmada pela coordenação'
    );
    v_modality_version := (v_result ->> 'updated_at')::timestamptz;
    v_result := public.change_modality_activation(
        v_modality_id,
        gen_random_uuid(),
        v_modality_version,
        true,
        'Retorno sintético confirmado pela coordenação'
    );
    v_modality_version := (v_result ->> 'updated_at')::timestamptz;
    perform public.change_class_activation(
        v_class_id,
        gen_random_uuid(),
        v_class_version,
        true,
        'Retorno sintético confirmado pela coordenação'
    );

    perform public.create_class(
        v_second_class_id,
        gen_random_uuid(),
        v_modality_id,
        'Turma Juvenil B',
        18,
        'Sala 2',
        13,
        17,
        '[{"weekday":"tuesday","starts_at":"16:00","ends_at":"17:00"}]'::jsonb,
        array[v_instructor_id]
    );

    v_result := public.list_classes(true, v_modality_id, null, 25, 0);
    if (v_result ->> 'total')::integer <> 2 then
        raise exception 'class_list_total_is_invalid';
    end if;
end;
$lifecycle$;
reset role;

-- A atribuição direta prepara a identidade existente para o teste de escopo.
-- A turma continua com o instrutor sintético válido usado no CRUD real.
insert into public.class_instructors (class_id, instructor_id, created_by)
values (
    '00000000-0000-4000-8000-000000000402',
    (select id from pg_temp.test_class_operator),
    (select id from pg_temp.test_class_operator)
);

create or replace function pg_temp.expect_class_sqlstate(
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
                raise exception 'class_matrix_failure:%:expected:%:received:%',
                    p_label,
                    p_expected_sqlstate,
                    sqlstate;
            end if;
    end;
end;
$$;

grant execute on function pg_temp.expect_class_sqlstate(text, text, text)
to authenticated;

-- Coordenação lê e administra todas as dez operações.
update public.profiles
set role = 'coordinator', active = true
where id = (select id from pg_temp.test_class_operator);
set local role authenticated;
select pg_temp.expect_class_sqlstate(
    'coordinator.modality_list',
    'select public.list_modalities(null, null, 25, 0)',
    '00000'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.modality_get',
    $$select public.get_modality('00000000-0000-4000-8000-000000000401')$$,
    '00000'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.modality_create',
    $$select public.create_modality(gen_random_uuid(), gen_random_uuid(), 'x', null)$$,
    '22023'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.modality_update',
    $$select public.update_modality(
        gen_random_uuid(), gen_random_uuid(), now(), 'Modalidade Sintética', null
    )$$,
    'P0002'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.modality_activation',
    $$select public.change_modality_activation(
        gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido'
    )$$,
    'P0002'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.class_list',
    'select public.list_classes(null, null, null, 25, 0)',
    '00000'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.class_get',
    $$select public.get_class('00000000-0000-4000-8000-000000000402')$$,
    '00000'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.class_create',
    $$select public.create_class(
        gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 'Turma Sintética', 20,
        'Sala 1', null, null,
        '[{"weekday":"monday","starts_at":"09:00","ends_at":"10:00"}]'::jsonb,
        array['00000000-0000-4000-8000-000000000409'::uuid]
    )$$,
    'P0002'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.class_update',
    $$select public.update_class(
        gen_random_uuid(), gen_random_uuid(), now(), gen_random_uuid(), 'Turma Sintética',
        20, 'Sala 1', null, null,
        '[{"weekday":"monday","starts_at":"09:00","ends_at":"10:00"}]'::jsonb,
        array['00000000-0000-4000-8000-000000000409'::uuid]
    )$$,
    'P0002'
);
select pg_temp.expect_class_sqlstate(
    'coordinator.class_activation',
    $$select public.change_class_activation(
        gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido'
    )$$,
    'P0002'
);
reset role;

-- Recepção consulta catálogo completo, sem alterar configuração.
update public.profiles
set role = 'receptionist', active = true
where id = (select id from pg_temp.test_class_operator);
set local role authenticated;
select pg_temp.expect_class_sqlstate('receptionist.modality_list', 'select public.list_modalities(null, null, 25, 0)', '00000');
select pg_temp.expect_class_sqlstate('receptionist.modality_get', $$select public.get_modality('00000000-0000-4000-8000-000000000401')$$, '00000');
select pg_temp.expect_class_sqlstate('receptionist.modality_create', $$select public.create_modality(gen_random_uuid(), gen_random_uuid(), 'Modalidade Sintética', null)$$, '42501');
select pg_temp.expect_class_sqlstate('receptionist.modality_update', $$select public.update_modality(gen_random_uuid(), gen_random_uuid(), now(), 'Modalidade Sintética', null)$$, '42501');
select pg_temp.expect_class_sqlstate('receptionist.modality_activation', $$select public.change_modality_activation(gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido')$$, '42501');
select pg_temp.expect_class_sqlstate('receptionist.class_list', 'select public.list_classes(null, null, null, 25, 0)', '00000');
select pg_temp.expect_class_sqlstate('receptionist.class_get', $$select public.get_class('00000000-0000-4000-8000-000000000402')$$, '00000');
select pg_temp.expect_class_sqlstate('receptionist.class_create', $$select public.create_class(gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 'Turma Sintética', 20, 'Sala 1', null, null, '[]'::jsonb, array[]::uuid[])$$, '42501');
select pg_temp.expect_class_sqlstate('receptionist.class_update', $$select public.update_class(gen_random_uuid(), gen_random_uuid(), now(), gen_random_uuid(), 'Turma Sintética', 20, 'Sala 1', null, null, '[]'::jsonb, array[]::uuid[])$$, '42501');
select pg_temp.expect_class_sqlstate('receptionist.class_activation', $$select public.change_class_activation(gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido')$$, '42501');
reset role;

-- Consulta possui as mesmas leituras, sem qualquer mutação.
update public.profiles
set role = 'read_only', active = true
where id = (select id from pg_temp.test_class_operator);
set local role authenticated;
select pg_temp.expect_class_sqlstate('read_only.modality_list', 'select public.list_modalities(null, null, 25, 0)', '00000');
select pg_temp.expect_class_sqlstate('read_only.modality_get', $$select public.get_modality('00000000-0000-4000-8000-000000000401')$$, '00000');
select pg_temp.expect_class_sqlstate('read_only.modality_create', $$select public.create_modality(gen_random_uuid(), gen_random_uuid(), 'Modalidade Sintética', null)$$, '42501');
select pg_temp.expect_class_sqlstate('read_only.modality_update', $$select public.update_modality(gen_random_uuid(), gen_random_uuid(), now(), 'Modalidade Sintética', null)$$, '42501');
select pg_temp.expect_class_sqlstate('read_only.modality_activation', $$select public.change_modality_activation(gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido')$$, '42501');
select pg_temp.expect_class_sqlstate('read_only.class_list', 'select public.list_classes(null, null, null, 25, 0)', '00000');
select pg_temp.expect_class_sqlstate('read_only.class_get', $$select public.get_class('00000000-0000-4000-8000-000000000402')$$, '00000');
select pg_temp.expect_class_sqlstate('read_only.class_create', $$select public.create_class(gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 'Turma Sintética', 20, 'Sala 1', null, null, '[]'::jsonb, array[]::uuid[])$$, '42501');
select pg_temp.expect_class_sqlstate('read_only.class_update', $$select public.update_class(gen_random_uuid(), gen_random_uuid(), now(), gen_random_uuid(), 'Turma Sintética', 20, 'Sala 1', null, null, '[]'::jsonb, array[]::uuid[])$$, '42501');
select pg_temp.expect_class_sqlstate('read_only.class_activation', $$select public.change_class_activation(gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido')$$, '42501');
reset role;

-- Instrutor lê modalidades e somente a turma explicitamente atribuída.
update public.profiles
set role = 'instructor', active = true
where id = (select id from pg_temp.test_class_operator);
set local role authenticated;
select pg_temp.expect_class_sqlstate('instructor.modality_list', 'select public.list_modalities(null, null, 25, 0)', '00000');
select pg_temp.expect_class_sqlstate('instructor.modality_get', $$select public.get_modality('00000000-0000-4000-8000-000000000401')$$, '00000');
select pg_temp.expect_class_sqlstate('instructor.modality_create', $$select public.create_modality(gen_random_uuid(), gen_random_uuid(), 'Modalidade Sintética', null)$$, '42501');
select pg_temp.expect_class_sqlstate('instructor.modality_update', $$select public.update_modality(gen_random_uuid(), gen_random_uuid(), now(), 'Modalidade Sintética', null)$$, '42501');
select pg_temp.expect_class_sqlstate('instructor.modality_activation', $$select public.change_modality_activation(gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido')$$, '42501');
select pg_temp.expect_class_sqlstate('instructor.class_list', 'select public.list_classes(null, null, null, 25, 0)', '00000');
select pg_temp.expect_class_sqlstate('instructor.class_get', $$select public.get_class('00000000-0000-4000-8000-000000000402')$$, '00000');
select pg_temp.expect_class_sqlstate('instructor.class_create', $$select public.create_class(gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 'Turma Sintética', 20, 'Sala 1', null, null, '[]'::jsonb, array[]::uuid[])$$, '42501');
select pg_temp.expect_class_sqlstate('instructor.class_update', $$select public.update_class(gen_random_uuid(), gen_random_uuid(), now(), gen_random_uuid(), 'Turma Sintética', 20, 'Sala 1', null, null, '[]'::jsonb, array[]::uuid[])$$, '42501');
select pg_temp.expect_class_sqlstate('instructor.class_activation', $$select public.change_class_activation(gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido')$$, '42501');
select pg_temp.expect_class_sqlstate(
    'instructor.other_class_hidden',
    $$select public.get_class('00000000-0000-4000-8000-000000000403')$$,
    'P0002'
);
do $scope$
declare
    v_result jsonb;
begin
    v_result := public.list_classes(null, null, null, 25, 0);
    if (v_result ->> 'total')::integer <> 1
       or (v_result -> 'items' -> 0 ->> 'id')::uuid
          <> '00000000-0000-4000-8000-000000000402'::uuid then
        raise exception 'instructor_scope_is_invalid';
    end if;
end;
$scope$;
reset role;

-- Perfil pendente/inativo não lê nem altera o catálogo.
update public.profiles
set role = 'pending', active = false
where id = (select id from pg_temp.test_class_operator);
set local role authenticated;
select pg_temp.expect_class_sqlstate('pending.modality_list', 'select public.list_modalities(null, null, 25, 0)', '42501');
select pg_temp.expect_class_sqlstate('pending.modality_get', $$select public.get_modality('00000000-0000-4000-8000-000000000401')$$, '42501');
select pg_temp.expect_class_sqlstate('pending.modality_create', $$select public.create_modality(gen_random_uuid(), gen_random_uuid(), 'Modalidade Sintética', null)$$, '42501');
select pg_temp.expect_class_sqlstate('pending.modality_update', $$select public.update_modality(gen_random_uuid(), gen_random_uuid(), now(), 'Modalidade Sintética', null)$$, '42501');
select pg_temp.expect_class_sqlstate('pending.modality_activation', $$select public.change_modality_activation(gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido')$$, '42501');
select pg_temp.expect_class_sqlstate('pending.class_list', 'select public.list_classes(null, null, null, 25, 0)', '42501');
select pg_temp.expect_class_sqlstate('pending.class_get', $$select public.get_class('00000000-0000-4000-8000-000000000402')$$, '42501');
select pg_temp.expect_class_sqlstate('pending.class_create', $$select public.create_class(gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 'Turma Sintética', 20, 'Sala 1', null, null, '[]'::jsonb, array[]::uuid[])$$, '42501');
select pg_temp.expect_class_sqlstate('pending.class_update', $$select public.update_class(gen_random_uuid(), gen_random_uuid(), now(), gen_random_uuid(), 'Turma Sintética', 20, 'Sala 1', null, null, '[]'::jsonb, array[]::uuid[])$$, '42501');
select pg_temp.expect_class_sqlstate('pending.class_activation', $$select public.change_class_activation(gen_random_uuid(), gen_random_uuid(), now(), false, 'Motivo sintético válido')$$, '42501');
reset role;

-- Inspeções internas usam o papel administrativo apenas para ler tabelas
-- privadas; nenhuma dessas leituras seria concedida ao cliente autenticado.
do $history$
begin
    if (select count(*) from private.catalog_change_history) < 8 then
        raise exception 'catalog_history_is_incomplete';
    end if;
    if (select count(*) from public.classes where active) <> 2 then
        raise exception 'class_lifecycle_did_not_finish_active';
    end if;
    if (select count(*) from public.class_schedules) <> 3 then
        raise exception 'class_schedule_count_is_invalid';
    end if;
end;
$history$;

rollback;

select '50/50 class permission checks passed; lifecycle and instructor scope passed; transaction rolled back' as result;
