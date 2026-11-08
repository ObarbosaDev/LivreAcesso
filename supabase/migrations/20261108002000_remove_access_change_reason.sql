-- O motivo deixou de ser exigido de quem opera ao trocar papel ou
-- ativar/desativar um perfil. O histórico continua existindo, só que sem
-- obrigar texto nenhum.

begin;

alter table private.profile_access_history
    alter column reason drop not null;

alter table private.profile_access_history
    drop constraint profile_access_history_reason_length,
    add constraint profile_access_history_reason_length check (
        reason is null or char_length(btrim(reason)) between 10 and 500
    );

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
    v_reason text := nullif(btrim(coalesce(p_reason, '')), '');
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
    v_reason text := nullif(btrim(coalesce(p_reason, '')), '');
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

commit;
