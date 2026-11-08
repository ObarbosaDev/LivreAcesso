-- Torna CPF, data de nascimento e responsável opcionais no cadastro do aluno.
-- Apenas o nome completo continua obrigatório para salvar; os demais dados
-- podem ser completados depois, em telas próprias (edição e gestão de
-- responsáveis), sem bloquear o cadastro inicial.

begin;

alter table public.students
    alter column cpf drop not null,
    alter column birth_date drop not null;

alter table public.students
    drop constraint students_cpf_digits,
    add constraint students_cpf_digits check (
        cpf is null or (cpf ~ '^[0-9]{11}$' and private.is_valid_cpf(cpf))
    );

alter table public.students
    drop constraint students_birth_date_range,
    add constraint students_birth_date_range check (
        birth_date is null
        or (birth_date >= date '1900-01-01' and birth_date < current_date)
    );

-- O gatilho exigia responsável principal ativo para todo aluno. Agora só
-- exige isso quando já existe algum vínculo cadastrado: um aluno sem nenhum
-- responsável vinculado é um estado válido, aguardando complemento futuro.
create or replace function private.ensure_student_has_primary_guardian()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_student_id uuid;
begin
    v_student_id := case when tg_op = 'DELETE' then old.student_id else new.student_id end;

    if exists (select 1 from public.students where id = v_student_id)
       and exists (
           select 1 from public.student_guardians where student_id = v_student_id
       )
       and not exists (
           select 1
           from public.student_guardians
           where student_id = v_student_id
             and active
             and is_primary
       ) then
        raise exception using errcode = '23514', message = 'primary_guardian_required';
    end if;
    return null;
end;
$$;

