-- Gerenciamento seguro do cadastro de alunos.
-- Esta migration não altera CPF e não implementa exclusão física.

begin;

create table private.student_status_history (
    id bigint generated always as identity primary key,
    student_id uuid not null references public.students (id) on delete restrict,
    previous_status public.student_status not null,
    current_status public.student_status not null,
    reason text not null,
    actor_id uuid references auth.users (id) on delete set null,
    request_id uuid not null,
    occurred_at timestamptz not null default now(),
    constraint student_status_history_transition check (previous_status <> current_status),
    constraint student_status_history_reason_length check (
        char_length(btrim(reason)) between 10 and 500
    )
);

comment on table private.student_status_history is
    'Histórico protegido de ativação/desativação com motivo e autoria.';
comment on column private.student_status_history.reason is
    'Texto potencialmente sensível; nunca deve ser copiado para logs ou eventos.';

create index student_status_history_student_idx
    on private.student_status_history (student_id, occurred_at desc);

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
        'guardian', jsonb_build_object(
            'id', guardian.id,
            'full_name', guardian.full_name,
            'phone', guardian.phone,
            'email', guardian.email
        ),
        'created_at', student.created_at,
        'updated_at', student.updated_at
    )
    into v_result
    from public.students as student
    join public.student_guardians as relationship
        on relationship.student_id = student.id
       and relationship.is_primary
    join public.guardians as guardian
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
    'Retorna cadastro e contato completo após autorização e registra a leitura.';
revoke all on function public.get_student_detail(uuid, uuid) from public, anon;
grant execute on function public.get_student_detail(uuid, uuid) to authenticated;

create or replace function public.update_student_with_guardian(
    p_student_id uuid,
    p_request_id uuid,
    p_expected_updated_at timestamptz,
    p_full_name text,
    p_birth_date date,
    p_guardian_full_name text,
    p_guardian_phone text,
    p_guardian_email text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor_id uuid := auth.uid();
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_guardian_id uuid;
    v_student_name text := btrim(coalesce(p_full_name, ''));
    v_guardian_name text := btrim(coalesce(p_guardian_full_name, ''));
    v_phone text := regexp_replace(coalesce(p_guardian_phone, ''), '[^0-9]', '', 'g');
    v_email text := nullif(lower(btrim(p_guardian_email)), '');
begin
    if p_student_id is null or p_request_id is null or p_expected_updated_at is null then
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
    if char_length(v_guardian_name) not between 3 and 120 then
        raise exception using errcode = '22023', message = 'invalid_guardian_name';
    end if;
    if v_phone !~ '^[0-9]{10,11}$' then
        raise exception using errcode = '22023', message = 'invalid_phone';
    end if;
    if p_birth_date is null
       or p_birth_date < date '1900-01-01'
       or p_birth_date >= current_date then
        raise exception using errcode = '22023', message = 'invalid_birth_date';
    end if;
    if v_email is not null
       and (
           char_length(v_email) > 254
           or v_email !~* '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
       ) then
        raise exception using errcode = '22023', message = 'invalid_email';
    end if;

    select student.updated_at, relationship.guardian_id
    into v_current_updated_at, v_guardian_id
    from public.students as student
    left join public.student_guardians as relationship
        on relationship.student_id = student.id
       and relationship.is_primary
    where student.id = p_student_id
    for update of student;

    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    if v_guardian_id is null then
        raise exception using errcode = 'P0002', message = 'primary_guardian_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'student_version_conflict';
    end if;

    update public.students
    set full_name = v_student_name,
        birth_date = p_birth_date
    where id = p_student_id
    returning updated_at into v_updated_at;

    update public.guardians
    set full_name = v_guardian_name,
        phone = v_phone,
        email = v_email
    where id = v_guardian_id;

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
        'student.updated',
        'student',
        p_student_id,
        array['full_name', 'birth_date', 'guardian'],
        p_request_id
    );

    insert into private.outbox_events (
        event_type,
        aggregate_type,
        aggregate_id,
        payload
    )
    values (
        'StudentUpdated',
        'Student',
        p_student_id,
        jsonb_build_object('student_id', p_student_id)
    );

    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

comment on function public.update_student_with_guardian(
    uuid, uuid, timestamptz, text, date, text, text, text
) is 'Atualiza aluno e responsável principal com concorrência otimista e auditoria.';
revoke all on function public.update_student_with_guardian(
    uuid, uuid, timestamptz, text, date, text, text, text
) from public, anon;
grant execute on function public.update_student_with_guardian(
    uuid, uuid, timestamptz, text, date, text, text, text
) to authenticated;

create or replace function public.change_student_status(
    p_student_id uuid,
    p_request_id uuid,
    p_expected_updated_at timestamptz,
    p_target_status public.student_status,
    p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor_id uuid := auth.uid();
    v_previous_status public.student_status;
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_reason text := btrim(coalesce(p_reason, ''));
begin
    if p_student_id is null or p_request_id is null or p_expected_updated_at is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    -- Alterar o ciclo cadastral afeta todos os módulos futuros. Apenas a
    -- coordenação toma essa decisão; alertas nunca chamam esta função sozinhos.
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if char_length(v_reason) not between 10 and 500 then
        raise exception using errcode = '22023', message = 'invalid_status_reason';
    end if;

    select status, updated_at
    into v_previous_status, v_current_updated_at
    from public.students
    where id = p_student_id
    for update;

    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'student_version_conflict';
    end if;
    if v_previous_status = p_target_status then
        return jsonb_build_object('updated_at', v_current_updated_at);
    end if;

    update public.students
    set status = p_target_status
    where id = p_student_id
    returning updated_at into v_updated_at;

    insert into private.student_status_history (
        student_id,
        previous_status,
        current_status,
        reason,
        actor_id,
        request_id
    )
    values (
        p_student_id,
        v_previous_status,
        p_target_status,
        v_reason,
        v_actor_id,
        p_request_id
    );

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
        'student.status_changed',
        'student',
        p_student_id,
        array['status'],
        p_request_id
    );

    -- O motivo fica somente no histórico protegido. O evento informa apenas a
    -- transição necessária para projeções e integrações futuras.
    insert into private.outbox_events (
        event_type,
        aggregate_type,
        aggregate_id,
        payload
    )
    values (
        'StudentStatusChanged',
        'Student',
        p_student_id,
        jsonb_build_object(
            'student_id', p_student_id,
            'previous_status', v_previous_status,
            'current_status', p_target_status
        )
    );

    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

comment on function public.change_student_status(
    uuid, uuid, timestamptz, public.student_status, text
) is 'Ativa ou desativa cadastro com motivo protegido, versão e autorização.';
revoke all on function public.change_student_status(
    uuid, uuid, timestamptz, public.student_status, text
) from public, anon;
grant execute on function public.change_student_status(
    uuid, uuid, timestamptz, public.student_status, text
) to authenticated;

-- A listagem inclui a versão usada na futura edição, sem liberar contato integral.
create or replace function public.list_students(
    p_status public.student_status default null,
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
            '***.***.***-' || right(student.cpf, 2) as cpf_masked,
            student.birth_date,
            extract(year from age(current_date, student.birth_date))::integer as age,
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
    public.student_status, text, integer, integer
) from public, anon;
grant execute on function public.list_students(
    public.student_status, text, integer, integer
) to authenticated;

revoke all on all tables in schema private from public, anon, authenticated;
revoke all on sequence private.student_status_history_id_seq from public, anon, authenticated;

commit;
