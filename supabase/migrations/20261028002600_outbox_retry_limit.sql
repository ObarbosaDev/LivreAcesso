-- BL-11: impede retry infinito de uma entrega externa indisponível.

begin;

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
          and attempts < 5
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

revoke all on function public.claim_pending_communications(integer) from public, anon, authenticated;
grant execute on function public.claim_pending_communications(integer) to service_role;

commit;
