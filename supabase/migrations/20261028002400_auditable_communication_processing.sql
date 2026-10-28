-- BL-09: torna a outbox auditável e preparada para processamento com retry.
-- Cada intenção conserva autor, correlação, horários, tentativas e falha
-- sanitizada. O conteúdo continua privado e nunca é exposto por tabela.

begin;

alter table private.communication_deliveries
    add column if not exists requested_by uuid references auth.users(id),
    add column if not exists request_id uuid,
    add column if not exists attempts integer not null default 0,
    add column if not exists available_at timestamptz not null default timezone('utc', now()),
    add column if not exists processed_at timestamptz,
    add column if not exists last_error_code text;

alter table private.communication_deliveries
    add constraint communication_deliveries_attempts_non_negative
    check (attempts >= 0);

create index if not exists communication_deliveries_pending_idx
    on private.communication_deliveries (available_at, created_at)
    where status = 'pending';

create or replace function public.enqueue_communication(
    p_idempotency_key uuid,
    p_channel public.communication_channel,
    p_recipient text,
    p_subject text,
    p_body text,
    p_requested_by uuid,
    p_request_id uuid
)
returns private.communication_deliveries
language plpgsql
security definer
set search_path = ''
as $$
declare
    delivery private.communication_deliveries;
begin
    if p_requested_by is distinct from (select auth.uid()) then
        raise exception using errcode = '42501', message = 'communication_actor_mismatch';
    end if;
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role])) then
        raise exception using errcode = '42501', message = 'communication_forbidden';
    end if;
    insert into private.communication_deliveries (
        idempotency_key, channel, recipient, subject, body,
        requested_by, request_id
    )
    values (
        p_idempotency_key, p_channel, p_recipient, p_subject, p_body,
        p_requested_by, p_request_id
    )
    on conflict (idempotency_key) do update
        set recipient = excluded.recipient,
            subject = excluded.subject,
            body = excluded.body,
            requested_by = excluded.requested_by,
            request_id = excluded.request_id
    returning * into delivery;
    return delivery;
end;
$$;

revoke all on function public.enqueue_communication(uuid, public.communication_channel, text, text, text)
    from public, anon, authenticated;
revoke all on function public.enqueue_communication(uuid, public.communication_channel, text, text, text, uuid, uuid)
    from public, anon;
grant execute on function public.enqueue_communication(uuid, public.communication_channel, text, text, text, uuid, uuid)
    to authenticated;

commit;
