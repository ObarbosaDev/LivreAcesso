-- Matriz transacional do BL-05. Todos os registros e perfis auxiliares são
-- sintéticos e desaparecem no ROLLBACK final.
begin;

create temporary table test_enrollment_operator on commit drop as
select id from public.profiles where role = 'coordinator' and active;
grant select on table pg_temp.test_enrollment_operator to authenticated;

do $guard$
begin
    if (select count(*) from pg_temp.test_enrollment_operator) <> 1 then
        raise exception 'enrollment_matrix_requires_one_active_coordinator';
    end if;
end;
$guard$;

insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
    raw_app_meta_data, raw_user_meta_data, created_at, updated_at
) values (
    '00000000-0000-0000-0000-000000000000',
    '00000000-0000-4000-8000-000000000910',
    'authenticated', 'authenticated', 'instrutor.bl05@livreacesso.test', '', now(),
    '{"provider":"email","providers":["email"]}'::jsonb,
    '{"full_name":"Instrutor Sintético BL-05"}'::jsonb, now(), now()
);
update public.profiles set role = 'instructor', active = true
where id = '00000000-0000-4000-8000-000000000910';

select set_config('request.jwt.claim.sub', (select id::text from pg_temp.test_enrollment_operator), true);
select set_config('request.jwt.claim.role', 'authenticated', true);
set local role authenticated;

do $setup$
declare
    v_modality jsonb;
    v_class jsonb;
begin
    v_modality := public.create_modality(
        '00000000-0000-4000-8000-000000000911', gen_random_uuid(),
        'Modalidade BL-05', 'Homologação de matrículas'
    );
    v_class := public.create_class(
        '00000000-0000-4000-8000-000000000912', gen_random_uuid(),
        '00000000-0000-4000-8000-000000000911', 'Turma BL-05', 1,
        'Sala de testes', null, null,
        '[{"weekday":"monday","starts_at":"14:00","ends_at":"15:00"}]'::jsonb,
        array['00000000-0000-4000-8000-000000000910']::uuid[]
    );
    if v_modality->>'id' <> '00000000-0000-4000-8000-000000000911'
       or v_class->>'id' <> '00000000-0000-4000-8000-000000000912' then
        raise exception 'catalog_setup_contract_invalid';
    end if;
end;
$setup$;

select public.register_student_with_guardian_v2(
    '00000000-0000-4000-8000-000000000913', gen_random_uuid(), gen_random_uuid(),
    'Estudante Sintético BL-05', '52998224725', date '2015-05-10',
    'Responsável Sintético', '61999991234', null, 'responsible_contact'
);
select public.register_student_with_guardian_v2(
    '00000000-0000-4000-8000-000000000915', gen_random_uuid(), gen_random_uuid(),
    'Segundo Estudante Sintético BL-05', '11144477735', date '2014-06-12',
    'Segundo Responsável Sintético', '61999991235', null, 'responsible_contact'
);

do $lifecycle$
declare
    v_result jsonb;
    v_version timestamptz;
begin
    v_result := public.register_enrollment(
        '00000000-0000-4000-8000-000000000914',
        '00000000-0000-4000-8000-000000000913',
        '00000000-0000-4000-8000-000000000912', gen_random_uuid()
    );
    if v_result->>'status' <> 'ativa' then raise exception 'enrollment_not_active'; end if;
    v_version := (v_result->>'updated_at')::timestamptz;

    begin
        perform public.register_enrollment(gen_random_uuid(), '00000000-0000-4000-8000-000000000913', '00000000-0000-4000-8000-000000000912', gen_random_uuid());
        raise exception 'duplicate_enrollment_was_allowed';
    exception when unique_violation then null;
    end;

    begin
        perform public.register_enrollment(gen_random_uuid(), '00000000-0000-4000-8000-000000000915', '00000000-0000-4000-8000-000000000912', gen_random_uuid());
        raise exception 'capacity_was_not_checked';
    exception when raise_exception then
        if sqlerrm <> 'class_capacity_reached' then raise; end if;
    end;

    v_result := public.change_enrollment_status(
        '00000000-0000-4000-8000-000000000914', 'cancelada', v_version,
        'Cancelamento sintético aprovado pela coordenação', gen_random_uuid()
    );
    if v_result->>'status' <> 'cancelada' then raise exception 'cancellation_failed'; end if;
    v_version := (v_result->>'updated_at')::timestamptz;
    v_result := public.change_enrollment_status(
        '00000000-0000-4000-8000-000000000914', 'ativa', v_version,
        'Reativação sintética aprovada pela coordenação', gen_random_uuid()
    );
    if v_result->>'status' <> 'ativa' then raise exception 'reactivation_failed'; end if;
    v_version := (v_result->>'updated_at')::timestamptz;
    begin
        perform public.change_enrollment_status('00000000-0000-4000-8000-000000000914', 'cancelada', v_version - interval '1 second', 'Conflito sintético de versão', gen_random_uuid());
        raise exception 'stale_version_was_allowed';
    exception when sqlstate '40001' then
        null;
    end;
end;
$lifecycle$;

-- A matrícula respeita a mesma matriz de papéis do catálogo: recepção pode
-- cadastrar, consulta e instrutor podem consultar, e somente coordenação muda
-- status. O perfil é alternado apenas dentro da transação desta matriz.
set local role postgres;
update public.profiles
set role = 'receptionist', active = true
where id = (select id from pg_temp.test_enrollment_operator);
set local role authenticated;
do $reception$
begin
    begin
        perform public.change_enrollment_status(
            '00000000-0000-4000-8000-000000000914', 'cancelada', now(),
            'Recepção não deve alterar status', gen_random_uuid()
        );
        raise exception 'receptionist_status_change_was_allowed';
    exception when sqlstate '42501' then null;
    end;
end;
$reception$;

set local role postgres;
update public.profiles
set role = 'read_only', active = true
where id = (select id from pg_temp.test_enrollment_operator);
set local role authenticated;
do $readonly$
begin
    if public.get_enrollment('00000000-0000-4000-8000-000000000914')->>'status' <> 'ativa' then
        raise exception 'read_only_could_not_read_enrollment';
    end if;
end;
$readonly$;

set local role postgres;
update public.profiles
set role = 'instructor', active = true
where id = (select id from pg_temp.test_enrollment_operator);
set local role postgres;
insert into public.class_instructors (class_id, instructor_id, created_by)
values (
    '00000000-0000-4000-8000-000000000912',
    (select id from pg_temp.test_enrollment_operator),
    (select id from pg_temp.test_enrollment_operator)
);
set local role authenticated;
set local role authenticated;
do $instructor$
begin
    if public.get_active_enrollment(
        '00000000-0000-4000-8000-000000000913',
        '00000000-0000-4000-8000-000000000912'
    ) is null then
        raise exception 'instructor_could_not_read_enrollment';
    end if;
end;
$instructor$;

set local role postgres;
update public.profiles
set role = 'pending', active = false
where id = (select id from pg_temp.test_enrollment_operator);
set local role authenticated;
do $pending$
begin
    begin
        perform public.get_enrollment('00000000-0000-4000-8000-000000000914');
        raise exception 'pending_read_was_allowed';
    exception when sqlstate '42501' then null;
    end;
end;
$pending$;

select '8/8 permission checks passed; transaction rolled back' as result;
rollback;