-- Cadastro com responsável e CPF/data de nascimento totalmente opcionais.
-- Quando o nome do responsável e o telefone não são informados, nenhum
-- responsável é criado nem vinculado ao aluno.
create or replace function public.register_student_with_guardian(
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
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor_id uuid := auth.uid();
    v_student_id uuid;
    v_guardian_id uuid;
    v_constraint_name text;
    v_cpf text := nullif(regexp_replace(coalesce(p_cpf, ''), '[^0-9]', '', 'g'), '');
    v_phone text := nullif(regexp_replace(coalesce(p_guardian_phone, ''), '[^0-9]', '', 'g'), '');
    v_student_name text := btrim(coalesce(p_full_name, ''));
    v_guardian_name text := nullif(btrim(coalesce(p_guardian_full_name, '')), '');
    v_guardian_email text := nullif(lower(btrim(p_guardian_email)), '');
    v_has_guardian boolean := v_guardian_name is not null or v_phone is not null;
    v_changed_fields text[] := array['full_name'];
begin
    if p_student_id is null or p_guardian_id is null or p_request_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;

    if not private.has_any_role(
        array['coordinator', 'receptionist']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    if char_length(v_student_name) not between 3 and 120 then
        raise exception using errcode = '22023', message = 'invalid_student_name';
    end if;
    if v_cpf is not null and not private.is_valid_cpf(v_cpf) then
        raise exception using errcode = '22023', message = 'invalid_cpf';
    end if;
    if p_birth_date is not null
       and (p_birth_date < date '1900-01-01' or p_birth_date >= current_date) then
        raise exception using errcode = '22023', message = 'invalid_birth_date';
    end if;
    if v_has_guardian then
        if v_guardian_name is null or char_length(v_guardian_name) not between 3 and 120 then
            raise exception using errcode = '22023', message = 'invalid_guardian_name';
        end if;
        if v_phone !~ '^[0-9]{10,11}$' then
            raise exception using errcode = '22023', message = 'invalid_phone_format';
        end if;
    end if;
    if v_guardian_email is not null
       and (
           char_length(v_guardian_email) > 254
           or v_guardian_email !~* '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
       ) then
        raise exception using errcode = '22023', message = 'invalid_email';
    end if;

    if v_cpf is not null then
        v_changed_fields := array_append(v_changed_fields, 'cpf');
    end if;
    if p_birth_date is not null then
        v_changed_fields := array_append(v_changed_fields, 'birth_date');
    end if;
    if v_has_guardian then
        v_changed_fields := array_append(v_changed_fields, 'guardian');
    end if;

    begin
        insert into public.students (
            id,
            full_name,
            cpf,
            birth_date,
            status,
            created_by
        )
        values (
            p_student_id,
            v_student_name,
            v_cpf,
            p_birth_date,
            'active',
            v_actor_id
        )
        returning id into v_student_id;
    exception
        when unique_violation then
            get stacked diagnostics v_constraint_name = constraint_name;
            if v_constraint_name = 'students_cpf_unique' then
                -- Somente a constraint de CPF pode virar conflito cadastral.
                -- Colisão de UUID ou outra integridade continua sendo erro técnico.
                raise exception using errcode = '23505', message = 'duplicate_cpf';
            end if;
            raise;
    end;

    if v_has_guardian then
        insert into public.guardians (
            id,
            full_name,
            phone,
            email,
            created_by
        )
        values (
            p_guardian_id,
            v_guardian_name,
            v_phone,
            v_guardian_email,
            v_actor_id
        )
        returning id into v_guardian_id;

        insert into public.student_guardians (
            student_id,
            guardian_id,
            relationship,
            is_primary,
            receives_communications,
            created_by
        )
        values (
            v_student_id,
            v_guardian_id,
            p_relationship,
            true,
            true,
            v_actor_id
        );
    end if;

    -- A auditoria registra somente a ação e os campos envolvidos. Os valores
    -- pessoais permanecem nas tabelas protegidas e não são duplicados no log.
    insert into private.audit_entries (
        actor_id,
        action,
        entity_type,
        entity_id,
        changed_fields,
        request_id
    )
    values (
        v_actor_id,
        'student.registered',
        'student',
        v_student_id,
        v_changed_fields,
        p_request_id
    );

    -- O evento durável carrega apenas o ID. Qualquer listener futuro deverá
    -- buscar dados usando suas próprias permissões e finalidade autorizada.
    insert into private.outbox_events (
        event_type,
        aggregate_type,
        aggregate_id,
        payload
    )
    values (
        'StudentRegistered',
        'Student',
        v_student_id,
        jsonb_build_object('student_id', v_student_id)
    );

    return v_student_id;
end;
$$;

comment on function public.register_student_with_guardian(
    uuid, uuid, uuid, text, text, date, text, text, text, public.guardian_relationship
) is 'Cadastra aluno com CPF, data de nascimento e responsável opcionais.';

-- Detalhe do aluno com responsável opcional: um aluno sem contato vinculado
-- continua sendo consultável, apenas com "guardian" nulo na resposta.
create or replace function public.get_student_detail(
    p_student_id uuid,
    p_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_result jsonb;
begin
    if p_student_id is null or p_request_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(
        array['coordinator', 'receptionist']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    select jsonb_build_object(
        'id', student.id,
        'full_name', student.full_name,
        'cpf', student.cpf,
        'birth_date', student.birth_date,
        'status', student.status,
        'guardian', case
            when guardian.id is null then null
            else jsonb_build_object(
                'id', guardian.id,
                'full_name', guardian.full_name,
                'phone', guardian.phone,
                'email', guardian.email
            )
        end,
        'created_at', student.created_at,
        'updated_at', student.updated_at
    )
    into v_result
    from public.students as student
    left join public.student_guardians as relationship
        on relationship.student_id = student.id
       and relationship.is_primary
       and relationship.active
    left join public.guardians as guardian
        on guardian.id = relationship.guardian_id
    where student.id = p_student_id;

    if v_result is null then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;

    -- A leitura libera telefone e e-mail completos para a rotina autorizada.
    -- Registramos a finalidade sem duplicar os valores pessoais consultados.
    insert into private.audit_entries (
        actor_id,
        action,
        entity_type,
        entity_id,
        changed_fields,
        request_id
    )
    values (
        auth.uid(),
        'student.sensitive_viewed',
        'student',
        p_student_id,
        array[]::text[],
        p_request_id
    );

    return v_result;
end;
$$;

comment on function public.get_student_detail(uuid, uuid) is
    'Retorna cadastro e contato (quando houver) após autorização e registra a leitura.';

-- Listagem com CPF e idade nulos quando o aluno não tiver esses dados.
drop function if exists public.list_students(
    public.student_status, public.institute_unit, uuid, text, integer, integer
);

create or replace function public.list_students(
    p_status public.student_status default null,
    p_unit public.institute_unit default null,
    p_modality_id uuid default null,
    p_query text default null,
    p_limit integer default 25,
    p_offset integer default 0
)
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
        array['coordinator', 'receptionist', 'read_only']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if p_limit is not null and (p_limit < 1 or p_limit > 100) then
        raise exception using errcode = '22023', message = 'invalid_page_size';
    end if;
    if p_offset is not null and p_offset < 0 then
        raise exception using errcode = '22023', message = 'invalid_offset';
    end if;
    if p_query is not null
       and btrim(p_query) <> ''
       and char_length(btrim(p_query)) not between 2 and 120 then
        raise exception using errcode = '22023', message = 'invalid_query';
    end if;

    with filtered as materialized (
        select
            student.id,
            student.full_name,
            case
                when student.cpf is null then null
                else '***.***.***-' || right(student.cpf, 2)
            end as cpf_masked,
            student.birth_date,
            case
                when student.birth_date is null then null
                else extract(year from age(current_date, student.birth_date))::integer
            end as age,
            student.status,
            guardian.full_name as guardian_name,
            case
                when guardian.phone is null then null
                else '(' || left(guardian.phone, 2) || ') *****-' || right(guardian.phone, 4)
            end as guardian_phone_masked,
            student.created_at,
            student.updated_at,
            extensions.unaccent(lower(student.full_name)) as sort_name
        from public.students as student
        left join public.student_guardians as relationship
            on relationship.student_id = student.id
           and relationship.is_primary
           and relationship.active
        left join public.guardians as guardian
            on guardian.id = relationship.guardian_id
        where (p_status is null or student.status = p_status)
          and (
              p_query is null
              or btrim(p_query) = ''
              or strpos(
                  extensions.unaccent(lower(student.full_name)),
                  extensions.unaccent(lower(btrim(p_query)))
              ) > 0
          )
          and (
              (p_unit is null and p_modality_id is null)
              or exists (
                  select 1
                  from public.enrollments as enrollment
                  join public.classes as class_record on class_record.id = enrollment.class_id
                  where enrollment.student_id = student.id
                    and enrollment.status = 'ativa'
                    and (p_unit is null or class_record.unit = p_unit)
                    and (p_modality_id is null or class_record.modality_id = p_modality_id)
              )
          )
    ),
    page_items as (
        select *
        from filtered
        order by sort_name, id
        limit coalesce(p_limit, 25)
        offset coalesce(p_offset, 0)
    )
    select jsonb_build_object(
        'items', coalesce(
            (
                select jsonb_agg(
                    jsonb_build_object(
                        'id', item.id,
                        'full_name', item.full_name,
                        'cpf_masked', item.cpf_masked,
                        'birth_date', item.birth_date,
                        'age', item.age,
                        'status', item.status,
                        'guardian_name', item.guardian_name,
                        'guardian_phone_masked', item.guardian_phone_masked,
                        'created_at', item.created_at,
                        'updated_at', item.updated_at
                    )
                    order by item.sort_name, item.id
                )
                from page_items as item
            ),
            '[]'::jsonb
        ),
        'total', (select count(*) from filtered)
    )
    into v_result;

    return v_result;
end;
$$;

revoke all on function public.list_students(
    public.student_status, public.institute_unit, uuid, text, integer, integer
) from public, anon;
grant execute on function public.list_students(
    public.student_status, public.institute_unit, uuid, text, integer, integer
) to authenticated;

commit;
