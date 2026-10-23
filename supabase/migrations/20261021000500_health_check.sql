-- Readiness mínima para confirmar Data API e PostgreSQL sem consultar tabelas.

begin;

create or replace function public.health_check()
returns jsonb
language sql
stable
security invoker
set search_path = ''
as $$
    select jsonb_build_object('status', 'ok');
$$;

comment on function public.health_check() is
    'Retorna estado constante para readiness; não lê dados nem revela configuração.';

revoke all on function public.health_check() from public;
grant execute on function public.health_check() to anon, authenticated;

commit;
