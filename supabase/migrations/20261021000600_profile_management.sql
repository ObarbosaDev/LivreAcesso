-- Administração de perfis operacionais sem acesso ao SQL Editor.
-- Senhas, tokens e metadados do Auth permanecem fora deste domínio.

begin;

alter table public.profiles
add constraint profiles_pending_inactive
check (role <> 'pending' or not active);

create table private.profile_access_history (
    id bigint generated always as identity primary key,
    profile_id uuid not null references public.profiles (id) on delete restrict,
    previous_role public.user_role not null,
    new_role public.user_role not null,
    previous_active boolean not null,
    new_active boolean not null,
    reason text not null,
    actor_id uuid references auth.users (id) on delete set null,
    request_id uuid not null,
    occurred_at timestamptz not null default now(),
    constraint profile_access_history_has_change check (
        previous_role <> new_role or previous_active <> new_active
    ),
    constraint profile_access_history_reason_length check (
        char_length(btrim(reason)) between 10 and 500
    )
);

comment on table private.profile_access_history is
    'Histórico protegido de papel e ativação, sem senha, token ou metadados Auth.';
comment on column private.profile_access_history.reason is
    'Justificativa potencialmente sensível; nunca deve ser copiada para logs/eventos.';

create index profile_access_history_profile_idx
    on private.profile_access_history (profile_id, occurred_at desc);

