-- Permite que a própria pessoa peça acesso (nome, e-mail, senha e papel
-- sugerido) via supabase.auth.signUp, em vez de depender só de convite da
-- coordenação. O cadastro nasce pendente e inativo, como já acontecia; a
-- novidade é registrar qual papel a pessoa sugeriu para a coordenação decidir.

begin;

alter table public.profiles
add column requested_role public.user_role;

comment on column public.profiles.requested_role is
    'Papel sugerido pela própria pessoa ao pedir acesso; a coordenação decide o papel real.';

create or replace function private.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_requested_role text := new.raw_user_meta_data ->> 'requested_role';
begin
    -- Metadados fornecem apenas um nome inicial e um papel sugerido. A conta
    -- permanece inativa e pendente até uma pessoa coordenadora validar o acesso.
    insert into public.profiles (id, full_name, requested_role)
    values (
        new.id,
        coalesce(
            nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''),
            'Usuário pendente'
        ),
        case
            when v_requested_role in ('coordinator', 'receptionist', 'instructor', 'read_only')
            then v_requested_role::public.user_role
            else null
        end
    );
    return new;
end;
$$;

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
        'requested_role', profile.requested_role,
        'created_at', profile.created_at,
        'updated_at', profile.updated_at
    )
    from public.profiles as profile
    where profile.id = p_profile_id;
$$;

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
        'requested_role', profile.requested_role,
        'created_at', profile.created_at,
        'updated_at', profile.updated_at
    )
    from public.profiles as profile
    where profile.id = (select auth.uid());
$$;

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
            profile.requested_role,
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
                        'requested_role', item.requested_role,
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

commit;
