-- Catálogo de modalidades, turmas, horários e instrutores.
-- Matrículas e frequência permanecem fora desta migration e entram nos próximos blocos.

begin;

create type public.class_weekday as enum (
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday'
);

-- A extensão unaccent é estável porque depende de dicionário. Esta wrapper fixa
-- o dicionário usado pelo projeto para permitir índices únicos consistentes.
create or replace function private.normalized_catalog_text(p_value text)
returns text
language sql
immutable
strict
set search_path = ''
as $$
    select extensions.unaccent('extensions.unaccent', lower(btrim(p_value)));
$$;

revoke all on function private.normalized_catalog_text(text)
from public, anon, authenticated;

create table public.modalities (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    active boolean not null default true,
    created_by uuid references auth.users (id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint modalities_name_length check (char_length(btrim(name)) between 3 and 80),
    constraint modalities_description_length check (
        description is null or char_length(btrim(description)) between 1 and 500
    )
);

create unique index modalities_name_normalized_unique
    on public.modalities (private.normalized_catalog_text(name));

comment on table public.modalities is
    'Tipos de atividade; uma modalidade pode possuir várias turmas concretas.';
comment on column public.modalities.description is
    'Descrição operacional curta, sem dados pessoais de participantes.';

create table public.classes (
    id uuid primary key default gen_random_uuid(),
    modality_id uuid not null references public.modalities (id) on delete restrict,
    name text not null,
    capacity integer not null,
    location text not null,
    minimum_age smallint,
    maximum_age smallint,
    active boolean not null default true,
    created_by uuid references auth.users (id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint classes_name_length check (char_length(btrim(name)) between 3 and 120),
    constraint classes_capacity_range check (capacity between 1 and 500),
    constraint classes_location_length check (char_length(btrim(location)) between 2 and 120),
    constraint classes_minimum_age_range check (
        minimum_age is null or minimum_age between 0 and 120
    ),
    constraint classes_maximum_age_range check (
        maximum_age is null or maximum_age between 0 and 120
    ),
    constraint classes_age_order check (
        minimum_age is null or maximum_age is null or minimum_age <= maximum_age
    )
);

create unique index classes_modality_name_normalized_unique
    on public.classes (modality_id, private.normalized_catalog_text(name));
create index classes_modality_active_idx
    on public.classes (modality_id, active, private.normalized_catalog_text(name));

comment on table public.classes is
    'Oferta concreta de modalidade; capacidade não representa vagas ocupadas.';
comment on column public.classes.capacity is
    'Limite total da turma; reserva concorrente de vaga pertence ao BL-05.';
comment on column public.classes.minimum_age is
    'Orientação etária opcional; idade é calculada e nunca armazenada no aluno.';

create table public.class_schedules (
    class_id uuid not null references public.classes (id) on delete restrict,
    weekday public.class_weekday not null,
    starts_at time not null,
    ends_at time not null,
    created_by uuid references auth.users (id) on delete set null,
    created_at timestamptz not null default now(),
    primary key (class_id, weekday, starts_at),
    constraint class_schedules_time_order check (starts_at < ends_at)
);

comment on table public.class_schedules is
    'Horários semanais locais; calendário e timezone institucional entram na chamada.';

create table public.class_instructors (
    class_id uuid not null references public.classes (id) on delete restrict,
    instructor_id uuid not null references public.profiles (id) on delete restrict,
    created_by uuid references auth.users (id) on delete set null,
    created_at timestamptz not null default now(),
    primary key (class_id, instructor_id)
);

create index class_instructors_instructor_idx
    on public.class_instructors (instructor_id, class_id);

comment on table public.class_instructors is
    'Vínculo operacional usado para limitar o instrutor às próprias turmas.';

create table private.catalog_change_history (
    id bigint generated always as identity primary key,
    entity_type text not null,
    entity_id uuid not null,
    action text not null,
    changed_fields text[] not null default '{}',
    reason text,
    actor_id uuid references auth.users (id) on delete set null,
    request_id uuid not null,
    occurred_at timestamptz not null default now(),
    constraint catalog_change_history_entity check (
        entity_type in ('modality', 'class')
    ),
    constraint catalog_change_history_action check (
        action in ('created', 'updated', 'activation_changed')
    ),
    constraint catalog_change_history_reason check (
        reason is null or char_length(btrim(reason)) between 10 and 500
    )
);

create index catalog_change_history_entity_idx
    on private.catalog_change_history (entity_type, entity_id, occurred_at desc);

comment on table private.catalog_change_history is
    'Histórico de configuração; motivo de ativação fica privado e eventos levam apenas IDs.';

create trigger modalities_set_updated_at
before update on public.modalities
for each row execute function private.set_updated_at();

create trigger classes_set_updated_at
before update on public.classes
for each row execute function private.set_updated_at();

-- A turma é bloqueada durante substituições de horários, então o trigger também
-- evita sobreposição em edições administrativas feitas fora das RPCs.
create or replace function private.prevent_class_schedule_overlap()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if exists (
        select 1
        from public.class_schedules as existing
        where existing.class_id = new.class_id
          and existing.weekday = new.weekday
          and new.starts_at < existing.ends_at
          and existing.starts_at < new.ends_at
          and (
              tg_op = 'INSERT'
              or (existing.class_id, existing.weekday, existing.starts_at)
                 <> (old.class_id, old.weekday, old.starts_at)
          )
    ) then
        raise exception using errcode = '23514', message = 'schedule_overlap';
    end if;
    return new;
end;
$$;

revoke all on function private.prevent_class_schedule_overlap()
from public, anon, authenticated;

create trigger class_schedules_prevent_overlap
before insert or update on public.class_schedules
for each row execute function private.prevent_class_schedule_overlap();

create or replace function private.modality_to_json(p_modality_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
    select jsonb_build_object(
        'id', modality.id,
        'name', modality.name,
        'description', modality.description,
        'active', modality.active,
        'created_at', modality.created_at,
        'updated_at', modality.updated_at
    )
    from public.modalities as modality
    where modality.id = p_modality_id;
$$;

revoke all on function private.modality_to_json(uuid)
from public, anon, authenticated;

create or replace function private.class_to_json(p_class_id uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
    select jsonb_build_object(
        'id', class_record.id,
        'modality_id', class_record.modality_id,
        'name', class_record.name,
        'capacity', class_record.capacity,
        'location', class_record.location,
        'minimum_age', class_record.minimum_age,
        'maximum_age', class_record.maximum_age,
        'schedules', coalesce(
            (
                select jsonb_agg(
                    jsonb_build_object(
                        'weekday', schedule.weekday,
                        'starts_at', schedule.starts_at,
                        'ends_at', schedule.ends_at
                    )
                    order by schedule.weekday, schedule.starts_at
                )
                from public.class_schedules as schedule
                where schedule.class_id = class_record.id
            ),
            '[]'::jsonb
        ),
        'instructors', coalesce(
            (
                select jsonb_agg(
                    jsonb_build_object(
                        'id', profile.id,
                        'full_name', profile.full_name
                    )
                    order by private.normalized_catalog_text(profile.full_name), profile.id
                )
                from public.class_instructors as assignment
                join public.profiles as profile on profile.id = assignment.instructor_id
                where assignment.class_id = class_record.id
            ),
            '[]'::jsonb
        ),
        'active', class_record.active,
        'created_at', class_record.created_at,
        'updated_at', class_record.updated_at
    )
    from public.classes as class_record
    where class_record.id = p_class_id;
$$;

revoke all on function private.class_to_json(uuid)
from public, anon, authenticated;

create or replace function private.record_catalog_change(
    p_entity_type text,
    p_entity_id uuid,
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
    insert into private.catalog_change_history (
        entity_type,
        entity_id,
        action,
        changed_fields,
        reason,
        actor_id,
        request_id
    )
    values (
        p_entity_type,
        p_entity_id,
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
        p_entity_type || '.' || p_action,
        p_entity_type,
        p_entity_id,
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
        case when p_entity_type = 'class' then 'Class' else 'Modality' end,
        p_entity_id,
        jsonb_build_object(p_entity_type || '_id', p_entity_id)
    );
end;
$$;

revoke all on function private.record_catalog_change(
    text, uuid, text, text[], text, uuid, text
) from public, anon, authenticated;

create or replace function private.replace_class_schedules(
    p_class_id uuid,
    p_schedules jsonb
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_item jsonb;
    v_weekday public.class_weekday;
    v_starts_at time;
    v_ends_at time;
begin
    if p_schedules is null
       or jsonb_typeof(p_schedules) <> 'array'
       or jsonb_array_length(p_schedules) not between 1 and 14 then
        raise exception using errcode = '22023', message = 'invalid_class_schedule';
    end if;

    delete from public.class_schedules where class_id = p_class_id;

    for v_item in select value from jsonb_array_elements(p_schedules) loop
        if jsonb_typeof(v_item) <> 'object'
           or not (v_item ? 'weekday')
           or not (v_item ? 'starts_at')
           or not (v_item ? 'ends_at') then
            raise exception using errcode = '22023', message = 'invalid_class_schedule';
        end if;
        begin
            v_weekday := (v_item ->> 'weekday')::public.class_weekday;
            v_starts_at := (v_item ->> 'starts_at')::time;
            v_ends_at := (v_item ->> 'ends_at')::time;
        exception
            when invalid_text_representation or datetime_field_overflow then
                raise exception using errcode = '22023', message = 'invalid_class_schedule';
        end;
        if v_starts_at >= v_ends_at then
            raise exception using errcode = '22023', message = 'invalid_class_schedule';
        end if;

        begin
            insert into public.class_schedules (
                class_id, weekday, starts_at, ends_at, created_by
            )
            values (
                p_class_id, v_weekday, v_starts_at, v_ends_at, auth.uid()
            );
        exception
            when unique_violation then
                raise exception using errcode = '23514', message = 'schedule_overlap';
        end;
    end loop;
end;
$$;

revoke all on function private.replace_class_schedules(uuid, jsonb)
from public, anon, authenticated;

create or replace function private.replace_class_instructors(
    p_class_id uuid,
    p_instructor_ids uuid[]
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_count integer;
begin
    if p_instructor_ids is null
       or cardinality(p_instructor_ids) not between 1 and 20
       or exists (select 1 from unnest(p_instructor_ids) as item(id) where id is null) then
        raise exception using errcode = '22023', message = 'invalid_instructor_assignment';
    end if;

    select count(distinct id) into v_count from unnest(p_instructor_ids) as item(id);
    if v_count <> cardinality(p_instructor_ids) then
        raise exception using errcode = '22023', message = 'invalid_instructor_assignment';
    end if;

    select count(*) into v_count
    from public.profiles
    where id = any(p_instructor_ids)
      and role = 'instructor'
      and active;
    if v_count <> cardinality(p_instructor_ids) then
        raise exception using errcode = '22023', message = 'invalid_instructor_assignment';
    end if;

    delete from public.class_instructors where class_id = p_class_id;
    insert into public.class_instructors (class_id, instructor_id, created_by)
    select p_class_id, id, auth.uid()
    from unnest(p_instructor_ids) as item(id);
end;
$$;

revoke all on function private.replace_class_instructors(uuid, uuid[])
from public, anon, authenticated;

create or replace function private.validate_class_fields(
    p_modality_id uuid,
    p_name text,
    p_capacity integer,
    p_location text,
    p_minimum_age integer,
    p_maximum_age integer
)
returns void
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
    if not exists (
        select 1 from public.modalities where id = p_modality_id and active
    ) then
        raise exception using errcode = 'P0002', message = 'modality_not_found';
    end if;
    if char_length(btrim(coalesce(p_name, ''))) not between 3 and 120 then
        raise exception using errcode = '22023', message = 'invalid_class_name';
    end if;
    if p_capacity is null or p_capacity not between 1 and 500 then
        raise exception using errcode = '22023', message = 'invalid_class_capacity';
    end if;
    if char_length(btrim(coalesce(p_location, ''))) not between 2 and 120 then
        raise exception using errcode = '22023', message = 'invalid_class_location';
    end if;
    if (p_minimum_age is not null and p_minimum_age not between 0 and 120)
       or (p_maximum_age is not null and p_maximum_age not between 0 and 120)
       or (
           p_minimum_age is not null
           and p_maximum_age is not null
           and p_minimum_age > p_maximum_age
       ) then
        raise exception using errcode = '22023', message = 'invalid_class_age_range';
    end if;
end;
$$;

revoke all on function private.validate_class_fields(
    uuid, text, integer, text, integer, integer
) from public, anon, authenticated;

alter table public.modalities enable row level security;
alter table public.classes enable row level security;
alter table public.class_schedules enable row level security;
alter table public.class_instructors enable row level security;

-- Nenhuma tabela do catálogo recebe grant direto. Toda leitura aplica papel e,
-- para instrutor, vínculo com a turma dentro da função privilegiada.
revoke all on table public.modalities from public, anon, authenticated;
revoke all on table public.classes from public, anon, authenticated;
revoke all on table public.class_schedules from public, anon, authenticated;
revoke all on table public.class_instructors from public, anon, authenticated;

create or replace function public.list_modalities(
    p_active boolean,
    p_query text,
    p_limit integer,
    p_offset integer
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
        array['coordinator', 'receptionist', 'instructor', 'read_only']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if p_limit is null or p_limit not between 1 and 100 or p_offset is null or p_offset < 0 then
        raise exception using errcode = '22023', message = 'invalid_pagination';
    end if;
    if p_query is not null
       and btrim(p_query) <> ''
       and char_length(btrim(p_query)) not between 2 and 80 then
        raise exception using errcode = '22023', message = 'invalid_query';
    end if;

    with filtered as materialized (
        select id, private.normalized_catalog_text(name) as sort_name
        from public.modalities
        where (p_active is null or active = p_active)
          and (
              p_query is null
              or btrim(p_query) = ''
              or strpos(
                  private.normalized_catalog_text(name),
                  private.normalized_catalog_text(p_query)
              ) > 0
          )
    ),
    page_items as (
        select id, sort_name
        from filtered
        order by sort_name, id
        limit p_limit offset p_offset
    )
    select jsonb_build_object(
        'items', coalesce(
            (
                select jsonb_agg(private.modality_to_json(id) order by sort_name, id)
                from page_items
            ),
            '[]'::jsonb
        ),
        'total', (select count(*) from filtered)
    ) into v_result;
    return v_result;
end;
$$;

revoke all on function public.list_modalities(boolean, text, integer, integer)
from public, anon;
grant execute on function public.list_modalities(boolean, text, integer, integer)
to authenticated;

create or replace function public.get_modality(p_modality_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_result jsonb;
begin
    if p_modality_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(
        array['coordinator', 'receptionist', 'instructor', 'read_only']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    v_result := private.modality_to_json(p_modality_id);
    if v_result is null then
        raise exception using errcode = 'P0002', message = 'modality_not_found';
    end if;
    return v_result;
end;
$$;

revoke all on function public.get_modality(uuid) from public, anon;
grant execute on function public.get_modality(uuid) to authenticated;

create or replace function public.create_modality(
    p_modality_id uuid,
    p_request_id uuid,
    p_name text,
    p_description text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_name text := btrim(coalesce(p_name, ''));
    v_description text := nullif(btrim(p_description), '');
    v_constraint_name text;
begin
    if p_modality_id is null or p_request_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if char_length(v_name) not between 3 and 80
       or (v_description is not null and char_length(v_description) > 500) then
        raise exception using errcode = '22023', message = 'invalid_modality_data';
    end if;

    begin
        insert into public.modalities (
            id, name, description, active, created_by
        )
        values (
            p_modality_id, v_name, v_description, true, auth.uid()
        );
    exception
        when unique_violation then
            get stacked diagnostics v_constraint_name = constraint_name;
            if v_constraint_name = 'modalities_name_normalized_unique' then
                raise exception using errcode = '23505', message = 'duplicate_modality';
            end if;
            raise;
    end;

    perform private.record_catalog_change(
        'modality', p_modality_id, 'created', array['name', 'description', 'active'],
        null, p_request_id, 'ModalityCreated'
    );
    return private.modality_to_json(p_modality_id);
end;
$$;

revoke all on function public.create_modality(uuid, uuid, text, text)
from public, anon;
grant execute on function public.create_modality(uuid, uuid, text, text)
to authenticated;

create or replace function public.update_modality(
    p_modality_id uuid,
    p_request_id uuid,
    p_expected_updated_at timestamptz,
    p_name text,
    p_description text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_name text := btrim(coalesce(p_name, ''));
    v_description text := nullif(btrim(p_description), '');
    v_current_name text;
    v_current_description text;
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_changed_fields text[] := array[]::text[];
    v_constraint_name text;
begin
    if p_modality_id is null or p_request_id is null or p_expected_updated_at is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if char_length(v_name) not between 3 and 80
       or (v_description is not null and char_length(v_description) > 500) then
        raise exception using errcode = '22023', message = 'invalid_modality_data';
    end if;

    select name, description, updated_at
    into v_current_name, v_current_description, v_current_updated_at
    from public.modalities
    where id = p_modality_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'modality_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'modality_version_conflict';
    end if;
    if v_current_name is distinct from v_name then
        v_changed_fields := array_append(v_changed_fields, 'name');
    end if;
    if v_current_description is distinct from v_description then
        v_changed_fields := array_append(v_changed_fields, 'description');
    end if;
    if cardinality(v_changed_fields) = 0 then
        return jsonb_build_object('updated_at', v_current_updated_at);
    end if;

    begin
        update public.modalities
        set name = v_name,
            description = v_description
        where id = p_modality_id
        returning updated_at into v_updated_at;
    exception
        when unique_violation then
            get stacked diagnostics v_constraint_name = constraint_name;
            if v_constraint_name = 'modalities_name_normalized_unique' then
                raise exception using errcode = '23505', message = 'duplicate_modality';
            end if;
            raise;
    end;

    perform private.record_catalog_change(
        'modality', p_modality_id, 'updated', v_changed_fields,
        null, p_request_id, 'ModalityUpdated'
    );
    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

revoke all on function public.update_modality(uuid, uuid, timestamptz, text, text)
from public, anon;
grant execute on function public.update_modality(uuid, uuid, timestamptz, text, text)
to authenticated;

create or replace function public.change_modality_activation(
    p_modality_id uuid,
    p_request_id uuid,
    p_expected_updated_at timestamptz,
    p_active boolean,
    p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_current_active boolean;
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_reason text := btrim(coalesce(p_reason, ''));
begin
    if p_modality_id is null
       or p_request_id is null
       or p_expected_updated_at is null
       or p_active is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if char_length(v_reason) not between 10 and 500 then
        raise exception using errcode = '22023', message = 'invalid_class_change_reason';
    end if;

    select active, updated_at
    into v_current_active, v_current_updated_at
    from public.modalities
    where id = p_modality_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'modality_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'modality_version_conflict';
    end if;
    if v_current_active = p_active then
        return jsonb_build_object('updated_at', v_current_updated_at);
    end if;
    if not p_active and exists (
        select 1 from public.classes where modality_id = p_modality_id and active
    ) then
        raise exception using errcode = '23514', message = 'active_classes_exist';
    end if;

    update public.modalities
    set active = p_active
    where id = p_modality_id
    returning updated_at into v_updated_at;

    perform private.record_catalog_change(
        'modality', p_modality_id, 'activation_changed', array['active'],
        v_reason, p_request_id, 'ModalityActivationChanged'
    );
    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

revoke all on function public.change_modality_activation(
    uuid, uuid, timestamptz, boolean, text
) from public, anon;
grant execute on function public.change_modality_activation(
    uuid, uuid, timestamptz, boolean, text
) to authenticated;

create or replace function public.list_classes(
    p_active boolean,
    p_modality_id uuid,
    p_query text,
    p_limit integer,
    p_offset integer
)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_role public.user_role;
    v_result jsonb;
begin
    select role into v_role
    from public.profiles
    where id = auth.uid() and active;
    if v_role is null
       or v_role not in ('coordinator', 'receptionist', 'instructor', 'read_only') then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if p_limit is null or p_limit not between 1 and 100 or p_offset is null or p_offset < 0 then
        raise exception using errcode = '22023', message = 'invalid_pagination';
    end if;
    if p_query is not null
       and btrim(p_query) <> ''
       and char_length(btrim(p_query)) not between 2 and 120 then
        raise exception using errcode = '22023', message = 'invalid_query';
    end if;

    with filtered as materialized (
        select class_record.id, private.normalized_catalog_text(class_record.name) as sort_name
        from public.classes as class_record
        where (p_active is null or class_record.active = p_active)
          and (p_modality_id is null or class_record.modality_id = p_modality_id)
          and (
              p_query is null
              or btrim(p_query) = ''
              or strpos(
                  private.normalized_catalog_text(class_record.name),
                  private.normalized_catalog_text(p_query)
              ) > 0
          )
          and (
              v_role <> 'instructor'
              or exists (
                  select 1
                  from public.class_instructors as assignment
                  where assignment.class_id = class_record.id
                    and assignment.instructor_id = auth.uid()
              )
          )
    ),
    page_items as (
        select id, sort_name
        from filtered
        order by sort_name, id
        limit p_limit offset p_offset
    )
    select jsonb_build_object(
        'items', coalesce(
            (
                select jsonb_agg(private.class_to_json(id) order by sort_name, id)
                from page_items
            ),
            '[]'::jsonb
        ),
        'total', (select count(*) from filtered)
    ) into v_result;
    return v_result;
end;
$$;

revoke all on function public.list_classes(boolean, uuid, text, integer, integer)
from public, anon;
grant execute on function public.list_classes(boolean, uuid, text, integer, integer)
to authenticated;

create or replace function public.get_class(p_class_id uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_role public.user_role;
    v_result jsonb;
begin
    if p_class_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    select role into v_role
    from public.profiles
    where id = auth.uid() and active;
    if v_role is null
       or v_role not in ('coordinator', 'receptionist', 'instructor', 'read_only') then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if v_role = 'instructor' and not exists (
        select 1 from public.class_instructors
        where class_id = p_class_id and instructor_id = auth.uid()
    ) then
        raise exception using errcode = 'P0002', message = 'class_not_found';
    end if;
    v_result := private.class_to_json(p_class_id);
    if v_result is null then
        raise exception using errcode = 'P0002', message = 'class_not_found';
    end if;
    return v_result;
end;
$$;

revoke all on function public.get_class(uuid) from public, anon;
grant execute on function public.get_class(uuid) to authenticated;

create or replace function public.create_class(
    p_class_id uuid,
    p_request_id uuid,
    p_modality_id uuid,
    p_name text,
    p_capacity integer,
    p_location text,
    p_minimum_age integer,
    p_maximum_age integer,
    p_schedules jsonb,
    p_instructor_ids uuid[]
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_constraint_name text;
begin
    if p_class_id is null or p_request_id is null or p_modality_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    perform private.validate_class_fields(
        p_modality_id, p_name, p_capacity, p_location, p_minimum_age, p_maximum_age
    );

    begin
        insert into public.classes (
            id,
            modality_id,
            name,
            capacity,
            location,
            minimum_age,
            maximum_age,
            active,
            created_by
        )
        values (
            p_class_id,
            p_modality_id,
            btrim(p_name),
            p_capacity,
            btrim(p_location),
            p_minimum_age,
            p_maximum_age,
            true,
            auth.uid()
        );
    exception
        when unique_violation then
            get stacked diagnostics v_constraint_name = constraint_name;
            if v_constraint_name = 'classes_modality_name_normalized_unique' then
                raise exception using errcode = '23505', message = 'duplicate_class';
            end if;
            raise;
    end;

    perform private.replace_class_schedules(p_class_id, p_schedules);
    perform private.replace_class_instructors(p_class_id, p_instructor_ids);
    perform private.record_catalog_change(
        'class',
        p_class_id,
        'created',
        array[
            'modality_id', 'name', 'capacity', 'location', 'minimum_age',
            'maximum_age', 'schedules', 'instructors', 'active'
        ],
        null,
        p_request_id,
        'ClassCreated'
    );
    return private.class_to_json(p_class_id);
end;
$$;

revoke all on function public.create_class(
    uuid, uuid, uuid, text, integer, text, integer, integer, jsonb, uuid[]
) from public, anon;
grant execute on function public.create_class(
    uuid, uuid, uuid, text, integer, text, integer, integer, jsonb, uuid[]
) to authenticated;

create or replace function public.update_class(
    p_class_id uuid,
    p_request_id uuid,
    p_expected_updated_at timestamptz,
    p_modality_id uuid,
    p_name text,
    p_capacity integer,
    p_location text,
    p_minimum_age integer,
    p_maximum_age integer,
    p_schedules jsonb,
    p_instructor_ids uuid[]
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_constraint_name text;
begin
    if p_class_id is null
       or p_request_id is null
       or p_expected_updated_at is null
       or p_modality_id is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    select updated_at into v_current_updated_at
    from public.classes
    where id = p_class_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'class_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'class_version_conflict';
    end if;
    perform private.validate_class_fields(
        p_modality_id, p_name, p_capacity, p_location, p_minimum_age, p_maximum_age
    );

    begin
        update public.classes
        set modality_id = p_modality_id,
            name = btrim(p_name),
            capacity = p_capacity,
            location = btrim(p_location),
            minimum_age = p_minimum_age,
            maximum_age = p_maximum_age
        where id = p_class_id
        returning updated_at into v_updated_at;
    exception
        when unique_violation then
            get stacked diagnostics v_constraint_name = constraint_name;
            if v_constraint_name = 'classes_modality_name_normalized_unique' then
                raise exception using errcode = '23505', message = 'duplicate_class';
            end if;
            raise;
    end;

    perform private.replace_class_schedules(p_class_id, p_schedules);
    perform private.replace_class_instructors(p_class_id, p_instructor_ids);
    perform private.record_catalog_change(
        'class',
        p_class_id,
        'updated',
        array[
            'modality_id', 'name', 'capacity', 'location', 'minimum_age',
            'maximum_age', 'schedules', 'instructors'
        ],
        null,
        p_request_id,
        'ClassUpdated'
    );
    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

revoke all on function public.update_class(
    uuid, uuid, timestamptz, uuid, text, integer, text, integer, integer, jsonb, uuid[]
) from public, anon;
grant execute on function public.update_class(
    uuid, uuid, timestamptz, uuid, text, integer, text, integer, integer, jsonb, uuid[]
) to authenticated;

create or replace function public.change_class_activation(
    p_class_id uuid,
    p_request_id uuid,
    p_expected_updated_at timestamptz,
    p_active boolean,
    p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_modality_id uuid;
    v_current_active boolean;
    v_current_updated_at timestamptz;
    v_updated_at timestamptz;
    v_reason text := btrim(coalesce(p_reason, ''));
begin
    if p_class_id is null
       or p_request_id is null
       or p_expected_updated_at is null
       or p_active is null then
        raise exception using errcode = '22023', message = 'missing_operation_identifier';
    end if;
    if not private.has_any_role(array['coordinator']::public.user_role[]) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;
    if char_length(v_reason) not between 10 and 500 then
        raise exception using errcode = '22023', message = 'invalid_class_change_reason';
    end if;

    select modality_id, active, updated_at
    into v_modality_id, v_current_active, v_current_updated_at
    from public.classes
    where id = p_class_id
    for update;
    if not found then
        raise exception using errcode = 'P0002', message = 'class_not_found';
    end if;
    if v_current_updated_at <> p_expected_updated_at then
        raise exception using errcode = '40001', message = 'class_version_conflict';
    end if;
    if v_current_active = p_active then
        return jsonb_build_object('updated_at', v_current_updated_at);
    end if;
    if p_active then
        if not exists (
            select 1 from public.modalities where id = v_modality_id and active
        ) then
            raise exception using errcode = 'P0002', message = 'modality_not_found';
        end if;
        if not exists (select 1 from public.class_schedules where class_id = p_class_id)
           or not exists (
               select 1
               from public.class_instructors as assignment
               join public.profiles as profile on profile.id = assignment.instructor_id
               where assignment.class_id = p_class_id
                 and profile.role = 'instructor'
                 and profile.active
           ) then
            raise exception using errcode = '23514', message = 'invalid_class_configuration';
        end if;
    end if;

    update public.classes
    set active = p_active
    where id = p_class_id
    returning updated_at into v_updated_at;

    perform private.record_catalog_change(
        'class', p_class_id, 'activation_changed', array['active'],
        v_reason, p_request_id, 'ClassActivationChanged'
    );
    return jsonb_build_object('updated_at', v_updated_at);
end;
$$;

revoke all on function public.change_class_activation(
    uuid, uuid, timestamptz, boolean, text
) from public, anon;
grant execute on function public.change_class_activation(
    uuid, uuid, timestamptz, boolean, text
) to authenticated;

revoke all on table private.catalog_change_history from public, anon, authenticated;
revoke all on sequence private.catalog_change_history_id_seq
from public, anon, authenticated;
revoke all on all tables in schema private from public, anon, authenticated;
revoke all on all sequences in schema private from public, anon, authenticated;

commit;
