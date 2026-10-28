-- BL-12: leitura operacional agregada da fila sem expor conteúdo ou destinatários.

begin;

create or replace function public.get_communication_queue_status()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
begin
    if (select auth.role()) <> 'service_role' then
        raise exception using errcode = '42501', message = 'worker_forbidden';
    end if;
    return jsonb_build_object(
        'pending', (select count(*) from private.communication_deliveries where status = 'pending'),
        'processing', (select count(*) from private.communication_deliveries where status = 'processing'),
        'failed', (select count(*) from private.communication_deliveries where status = 'failed'),
        'sent', (select count(*) from private.communication_deliveries where status = 'sent'),
        'oldest_pending_at', (select min(created_at) from private.communication_deliveries where status = 'pending')
    );
end;
$$;

revoke all on function public.get_communication_queue_status() from public, anon, authenticated;
grant execute on function public.get_communication_queue_status() to service_role;

commit;
