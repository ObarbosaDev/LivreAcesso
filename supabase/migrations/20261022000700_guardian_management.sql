-- Gestão segura de múltiplos responsáveis e histórico cadastral do aluno.
-- Contatos podem ser compartilhados entre irmãos sem duplicação de dados pessoais.

begin;

-- A desvinculação é lógica: o relacionamento deixa de operar, mas permanece
-- disponível para auditoria e eventual revinculação explícita.
alter table public.student_guardians
    add column active boolean not null default true,
    add column ended_at timestamptz,
    add constraint student_guardians_primary_active check (not is_primary or active),
    add constraint student_guardians_active_period check (
        (active and ended_at is null)
        or (not active and ended_at is not null)
    );

comment on column public.student_guardians.active is
    'Vínculo operacional; false preserva histórico sem liberar contato ao aluno.';
comment on column public.student_guardians.ended_at is
    'Instante da desvinculação lógica; não representa exclusão do responsável.';

-- A unicidade considera somente vínculos ativos para permitir manter versões
-- antigas sem bloquear a escolha atual do contato principal.
drop index public.student_guardians_one_primary;
create unique index student_guardians_one_active_primary
    on public.student_guardians (student_id)
    where is_primary and active;

create table private.guardian_change_history (
    id bigint generated always as identity primary key,
    student_id uuid not null references public.students (id) on delete restrict,
    guardian_id uuid not null references public.guardians (id) on delete restrict,
    action text not null,
    changed_fields text[] not null default '{}',
    reason text,
    actor_id uuid references auth.users (id) on delete set null,
    request_id uuid not null,
    occurred_at timestamptz not null default now(),
    constraint guardian_change_history_action check (
        action in ('linked', 'relinked', 'updated', 'primary_changed', 'unlinked')
    ),
    constraint guardian_change_history_reason check (
        reason is null or char_length(btrim(reason)) between 10 and 500
    )
);

comment on table private.guardian_change_history is
    'Histórico privado de vínculos; registra campos e motivo, nunca valores pessoais.';
comment on column private.guardian_change_history.changed_fields is
    'Nomes técnicos dos campos alterados, sem telefone, e-mail ou nome.';
comment on column private.guardian_change_history.reason is
    'Justificativa potencialmente sensível, disponível somente no schema privado.';

create index guardian_change_history_student_idx
    on private.guardian_change_history (student_id, occurred_at desc);
create index guardian_change_history_guardian_idx
    on private.guardian_change_history (guardian_id, occurred_at desc);

-- Como as tabelas pessoais não possuem grants de escrita, esta constraint
-- diferida protege também operações administrativas feitas pelo SQL Editor.
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

revoke all on function private.ensure_student_has_primary_guardian()
from public, anon, authenticated;

create constraint trigger student_guardians_require_primary
after insert or update or delete on public.student_guardians
deferrable initially deferred
for each row execute function private.ensure_student_has_primary_guardian();

-- A projeção integral fica interna para que todas as mutações devolvam o mesmo
-- contrato. A versão do aluno protege o vínculo; a versão do responsável protege
-- o contato quando ele é compartilhado por mais de um aluno.
create or replace function private.student_guardian_detail(
    p_student_id uuid,
    p_guardian_id uuid
)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
    select jsonb_build_object(
        'student_id', student.id,
        'student_updated_at', student.updated_at,
        'id', guardian.id,
        'full_name', guardian.full_name,
        'phone', guardian.phone,
        'email', guardian.email,
        'relationship', relationship.relationship,
        'is_primary', relationship.is_primary,
        'receives_communications', relationship.receives_communications,
        'active', relationship.active,
        'linked_at', relationship.created_at,
        'guardian_updated_at', guardian.updated_at
    )
    from public.students as student
    join public.student_guardians as relationship
      on relationship.student_id = student.id
    join public.guardians as guardian
      on guardian.id = relationship.guardian_id
    where student.id = p_student_id
      and guardian.id = p_guardian_id;
$$;

revoke all on function private.student_guardian_detail(uuid, uuid)
from public, anon, authenticated;

