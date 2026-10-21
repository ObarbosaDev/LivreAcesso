-- Fundação persistente do Livre Acesso.
-- A migration cria somente identidade, alunos, responsáveis, auditoria e outbox.
-- Turmas e matrículas entram em outra migration porque pertencem a outro domínio.

begin;

-- Unaccent mantém a busca por nome intuitiva: "joao" encontra "João". A
-- extensão é usada somente para comparação e nunca altera o nome armazenado.
create schema if not exists extensions;
create extension if not exists unaccent with schema extensions;

-- Objetos internos ficam fora do schema exposto pelo PostgREST. Isso reduz a
-- superfície de acesso a auditoria, eventos pendentes e funções auxiliares.
create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to authenticated;

create type public.user_role as enum (
    'pending',
    'coordinator',
    'receptionist',
    'instructor',
    'read_only'
);

create type public.student_status as enum (
    'active',
    'inactive'
);

create type public.guardian_relationship as enum (
    'legal_guardian',
    'parent',
    'emergency_contact',
    'self',
    'other'
);

create table public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    full_name text not null,
    role public.user_role not null default 'pending',
    active boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint profiles_full_name_length check (char_length(btrim(full_name)) between 3 and 120)
);

comment on table public.profiles is
    'Perfil operacional ligado ao Supabase Auth; não armazena senha ou token.';
comment on column public.profiles.role is
    'Papel de autorização. Novas contas começam pendentes e sem acesso operacional.';
comment on column public.profiles.active is
    'Bloqueio administrativo independente da existência da conta no Auth.';

create table public.students (
    id uuid primary key default gen_random_uuid(),
    full_name text not null,
    cpf varchar(11) not null,
    birth_date date not null,
    status public.student_status not null default 'active',
    created_by uuid references auth.users (id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint students_full_name_length check (char_length(btrim(full_name)) between 3 and 120),
    constraint students_cpf_digits check (cpf ~ '^[0-9]{11}$'),
    constraint students_cpf_unique unique (cpf),
    constraint students_birth_date_range check (
        birth_date >= date '1900-01-01' and birth_date < current_date
    )
);

comment on table public.students is
    'Cadastro pessoal do aluno; turma e modalidade são vinculadas por matrícula.';
comment on column public.students.cpf is
    'Dado pessoal de acesso restrito, normalizado para unicidade; nunca deve ir para logs.';
comment on column public.students.status is
    'Ciclo global do cadastro. Lista de espera e matrícula possuem estados próprios.';

create table public.guardians (
    id uuid primary key default gen_random_uuid(),
    full_name text not null,
    cpf varchar(11),
    phone varchar(11) not null,
    email text,
    created_by uuid references auth.users (id) on delete set null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint guardians_full_name_length check (char_length(btrim(full_name)) between 3 and 120),
    constraint guardians_cpf_digits check (cpf is null or cpf ~ '^[0-9]{11}$'),
    constraint guardians_phone_digits check (phone ~ '^[0-9]{10,11}$'),
    constraint guardians_email_length check (email is null or char_length(email) <= 254)
);

-- CPF de responsável é opcional, mas precisa ser único quando informado.
create unique index guardians_cpf_unique
    on public.guardians (cpf)
    where cpf is not null;

comment on table public.guardians is
    'Responsáveis e contatos; uma pessoa pode estar vinculada a vários alunos.';
comment on column public.guardians.phone is
    'Dado pessoal usado para contato institucional; respostas de lista devem mascará-lo.';
comment on column public.guardians.email is
    'Dado pessoal opcional, normalizado em minúsculas pela operação de cadastro.';

create table public.student_guardians (
    student_id uuid not null references public.students (id) on delete restrict,
    guardian_id uuid not null references public.guardians (id) on delete restrict,
    relationship public.guardian_relationship not null,
    is_primary boolean not null default false,
    receives_communications boolean not null default true,
    created_by uuid references auth.users (id) on delete set null,
    created_at timestamptz not null default now(),
    primary key (student_id, guardian_id)
);

-- Um aluno pode ter vários contatos, mas apenas um é exibido como principal.
create unique index student_guardians_one_primary
    on public.student_guardians (student_id)
    where is_primary;

comment on table public.student_guardians is
    'Relação muitos-para-muitos entre alunos e responsáveis, com finalidade explícita.';

create table private.audit_entries (
    id bigint generated always as identity primary key,
    actor_id uuid references auth.users (id) on delete set null,
    action text not null,
    entity_type text not null,
    entity_id uuid not null,
    changed_fields text[] not null default '{}',
    request_id uuid,
    occurred_at timestamptz not null default now(),
    constraint audit_action_length check (char_length(action) between 3 and 100),
    constraint audit_entity_type_length check (char_length(entity_type) between 3 and 100)
);

comment on table private.audit_entries is
    'Trilha técnica sem cópia de CPF, telefone, e-mail ou valores completos alterados.';
comment on column private.audit_entries.changed_fields is
    'Registra nomes dos campos alterados, não seus valores pessoais.';

create table private.outbox_events (
    id uuid primary key default gen_random_uuid(),
    event_type text not null,
    aggregate_type text not null,
    aggregate_id uuid not null,
    payload jsonb not null default '{}'::jsonb,
    occurred_at timestamptz not null default now(),
    available_at timestamptz not null default now(),
    processed_at timestamptz,
    attempts integer not null default 0,
    last_error text,
    constraint outbox_event_type_length check (char_length(event_type) between 3 and 150),
    constraint outbox_aggregate_type_length check (char_length(aggregate_type) between 3 and 100),
    constraint outbox_attempts_non_negative check (attempts >= 0)
);

comment on table private.outbox_events is
    'Eventos duráveis para efeitos externos; payloads devem usar IDs e evitar dados pessoais.';
comment on column private.outbox_events.last_error is
    'Erro técnico sanitizado; nunca deve receber corpo de requisição, token ou PII.';

create index students_status_name_idx
    on public.students (status, lower(full_name));
create index student_guardians_guardian_idx
    on public.student_guardians (guardian_id);
create index audit_entries_entity_idx
    on private.audit_entries (entity_type, entity_id, occurred_at desc);
create index outbox_events_pending_idx
    on private.outbox_events (available_at, occurred_at)
    where processed_at is null;

create or replace function private.set_updated_at()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    new.updated_at := now();
    return new;
end;
$$;

revoke all on function private.set_updated_at() from public, anon, authenticated;

create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function private.set_updated_at();

create trigger students_set_updated_at
before update on public.students
for each row execute function private.set_updated_at();

create trigger guardians_set_updated_at
before update on public.guardians
for each row execute function private.set_updated_at();

create or replace function private.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    -- Metadados fornecem apenas um nome inicial. A conta permanece inativa e
    -- pendente até uma pessoa coordenadora validar seu acesso.
    insert into public.profiles (id, full_name)
    values (
        new.id,
        coalesce(
            nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''),
            'Usuário pendente'
        )
    );
    return new;
