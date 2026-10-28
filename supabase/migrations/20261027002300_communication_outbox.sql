-- BL-08: gravação idempotente da intenção de comunicação na outbox privada.

begin;

create or replace function public.enqueue_communication(
    p_idempotency_key uuid,
    p_channel public.communication_channel,
    p_recipient text,
    p_subject text,
    p_body text
)
returns private.communication_deliveries
language plpgsql
security definer
set search_path = ''
as $$
declare
    delivery private.communication_deliveries;
begin
    if not (select private.has_any_role(array['coordinator'::public.user_role, 'receptionist'::public.user_role])) then
        raise exception using errcode = '42501', message = 'communication_forbidden';
    end if;
    insert into private.communication_deliveries (
        idempotency_key, channel, recipient, subject, body
    )
    values (p_idempotency_key, p_channel, p_recipient, p_subject, p_body)
    on conflict (idempotency_key) do update
        set recipient = excluded.recipient
    returning * into delivery;
    return delivery;
end;
$$;

revoke all on function public.enqueue_communication(uuid, public.communication_channel, text, text, text)
    from public, anon;
grant execute on function public.enqueue_communication(uuid, public.communication_channel, text, text, text)
    to authenticated;

commit;