-- Uma única rotina grava histórico, auditoria técnica e outbox. Seus parâmetros
-- recebem apenas IDs, nomes de campos e o motivo privado da desvinculação.
create or replace function private.record_guardian_change(
    p_student_id uuid,
    p_guardian_id uuid,
    p_action text,
    p_changed_fields text[],
    p_reason text,
    p_request_id uuid,
    p_event_type text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into private.guardian_change_history (
        student_id,
        guardian_id,
        action,
        changed_fields,
        reason,
        actor_id,
        request_id
    )
    values (
        p_student_id,
        p_guardian_id,
        p_action,
        p_changed_fields,
        p_reason,
        auth.uid(),
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
        auth.uid(),
        'student_guardian.' || p_action,
        'student_guardian',
        p_student_id,
        p_changed_fields,
        p_request_id
    );

    insert into private.outbox_events (
        event_type,
        aggregate_type,
        aggregate_id,
        payload
    )
    values (
        p_event_type,
        'Student',
        p_student_id,
        jsonb_build_object(
            'student_id', p_student_id,
            'guardian_id', p_guardian_id
        )
    );
end;
$$;

revoke all on function private.record_guardian_change(
    uuid, uuid, text, text[], text, uuid, text
) from public, anon, authenticated;

-- Garante que qualquer caminho privilegiado preserve ao menos um vínculo
-- principal ativo ao concluir a transação.
set constraints student_guardians_require_primary deferred;

create or replace function public.update_student(
    p_student_id uuid,
    p_request_id uuid,
    p_expected_updated_at timestamptz,
    p_full_name text,
    p_birth_date date
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor_id uuid := auth.uid();
    v_current_name text;
    v_current_birth_date date;
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_student_name text := btrim(coalesce(p_full_name, ''));
    v_changed_fields text[] := array[]::text[];
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
    if p_birth_date is null
       or p_birth_date < date '1900-01-01'
       or p_birth_date >= current_date then
        raise exception using errcode = '22023', message = 'invalid_birth_date';
    end if;

    select full_name, birth_date, updated_at
    into v_current_name, v_current_birth_date, v_current_updated_at
    from public.students
    where id = p_student_id
    for update;

    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'student_version_conflict';
    end if;

    if v_current_name is distinct from v_student_name then
        v_changed_fields := array_append(v_changed_fields, 'full_name');
    end if;
    if v_current_birth_date is distinct from p_birth_date then
        v_changed_fields := array_append(v_changed_fields, 'birth_date');
    end if;
    if cardinality(v_changed_fields) = 0 then
        return jsonb_build_object('updated_at', v_current_updated_at);
    end if;

    update public.students
    set full_name = v_student_name,
        birth_date = p_birth_date
    where id = p_student_id
    returning updated_at into v_updated_at;

    insert into private.audit_entries (
        actor_id, action, entity_type, entity_id, changed_fields, request_id
    )
    values (
        v_actor_id,
        'student.updated',
        'student',
        p_student_id,
        v_changed_fields,
        p_request_id
    );

    insert into private.outbox_events (
        event_type, aggregate_type, aggregate_id, payload
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

comment on function public.update_student(uuid, uuid, timestamptz, text, date) is
    'Atualiza somente dados do aluno; contatos compartilhados usam RPC própria.';
revoke all on function public.update_student(uuid, uuid, timestamptz, text, date)
from public, anon;
grant execute on function public.update_student(uuid, uuid, timestamptz, text, date)
to authenticated;

-- A antiga RPC misturava a versão do aluno com a de um contato possivelmente
-- compartilhado. Ela permanece no catálogo para histórico, mas deixa de ser pública.
revoke all on function public.update_student_with_guardian(
    uuid, uuid, timestamptz, text, date, text, text, text
) from authenticated;

create or replace function public.list_student_guardians(p_student_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_student_updated_at timestamptz;
    v_items jsonb;
begin
    if p_student_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(
        array['coordinator', 'receptionist', 'read_only']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    select updated_at into v_student_updated_at
    from public.students
    where id = p_student_id;
    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;

    select coalesce(
        jsonb_agg(
            jsonb_build_object(
                'id', guardian.id,
                'full_name', guardian.full_name,
                'phone_masked',
                    '(' || left(guardian.phone, 2) || ') *****-' || right(guardian.phone, 4),
                'email_masked', case
                    when guardian.email is null then null
                    else left(guardian.email, 1) || '***@' || split_part(guardian.email, '@', 2)
                end,
                'relationship', relationship.relationship,
                'is_primary', relationship.is_primary,
                'receives_communications', relationship.receives_communications,
                'linked_at', relationship.created_at,
                'guardian_updated_at', guardian.updated_at
            )
            order by
                relationship.is_primary desc,
                extensions.unaccent(lower(guardian.full_name)),
                guardian.id
        ),
        '[]'::jsonb
    )
    into v_items
    from public.student_guardians as relationship
    join public.guardians as guardian
      on guardian.id = relationship.guardian_id
    where relationship.student_id = p_student_id
      and relationship.active;

    return jsonb_build_object(
        'student_id', p_student_id,
        'student_updated_at', v_student_updated_at,
        'items', v_items
    );
end;
$$;

comment on function public.list_student_guardians(uuid) is
    'Lista responsáveis ativos com telefone e e-mail mascarados.';
revoke all on function public.list_student_guardians(uuid) from public, anon;
grant execute on function public.list_student_guardians(uuid) to authenticated;

create or replace function public.get_student_guardian_detail(
    p_student_id uuid,
    p_guardian_id uuid,
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
    if p_student_id is null or p_guardian_id is null or p_request_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(
        array['coordinator', 'receptionist']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    v_result := private.student_guardian_detail(p_student_id, p_guardian_id);
    if v_result is null or not coalesce((v_result ->> 'active')::boolean, false) then
        raise exception using errcode = 'P0002', message = 'guardian_not_found';
    end if;

    -- Esta ação libera contato integral; a auditoria registra finalidade e IDs,
    -- mas não duplica telefone, e-mail ou nome.
    insert into private.audit_entries (
        actor_id, action, entity_type, entity_id, changed_fields, request_id
    )
    values (
        auth.uid(),
        'guardian.sensitive_viewed',
        'guardian',
        p_guardian_id,
        array[]::text[],
        p_request_id
    );

    return v_result;
end;
$$;

comment on function public.get_student_guardian_detail(uuid, uuid, uuid) is
    'Retorna contato integral de vínculo ativo e registra a leitura sensível.';
revoke all on function public.get_student_guardian_detail(uuid, uuid, uuid)
from public, anon;
grant execute on function public.get_student_guardian_detail(uuid, uuid, uuid)
to authenticated;

create or replace function public.add_student_guardian(
    p_student_id uuid,
    p_guardian_id uuid,
    p_request_id uuid,
    p_expected_student_updated_at timestamptz,
    p_create_guardian boolean,
    p_guardian_full_name text,
    p_guardian_phone text,
    p_guardian_email text,
    p_relationship public.guardian_relationship,
    p_make_primary boolean,
    p_receives_communications boolean
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_student_updated_at timestamptz;
    v_new_student_updated_at timestamptz;
    v_guardian_exists boolean;
    v_link_exists boolean;
    v_link_active boolean;
    v_name text := btrim(coalesce(p_guardian_full_name, ''));
    v_phone text := regexp_replace(coalesce(p_guardian_phone, ''), '[^0-9]', '', 'g');
    v_email text := nullif(lower(btrim(p_guardian_email)), '');
    v_action text;
begin
    if p_student_id is null
       or p_guardian_id is null
       or p_request_id is null
       or p_expected_student_updated_at is null
       or p_create_guardian is null
       or p_relationship is null
       or p_make_primary is null
       or p_receives_communications is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(
        array['coordinator', 'receptionist']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    select updated_at into v_student_updated_at
    from public.students
    where id = p_student_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    if v_student_updated_at <> p_expected_student_updated_at then
        raise exception using errcode = '40001', message = 'student_version_conflict';
    end if;

    select exists(select 1 from public.guardians where id = p_guardian_id)
    into v_guardian_exists;
    if p_create_guardian then
        if v_guardian_exists then
            raise exception using errcode = '23505', message = 'guardian_already_linked';
        end if;
        if char_length(v_name) not between 3 and 120 then
            raise exception using errcode = '22023', message = 'invalid_guardian_name';
        end if;
        if v_phone !~ '^[0-9]{10,11}$' then
            raise exception using errcode = '22023', message = 'invalid_phone';
        end if;
        if v_email is not null
           and (
               char_length(v_email) > 254
               or v_email !~* '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
           ) then
            raise exception using errcode = '22023', message = 'invalid_email';
        end if;
        insert into public.guardians (
            id, full_name, phone, email, created_by
        )
        values (
            p_guardian_id, v_name, v_phone, v_email, auth.uid()
        );
    else
        if not v_guardian_exists then
            raise exception using errcode = 'P0002', message = 'guardian_not_found';
        end if;
        if p_guardian_full_name is not null
           or p_guardian_phone is not null
           or p_guardian_email is not null then
            raise exception using errcode = '22023', message = 'existing_guardian_payload_forbidden';
        end if;
    end if;

    select true, active
    into v_link_exists, v_link_active
    from public.student_guardians
    where student_id = p_student_id
      and guardian_id = p_guardian_id
    for update;

    if coalesce(v_link_exists, false) and v_link_active then
        raise exception using errcode = '23505', message = 'guardian_already_linked';
    end if;

    if p_make_primary then
        update public.student_guardians
        set is_primary = false
        where student_id = p_student_id
          and active
          and is_primary;
    elsif not exists (
        select 1 from public.student_guardians
        where student_id = p_student_id and active and is_primary
    ) then
        raise exception using errcode = '23514', message = 'primary_guardian_required';
    end if;

    if coalesce(v_link_exists, false) then
        update public.student_guardians
        set relationship = p_relationship,
            is_primary = p_make_primary,
            receives_communications = p_receives_communications,
            active = true,
            ended_at = null,
            created_by = auth.uid()
        where student_id = p_student_id
          and guardian_id = p_guardian_id;
        v_action := 'relinked';
    else
        insert into public.student_guardians (
            student_id,
            guardian_id,
            relationship,
            is_primary,
            receives_communications,
            active,
            created_by
        )
        values (
            p_student_id,
            p_guardian_id,
            p_relationship,
            p_make_primary,
            p_receives_communications,
            true,
            auth.uid()
        );
        v_action := 'linked';
    end if;

    update public.students
    set updated_at = clock_timestamp()
    where id = p_student_id
    returning updated_at into v_new_student_updated_at;

    perform private.record_guardian_change(
        p_student_id,
        p_guardian_id,
        v_action,
        array['relationship', 'is_primary', 'receives_communications', 'active'],
        null,
        p_request_id,
        'StudentGuardianLinked'
    );

    return private.student_guardian_detail(p_student_id, p_guardian_id)
        || jsonb_build_object('changed', true);
end;
$$;

comment on function public.add_student_guardian(
    uuid, uuid, uuid, timestamptz, boolean, text, text, text,
    public.guardian_relationship, boolean, boolean
) is 'Cria ou revincula responsável com versão, auditoria e principal único.';
revoke all on function public.add_student_guardian(
    uuid, uuid, uuid, timestamptz, boolean, text, text, text,
    public.guardian_relationship, boolean, boolean
) from public, anon;
grant execute on function public.add_student_guardian(
    uuid, uuid, uuid, timestamptz, boolean, text, text, text,
    public.guardian_relationship, boolean, boolean
) to authenticated;

create or replace function public.update_student_guardian(
    p_student_id uuid,
    p_guardian_id uuid,
    p_request_id uuid,
    p_expected_student_updated_at timestamptz,
    p_expected_guardian_updated_at timestamptz,
    p_guardian_full_name text,
    p_guardian_phone text,
    p_guardian_email text,
    p_relationship public.guardian_relationship,
    p_receives_communications boolean
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_student_updated_at timestamptz;
    v_guardian_updated_at timestamptz;
    v_current_name text;
    v_current_phone text;
    v_current_email text;
    v_current_relationship public.guardian_relationship;
    v_current_receives boolean;
    v_name text := btrim(coalesce(p_guardian_full_name, ''));
    v_phone text := regexp_replace(coalesce(p_guardian_phone, ''), '[^0-9]', '', 'g');
    v_email text := nullif(lower(btrim(p_guardian_email)), '');
    v_changed_fields text[] := array[]::text[];
begin
    if p_student_id is null
       or p_guardian_id is null
       or p_request_id is null
       or p_expected_student_updated_at is null
       or p_expected_guardian_updated_at is null
       or p_relationship is null
       or p_receives_communications is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(
        array['coordinator', 'receptionist']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if char_length(v_name) not between 3 and 120 then
        raise exception using errcode = '22023', message = 'invalid_guardian_name';
    end if;
    if v_phone !~ '^[0-9]{10,11}$' then
        raise exception using errcode = '22023', message = 'invalid_phone';
    end if;
    if v_email is not null
       and (
           char_length(v_email) > 254
           or v_email !~* '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
       ) then
        raise exception using errcode = '22023', message = 'invalid_email';
    end if;

    select updated_at into v_student_updated_at
    from public.students
    where id = p_student_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    if v_student_updated_at <> p_expected_student_updated_at then
        raise exception using errcode = '40001', message = 'student_version_conflict';
    end if;

    select relationship, receives_communications
    into v_current_relationship, v_current_receives
    from public.student_guardians
    where student_id = p_student_id
      and guardian_id = p_guardian_id
      and active
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'guardian_not_found';
    end if;

    select full_name, phone, email, updated_at
    into v_current_name, v_current_phone, v_current_email, v_guardian_updated_at
    from public.guardians
    where id = p_guardian_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'guardian_not_found';
    end if;
    if v_guardian_updated_at <> p_expected_guardian_updated_at then
        raise exception using errcode = '40001', message = 'guardian_version_conflict';
    end if;

    if v_current_name is distinct from v_name then
        v_changed_fields := array_append(v_changed_fields, 'full_name');
    end if;
    if v_current_phone is distinct from v_phone then
        v_changed_fields := array_append(v_changed_fields, 'phone');
    end if;
    if v_current_email is distinct from v_email then
        v_changed_fields := array_append(v_changed_fields, 'email');
    end if;
    if v_current_relationship is distinct from p_relationship then
        v_changed_fields := array_append(v_changed_fields, 'relationship');
    end if;
    if v_current_receives is distinct from p_receives_communications then
        v_changed_fields := array_append(v_changed_fields, 'receives_communications');
    end if;

    if cardinality(v_changed_fields) = 0 then
        return private.student_guardian_detail(p_student_id, p_guardian_id)
            || jsonb_build_object('changed', false);
    end if;

    if v_current_name is distinct from v_name
       or v_current_phone is distinct from v_phone
       or v_current_email is distinct from v_email then
        update public.guardians
        set full_name = v_name,
            phone = v_phone,
            email = v_email
        where id = p_guardian_id;
    end if;

    update public.student_guardians
    set relationship = p_relationship,
        receives_communications = p_receives_communications
    where student_id = p_student_id
      and guardian_id = p_guardian_id;

    update public.students
    set updated_at = clock_timestamp()
    where id = p_student_id;

    perform private.record_guardian_change(
        p_student_id,
        p_guardian_id,
        'updated',
        v_changed_fields,
        null,
        p_request_id,
        'StudentGuardianUpdated'
    );

    return private.student_guardian_detail(p_student_id, p_guardian_id)
        || jsonb_build_object('changed', true);
end;
$$;

comment on function public.update_student_guardian(
    uuid, uuid, uuid, timestamptz, timestamptz, text, text, text,
    public.guardian_relationship, boolean
) is 'Atualiza contato e vínculo verificando versões do aluno e do responsável.';
revoke all on function public.update_student_guardian(
    uuid, uuid, uuid, timestamptz, timestamptz, text, text, text,
    public.guardian_relationship, boolean
) from public, anon;
grant execute on function public.update_student_guardian(
    uuid, uuid, uuid, timestamptz, timestamptz, text, text, text,
    public.guardian_relationship, boolean
) to authenticated;

create or replace function public.set_primary_student_guardian(
    p_student_id uuid,
    p_guardian_id uuid,
    p_request_id uuid,
    p_expected_student_updated_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_student_updated_at timestamptz;
    v_is_primary boolean;
begin
    if p_student_id is null
       or p_guardian_id is null
       or p_request_id is null
       or p_expected_student_updated_at is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(
        array['coordinator', 'receptionist']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    select updated_at into v_student_updated_at
    from public.students
    where id = p_student_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    if v_student_updated_at <> p_expected_student_updated_at then
        raise exception using errcode = '40001', message = 'student_version_conflict';
    end if;

    select is_primary into v_is_primary
    from public.student_guardians
    where student_id = p_student_id
      and guardian_id = p_guardian_id
      and active
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'guardian_not_found';
    end if;
    if v_is_primary then
        return private.student_guardian_detail(p_student_id, p_guardian_id)
            || jsonb_build_object('changed', false);
    end if;

    update public.student_guardians
    set is_primary = false
    where student_id = p_student_id
      and active
      and is_primary;
    update public.student_guardians
    set is_primary = true
    where student_id = p_student_id
      and guardian_id = p_guardian_id
      and active;
    update public.students
    set updated_at = clock_timestamp()
    where id = p_student_id;

    perform private.record_guardian_change(
        p_student_id,
        p_guardian_id,
        'primary_changed',
        array['is_primary'],
        null,
        p_request_id,
        'StudentPrimaryGuardianChanged'
    );

    return private.student_guardian_detail(p_student_id, p_guardian_id)
        || jsonb_build_object('changed', true);
end;
$$;

comment on function public.set_primary_student_guardian(uuid, uuid, uuid, timestamptz) is
    'Troca o contato principal atomicamente e preserva exatamente um vínculo ativo.';
revoke all on function public.set_primary_student_guardian(uuid, uuid, uuid, timestamptz)
from public, anon;
grant execute on function public.set_primary_student_guardian(uuid, uuid, uuid, timestamptz)
to authenticated;

create or replace function public.unlink_student_guardian(
    p_student_id uuid,
    p_guardian_id uuid,
    p_request_id uuid,
    p_expected_student_updated_at timestamptz,
    p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_student_updated_at timestamptz;
    v_new_student_updated_at timestamptz;
    v_is_primary boolean;
    v_reason text := btrim(coalesce(p_reason, ''));
begin
    if p_student_id is null
       or p_guardian_id is null
       or p_request_id is null
       or p_expected_student_updated_at is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(
        array['coordinator', 'receptionist']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if char_length(v_reason) not between 10 and 500 then
        raise exception using errcode = '22023', message = 'invalid_guardian_unlink_reason';
    end if;

    select updated_at into v_student_updated_at
    from public.students
    where id = p_student_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'student_not_found';
    end if;
    if v_student_updated_at <> p_expected_student_updated_at then
        raise exception using errcode = '40001', message = 'student_version_conflict';
    end if;

    select is_primary into v_is_primary
    from public.student_guardians
    where student_id = p_student_id
      and guardian_id = p_guardian_id
      and active
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'guardian_not_found';
    end if;
    if v_is_primary then
        raise exception using errcode = '23514', message = 'primary_guardian_required';
    end if;

    update public.student_guardians
    set active = false,
        is_primary = false,
        receives_communications = false,
        ended_at = clock_timestamp()
    where student_id = p_student_id
      and guardian_id = p_guardian_id;
    update public.students
    set updated_at = clock_timestamp()
    where id = p_student_id
    returning updated_at into v_new_student_updated_at;

    perform private.record_guardian_change(
        p_student_id,
        p_guardian_id,
        'unlinked',
        array['active', 'receives_communications'],
        v_reason,
        p_request_id,
        'StudentGuardianUnlinked'
    );

    return jsonb_build_object(
        'student_id', p_student_id,
        'guardian_id', p_guardian_id,
        'student_updated_at', v_new_student_updated_at,
        'changed', true
    );
end;
$$;

comment on function public.unlink_student_guardian(
    uuid, uuid, uuid, timestamptz, text
) is 'Desvincula contato não principal com motivo privado e sem exclusão física.';
revoke all on function public.unlink_student_guardian(
    uuid, uuid, uuid, timestamptz, text
) from public, anon;
grant execute on function public.unlink_student_guardian(
    uuid, uuid, uuid, timestamptz, text
) to authenticated;

-- Tabelas pessoais e histórico continuam inacessíveis ao navegador. Somente as
-- RPCs com verificação interna usam os privilégios de seu proprietário.
revoke all on table private.guardian_change_history from public, anon, authenticated;
revoke all on sequence private.guardian_change_history_id_seq
from public, anon, authenticated;
revoke all on all tables in schema private from public, anon, authenticated;
revoke all on all sequences in schema private from public, anon, authenticated;

commit;
