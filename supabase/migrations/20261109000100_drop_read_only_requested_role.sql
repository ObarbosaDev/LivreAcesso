-- O papel "consulta" (read_only) foi removido de ponta a ponta do produto.
-- O gatilho de autocadastro ainda aceitava 'read_only' como papel sugerido,
-- o que quebrava a listagem de perfis no backend (o adaptador Python não
-- reconhece mais esse valor). Fecha a mesma lacuna na origem do dado.

begin;

create or replace function private.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_requested_role text := new.raw_user_meta_data ->> 'requested_role';
begin
    -- Metadados fornecem apenas um nome inicial e um papel sugerido. A conta
    -- permanece inativa e pendente até uma pessoa coordenadora validar o acesso.
    insert into public.profiles (id, full_name, requested_role)
    values (
        new.id,
        coalesce(
            nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''),
            'Usuário pendente'
        ),
        case
            when v_requested_role in ('coordinator', 'receptionist', 'instructor')
            then v_requested_role::public.user_role
            else null
        end
    );
    return new;
end;
$$;

commit;