create or replace function private.profile_to_json(p_profile_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
    select jsonb_build_object(
        'id', profile.id,
        'full_name', profile.full_name,
        'role', profile.role,
        'active', profile.active,
        'created_at', profile.created_at,
        'updated_at', profile.updated_at
    )
    from public.profiles as profile
    where profile.id = p_profile_id;
$$;

revoke all on function private.profile_to_json(uuid) from public, anon, authenticated;

create or replace function public.get_my_profile()
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $$
    -- A policy de profiles limita a consulta ao próprio auth.uid(). Esta RPC
    -- funciona também para conta pendente/inativa, sem conceder operação.
    select jsonb_build_object(
        'id', profile.id,
        'full_name', profile.full_name,
        'role', profile.role,
        'active', profile.active,
        'created_at', profile.created_at,
        'updated_at', profile.updated_at
    )
    from public.profiles as profile
    where profile.id = (select auth.uid());
$$;

revoke all on function public.get_my_profile() from public, anon;
grant execute on function public.get_my_profile() to authenticated;

create or replace function public.get_profile_detail(p_profile_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_result jsonb;
begin
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    v_result := private.profile_to_json(p_profile_id);
    if v_result is null then
        raise exception using errcode = 'P0002', message = 'profile_not_found';
    end if;
    return v_result;
end;
$$;

revoke all on function public.get_profile_detail(uuid) from public, anon;
grant execute on function public.get_profile_detail(uuid) to authenticated;

create or replace function public.list_profiles(
    p_role public.user_role default null,
    p_active boolean default null,
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
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
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
            profile.id,
            profile.full_name,
            profile.role,
            profile.active,
            profile.created_at,
            profile.updated_at,
            extensions.unaccent(lower(profile.full_name)) as sort_name
        from public.profiles as profile
        where (p_role is null or profile.role = p_role)
          and (p_active is null or profile.active = p_active)
          and (
              p_query is null
              or btrim(p_query) = ''
              or strpos(
                  extensions.unaccent(lower(profile.full_name)),
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
                        'role', item.role,
                        'active', item.active,
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

revoke all on function public.list_profiles(
    public.user_role, boolean, text, integer, integer
) from public, anon;
grant execute on function public.list_profiles(
    public.user_role, boolean, text, integer, integer
) to authenticated;

create or replace function public.update_my_profile_name(
    p_expected_updated_at timestamptz,
    p_full_name text,
    p_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_profile_id uuid := auth.uid();
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_full_name text := btrim(coalesce(p_full_name, ''));
begin
    if v_profile_id is null or p_expected_updated_at is null or p_request_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if char_length(v_full_name) not between 3 and 120 then
        raise exception using errcode = '22023', message = 'invalid_profile_name';
    end if;

    select updated_at
    into v_current_updated_at
    from public.profiles
    where id = v_profile_id
    for update;

    if not found then
        raise exception using errcode = 'P0002', message = 'profile_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'profile_version_conflict';
    end if;

    update public.profiles
    set full_name = v_full_name
    where id = v_profile_id
      and full_name <> v_full_name
    returning updated_at into v_updated_at;

    if v_updated_at is null then
        return jsonb_build_object('updated_at', v_current_updated_at);
    end if;

    insert into private.audit_entries (
        actor_id, action, entity_type, entity_id, changed_fields, request_id
    )
    values (
        v_profile_id,
        'profile.name_updated',
        'profile',
        v_profile_id,
        array['full_name'],
        p_request_id
    );

    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

revoke all on function public.update_my_profile_name(
    timestamptz, text, uuid
) from public, anon;
grant execute on function public.update_my_profile_name(
    timestamptz, text, uuid
) to authenticated;

create or replace function public.change_profile_role(
    p_profile_id uuid,
    p_target_role public.user_role,
    p_reason text,
    p_expected_updated_at timestamptz,
    p_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor_id uuid := auth.uid();
    v_previous_role public.user_role;
    v_active boolean;
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_reason text := btrim(coalesce(p_reason, ''));
begin
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if p_profile_id is null or p_expected_updated_at is null or p_request_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if p_target_role is null or p_target_role = 'pending' then
        raise exception using errcode = '22023', message = 'invalid_profile_role';
    end if;
    if char_length(v_reason) not between 10 and 500 then
        raise exception using errcode = '22023', message = 'invalid_access_change_reason';
    end if;

    -- Toda mudança de acesso bloqueia os coordenadores ativos na mesma ordem.
    -- Duas requisições concorrentes não conseguem remover o último par em paralelo.
    perform id
    from public.profiles
    where role = 'coordinator' and active
    order by id
    for update;

    select role, active, updated_at
    into v_previous_role, v_active, v_current_updated_at
    from public.profiles
    where id = p_profile_id
    for update;

    if not found then
        raise exception using errcode = 'P0002', message = 'profile_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'profile_version_conflict';
    end if;
    if v_previous_role = p_target_role then
        return jsonb_build_object('updated_at', v_current_updated_at);
    end if;
    if v_previous_role = 'coordinator'
       and v_active
       and p_target_role <> 'coordinator'
       and (
           select count(*)
           from public.profiles
           where role = 'coordinator' and active
       ) <= 1 then
        raise exception using errcode = 'P0001', message = 'last_active_coordinator';
    end if;

    update public.profiles
    set role = p_target_role
    where id = p_profile_id
    returning updated_at into v_updated_at;

    insert into private.profile_access_history (
        profile_id,
        previous_role,
        new_role,
        previous_active,
        new_active,
        reason,
        actor_id,
        request_id
    )
    values (
        p_profile_id,
        v_previous_role,
        p_target_role,
        v_active,
        v_active,
        v_reason,
        v_actor_id,
        p_request_id
    );

    insert into private.audit_entries (
        actor_id, action, entity_type, entity_id, changed_fields, request_id
    )
    values (
        v_actor_id,
        'profile.role_changed',
        'profile',
        p_profile_id,
        array['role'],
        p_request_id
    );

    insert into private.outbox_events (
        event_type, aggregate_type, aggregate_id, payload
    )
    values (
        'ProfileRoleChanged',
        'UserProfile',
        p_profile_id,
        jsonb_build_object(
            'profile_id', p_profile_id,
            'previous_role', v_previous_role,
            'new_role', p_target_role
        )
    );

    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

revoke all on function public.change_profile_role(
    uuid, public.user_role, text, timestamptz, uuid
) from public, anon;
grant execute on function public.change_profile_role(
    uuid, public.user_role, text, timestamptz, uuid
) to authenticated;

create or replace function public.change_profile_activation(
    p_profile_id uuid,
    p_active boolean,
    p_reason text,
    p_expected_updated_at timestamptz,
    p_request_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor_id uuid := auth.uid();
    v_role public.user_role;
    v_previous_active boolean;
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_reason text := btrim(coalesce(p_reason, ''));
begin
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if p_profile_id is null
       or p_active is null
       or p_expected_updated_at is null
       or p_request_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if char_length(v_reason) not between 10 and 500 then
        raise exception using errcode = '22023', message = 'invalid_access_change_reason';
    end if;

    perform id
    from public.profiles
    where role = 'coordinator' and active
    order by id
    for update;

    select role, active, updated_at
    into v_role, v_previous_active, v_current_updated_at
    from public.profiles
    where id = p_profile_id
    for update;

    if not found then
        raise exception using errcode = 'P0002', message = 'profile_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'profile_version_conflict';
    end if;
    if v_previous_active = p_active then
        return jsonb_build_object('updated_at', v_current_updated_at);
    end if;
    if p_active and v_role = 'pending' then
        raise exception using errcode = '22023', message = 'profile_role_required';
    end if;
    if v_role = 'coordinator'
       and v_previous_active
       and not p_active
       and (
           select count(*)
           from public.profiles
           where role = 'coordinator' and active
       ) <= 1 then
        raise exception using errcode = 'P0001', message = 'last_active_coordinator';
    end if;

    update public.profiles
    set active = p_active
    where id = p_profile_id
    returning updated_at into v_updated_at;

    insert into private.profile_access_history (
        profile_id,
        previous_role,
        new_role,
        previous_active,
        new_active,
        reason,
        actor_id,
        request_id
    )
    values (
        p_profile_id,
        v_role,
        v_role,
        v_previous_active,
        p_active,
        v_reason,
        v_actor_id,
        p_request_id
    );

    insert into private.audit_entries (
        actor_id, action, entity_type, entity_id, changed_fields, request_id
    )
    values (
        v_actor_id,
        'profile.activation_changed',
        'profile',
        p_profile_id,
        array['active'],
        p_request_id
    );

    insert into private.outbox_events (
        event_type, aggregate_type, aggregate_id, payload
    )
    values (
        'ProfileActivationChanged',
        'UserProfile',
        p_profile_id,
        jsonb_build_object('profile_id', p_profile_id, 'active', p_active)
    );

    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

revoke all on function public.change_profile_activation(
    uuid, boolean, text, timestamptz, uuid
) from public, anon;
grant execute on function public.change_profile_activation(
    uuid, boolean, text, timestamptz, uuid
) to authenticated;

revoke all on all tables in schema private from public, anon, authenticated;
revoke all on sequence private.profile_access_history_id_seq from public, anon, authenticated;

commit;