end;
$$;

revoke all on function private.handle_new_auth_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function private.handle_new_auth_user();

create or replace function private.has_any_role(allowed_roles public.user_role[])
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.profiles as profile
        where profile.id = auth.uid()
          and profile.active
          and profile.role = any(allowed_roles)
    );
$$;

revoke all on function private.has_any_role(public.user_role[]) from public, anon;
grant execute on function private.has_any_role(public.user_role[]) to authenticated;

alter table public.profiles enable row level security;
alter table public.students enable row level security;
alter table public.guardians enable row level security;
alter table public.student_guardians enable row level security;

-- O próprio usuário consegue entender se sua conta está pendente. Somente a
-- coordenação ativa consegue consultar perfis de outras pessoas.
create policy profiles_read_own_or_coordinator
on public.profiles
for select
to authenticated
using (
    id = auth.uid()
    or private.has_any_role(array['coordinator']::public.user_role[])
);

-- Tabelas pessoais não recebem policies diretas nesta fase. Sem policy, RLS
-- nega o acesso; operações autorizadas passam pelas funções abaixo.
revoke all on table public.profiles from public, anon, authenticated;
revoke all on table public.students from public, anon, authenticated;
revoke all on table public.guardians from public, anon, authenticated;
revoke all on table public.student_guardians from public, anon, authenticated;
grant select on table public.profiles to authenticated;

