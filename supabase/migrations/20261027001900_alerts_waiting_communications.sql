-- BL-07/08: acompanhamento de frequência, fila de espera e comunicação.
-- A fila registra posição e decisão humana; nenhuma vaga é concedida por trigger.

begin;

create type public.alert_status as enum ('aberto', 'resolvido');
create type public.waiting_list_status as enum (
    'aguardando', 'vaga_ofertada', 'aceita', 'retirada', 'expirada'
);
create type public.communication_channel as enum ('email', 'whatsapp');

create table public.attendance_alerts (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id),
    class_id uuid references public.classes(id),
    alert_type text not null,
    title text not null,
    detail text not null,
    threshold integer not null check (threshold > 0),
    status public.alert_status not null default 'aberto',
    created_at timestamptz not null default timezone('utc', now()),
    resolved_at timestamptz,
    unique (student_id, class_id, alert_type, status)
);

create table public.waiting_list_entries (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references public.students(id),
    class_id uuid not null references public.classes(id),
    position integer not null check (position > 0),
    status public.waiting_list_status not null default 'aguardando',
    created_at timestamptz not null default timezone('utc', now()),
    offered_at timestamptz,
    decided_at timestamptz,
    unique (class_id, position, status),
    check (status <> 'vaga_ofertada' or offered_at is not null),
    check (status not in ('aceita', 'retirada', 'expirada') or decided_at is not null)
);

create unique index waiting_list_active_student_idx
    on public.waiting_list_entries (student_id, class_id)
    where status in ('aguardando', 'vaga_ofertada');
create index waiting_list_class_order_idx
    on public.waiting_list_entries (class_id, position)
    where status in ('aguardando', 'vaga_ofertada');
create index attendance_alerts_open_idx
    on public.attendance_alerts (student_id, created_at desc)
    where status = 'aberto';

create table private.communication_deliveries (
    id uuid primary key default gen_random_uuid(),
    idempotency_key uuid not null unique,
    channel public.communication_channel not null,
    recipient text not null,
    subject text not null,
    body text not null,
    external_id text,
    status text not null default 'pending' check (status in ('pending', 'sent', 'failed')),
    created_at timestamptz not null default timezone('utc', now()),
    sent_at timestamptz
);

alter table public.attendance_alerts enable row level security;
alter table public.waiting_list_entries enable row level security;
alter table private.communication_deliveries enable row level security;

revoke all on all tables in schema private from public, anon, authenticated;
revoke all on public.attendance_alerts from public, anon, authenticated;
revoke all on public.waiting_list_entries from public, anon, authenticated;
revoke all on private.communication_deliveries from public, anon, authenticated;

commit;
