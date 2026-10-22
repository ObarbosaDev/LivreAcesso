-- Evita reavaliar auth.uid() e a função de papel para cada linha de profiles.
-- A subconsulta transforma ambos em initplans sem alterar a regra de acesso.

begin;

drop policy if exists profiles_read_own_or_coordinator on public.profiles;

create policy profiles_read_own_or_coordinator
on public.profiles
for select
to authenticated
using (
    id = (select auth.uid())
    or (
        select private.has_any_role(
            array['coordinator']::public.user_role[]
        )
    )
);

commit;