create or replace function public.register_student_with_guardian(
    p_full_name text,
    p_cpf text,
    p_birth_date date,
    p_guardian_full_name text,
    p_guardian_phone text,
    p_guardian_email text default null,
    p_relationship public.guardian_relationship default 'legal_guardian'
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
    v_cpf text := regexp_replace(coalesce(p_cpf, ''), '[^0-9]', '', 'g');
    v_phone text := regexp_replace(coalesce(p_guardian_phone, ''), '[^0-9]', '', 'g');
    v_student_name text := btrim(coalesce(p_full_name, ''));
    v_guardian_name text := btrim(coalesce(p_guardian_full_name, ''));
    v_guardian_email text := nullif(lower(btrim(p_guardian_email)), '');
begin
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
    if v_cpf !~ '^[0-9]{11}$' then
        raise exception using errcode = '22023', message = 'invalid_cpf_format';
    end if;
    if v_phone !~ '^[0-9]{10,11}$' then
        raise exception using errcode = '22023', message = 'invalid_phone_format';
    end if;
    if p_birth_date is null
       or p_birth_date < date '1900-01-01'
       or p_birth_date >= current_date then
        raise exception using errcode = '22023', message = 'invalid_birth_date';
    end if;
    if v_guardian_email is not null and char_length(v_guardian_email) > 254 then
        raise exception using errcode = '22023', message = 'invalid_email';
    end if;

    begin
        insert into public.students (
            full_name,
            cpf,
            birth_date,
            status,
            created_by
        )
        values (
            v_student_name,
            v_cpf,
            p_birth_date,
            'active',
            v_actor_id
        )
        returning id into v_student_id;
    exception
        when unique_violation then
            -- O código estável será traduzido pela API para uma mensagem simples.
            raise exception using errcode = '23505', message = 'duplicate_cpf';
    end;

    insert into public.guardians (
        full_name,
        phone,
        email,
        created_by
    )
    values (
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

    -- A auditoria registra somente a ação e os campos envolvidos. Os valores
    -- pessoais permanecem nas tabelas protegidas e não são duplicados no log.
    insert into private.audit_entries (
        actor_id,
        action,
        entity_type,
        entity_id,
        changed_fields
    )
    values (
        v_actor_id,
        'student.registered',
        'student',
        v_student_id,
        array['full_name', 'cpf', 'birth_date', 'guardian']
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

comment on function public.register_student_with_guardian is
    'Cadastra aluno, responsável, vínculo, auditoria e evento na mesma transação.';

revoke all on function public.register_student_with_guardian(
    text,
    text,
    date,
    text,
    text,
    text,
    public.guardian_relationship
) from public, anon;
grant execute on function public.register_student_with_guardian(
    text,
    text,
    date,
    text,
    text,
    text,
    public.guardian_relationship
) to authenticated;

create or replace function public.list_students(
    p_status public.student_status default null,
    p_query text default null,
    p_limit integer default 25,
    p_offset integer default 0
)
returns table (
    id uuid,
    full_name text,
    cpf_masked text,
    birth_date date,
    age integer,
    status public.student_status,
    guardian_name text,
    guardian_phone_masked text,
    created_at timestamptz,
    total_count bigint
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
    if not private.has_any_role(
        array['coordinator', 'receptionist', 'read_only']::public.user_role[]
    ) then
        raise exception using errcode = '42501', message = 'forbidden';
    end if;

    return query
    select
        student.id,
        student.full_name,
        '***.***.***-' || right(student.cpf, 2),
        student.birth_date,
        extract(year from age(current_date, student.birth_date))::integer,
        student.status,
        guardian.full_name,
        case
            when guardian.phone is null then null
            else '(' || left(guardian.phone, 2) || ') *****-' || right(guardian.phone, 4)
        end,
        student.created_at,
        count(*) over ()
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
          or extensions.unaccent(lower(student.full_name))
             like '%' || extensions.unaccent(lower(btrim(p_query))) || '%'
      )
    order by extensions.unaccent(lower(student.full_name)), student.id
    limit greatest(1, least(coalesce(p_limit, 25), 100))
    offset greatest(coalesce(p_offset, 0), 0);
end;
$$;

comment on function public.list_students is
    'Lista paginada e mascarada; não concede leitura direta às tabelas pessoais.';

revoke all on function public.list_students(
    public.student_status,
    text,
    integer,
    integer
) from public, anon;
grant execute on function public.list_students(
    public.student_status,
    text,
    integer,
    integer
) to authenticated;

-- Objetos internos nunca ficam disponíveis pelos papéis usados pelo navegador.
revoke all on all tables in schema private from public, anon, authenticated;
revoke all on all sequences in schema private from public, anon, authenticated;

commit;
