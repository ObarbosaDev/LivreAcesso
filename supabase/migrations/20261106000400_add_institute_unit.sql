-- O instituto passa a operar em duas unidades (Ceilandia e Agua Quente).
-- A unidade pertence a turma, nao ao estudante: um aluno pode ter aula em
-- turmas de unidades diferentes. Estudantes sao filtrados por unidade e
-- modalidade via a(s) turma(s) em que tem matricula ativa.

begin;

create type public.institute_unit as enum ('ceilandia', 'agua_quente');

alter table public.classes
    add column unit public.institute_unit not null default 'ceilandia';

-- class_to_json passa a devolver a unidade.
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
        'unit', class_record.unit,
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

-- list_classes ganha o parametro p_unit. Assinatura muda (6 parametros em
-- vez de 5): precisa dropar a funcao antiga, create or replace nao troca
-- overload por assinatura diferente.
drop function if exists public.list_classes(boolean, uuid, text, integer, integer);

create or replace function public.list_classes(
    p_active boolean,
    p_modality_id uuid,
    p_unit public.institute_unit,
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
          and (p_unit is null or class_record.unit = p_unit)
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

revoke all on function public.list_classes(boolean, uuid, public.institute_unit, text, integer, integer)
from public, anon;
grant execute on function public.list_classes(boolean, uuid, public.institute_unit, text, integer, integer)
to authenticated;

-- create_class ganha p_unit. Assinatura muda (11 parametros): dropa a antiga.
drop function if exists public.create_class(
    uuid, uuid, uuid, text, integer, text, integer, integer, jsonb, uuid[]
);

create or replace function public.create_class(
    p_class_id uuid,
    p_request_id uuid,
    p_modality_id uuid,
    p_unit public.institute_unit,
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
    if p_class_id is null or p_request_id is null or p_modality_id is null or p_unit is null then
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
            unit,
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
            p_unit,
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
            'modality_id', 'unit', 'name', 'capacity', 'location', 'minimum_age',
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
    uuid, uuid, uuid, public.institute_unit, text, integer, text, integer, integer, jsonb, uuid[]
) from public, anon;
grant execute on function public.create_class(
    uuid, uuid, uuid, public.institute_unit, text, integer, text, integer, integer, jsonb, uuid[]
) to authenticated;

-- update_class ganha p_unit. Assinatura muda (12 parametros): dropa a antiga.
drop function if exists public.update_class(
    uuid, uuid, timestamptz, uuid, text, integer, text, integer, integer, jsonb, uuid[]
);

create or replace function public.update_class(
    p_class_id uuid,
    p_request_id uuid,
    p_expected_updated_at timestamptz,
    p_modality_id uuid,
    p_unit public.institute_unit,
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
       or p_modality_id is null
       or p_unit is null then
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
            unit = p_unit,
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
            'modality_id', 'unit', 'name', 'capacity', 'location', 'minimum_age',
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
    uuid, uuid, timestamptz, uuid, public.institute_unit, text, integer, text, integer, integer, jsonb, uuid[]
) from public, anon;
grant execute on function public.update_class(
    uuid, uuid, timestamptz, uuid, public.institute_unit, text, integer, text, integer, integer, jsonb, uuid[]
) to authenticated;

-- list_students ganha p_unit/p_modality_id, filtrando por matricula ativa
-- numa turma que bate com a unidade e/ou modalidade. Assinatura muda (6
-- parametros): dropa a antiga.
drop function if exists public.list_students(public.student_status, text, integer, integer);

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
