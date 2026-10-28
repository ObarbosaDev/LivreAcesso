-- BL-10: reserva concorrente e finalização segura da outbox.
-- Somente o worker interno, autenticado com service_role, pode executar
-- estas funções. O cliente autenticado nunca recebe acesso à fila privada.

begin;

alter table private.communication_deliveries
    drop constraint if exists communication_deliveries_status_check;

alter table private.communication_deliveries
    add constraint communication_deliveries_status_check
    check (status in ('pending', 'processing', 'sent', 'failed'));

create or replace function public.claim_pending_communications(p_limit integer)
returns setof private.communication_deliveries
language plpgsql
security definer
set search_path = ''
as $$
begin
    if (select auth.role()) <> 'service_role' then
        raise exception using errcode = '42501', message = 'worker_forbidden';
    end if;
    if p_limit is null or p_limit < 1 or p_limit > 100 then
        raise exception using errcode = '22023', message = 'invalid_worker_limit';
    end if;
    return query
    with candidates as (
        select id
        from private.communication_deliveries
        where status in ('pending', 'failed')
          and available_at <= timezone('utc', now())
        order by available_at, created_at
        for update skip locked
        limit p_limit
    )
    update private.communication_deliveries delivery
       set status = 'processing',
           attempts = delivery.attempts + 1
      from candidates
     where delivery.id = candidates.id
    returning delivery.*;
end;
$$;

create or replace function public.mark_communication_sent(
    p_delivery_id uuid,
    p_external_id text,
    p_processed_at timestamptz
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if (select auth.role()) <> 'service_role' then
        raise exception using errcode = '42501', message = 'worker_forbidden';
    end if;
    update private.communication_deliveries
       set status = 'sent',
           external_id = left(p_external_id, 500),
           processed_at = coalesce(p_processed_at, timezone('utc', now())),
           last_error_code = null
     where id = p_delivery_id
       and status = 'processing';
    if not found then
        raise exception using errcode = '40001', message = 'delivery_not_processing';
    end if;
end;
$$;

create or replace function public.mark_communication_failed(
    p_delivery_id uuid,
    p_error_code text,
    p_available_at timestamptz
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if (select auth.role()) <> 'service_role' then
        raise exception using errcode = '42501', message = 'worker_forbidden';
    end if;
    update private.communication_deliveries
       set status = 'failed',
           last_error_code = left(p_error_code, 80),
           available_at = coalesce(p_available_at, timezone('utc', now()))
     where id = p_delivery_id
       and status = 'processing';
    if not found then
        raise exception using errcode = '40001', message = 'delivery_not_processing';
    end if;
end;
$$;

revoke all on function public.claim_pending_communications(integer) from public, anon, authenticated;
revoke all on function public.mark_communication_sent(uuid, text, timestamptz) from public, anon, authenticated;
revoke all on function public.mark_communication_failed(uuid, text, timestamptz) from public, anon, authenticated;
grant execute on function public.claim_pending_communications(integer) to service_role;
grant execute on function public.mark_communication_sent(uuid, text, timestamptz) to service_role;
grant execute on function public.mark_communication_failed(uuid, text, timestamptz) to service_role;

commit;
