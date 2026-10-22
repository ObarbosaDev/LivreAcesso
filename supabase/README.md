# Supabase — banco, autenticação e dados duráveis

Este diretório contém somente artefatos versionáveis do banco. Credenciais, tokens, referências locais e arquivos `.env` não pertencem ao repositório.

## Responsabilidades do Supabase

- Supabase Auth: identidade, senha, sessão e JWT;
- PostgreSQL: dados relacionais e transações;
- Row Level Security: segunda barreira de autorização;
- funções RPC: operações atômicas usadas pelo back-end;
- schema `private`: auditoria e outbox fora da API pública;
- Storage: documentos futuros, somente após política de retenção.

## Primeira migration

`migrations/20261021000100_initial_identity_and_students.sql` cria:

- perfis operacionais vinculados a `auth.users`;
- papéis pendente, coordenação, recepção, instrutor e consulta;
- alunos sem acoplamento a modalidade;
- responsáveis com estrutura para vínculo a mais de um aluno;
- relação muitos-para-muitos com contato principal;
- auditoria sem valores pessoais;
- outbox com payload mínimo;
- RLS negando acesso direto às tabelas pessoais;
- RPC transacional de cadastro;
- RPC paginada e mascarada de listagem.

## Segunda migration

`migrations/20261021000200_student_management.sql` acrescenta:

- detalhe sensível restrito e auditado;
- atualização conjunta de aluno e responsável principal;
- concorrência otimista usando `updated_at`;
- histórico protegido de ativação e desativação;
- motivo obrigatório sem cópia para eventos ou logs;
- eventos duráveis `StudentUpdated` e `StudentStatusChanged`;
- listagem com versão para edição;
- ausência intencional de exclusão física.

## Aplicação da migration

Use a Supabase CLI autenticada de forma interativa ou o fluxo de CI da equipe. Nunca coloque senha ou chave em argumentos que possam ir para histórico compartilhado.

```powershell
supabase login
supabase link --project-ref <referencia-do-projeto>
supabase db push
```

Arquivos temporários produzidos pelo CLI são ignorados pelo Git.

## Primeiro coordenador

Toda conta criada começa como `pending` e `active = false`. Isso evita que um cadastro público ganhe acesso operacional por engano.

Depois de criar a primeira conta no Supabase Auth, uma pessoa autorizada deve promover manualmente esse usuário pelo SQL Editor:

```sql
update public.profiles
set role = 'coordinator',
    active = true
where id = '<uuid-da-conta-autorizada>';
```

Essa operação é de bootstrap e não deve virar endpoint público.

## Regras de segurança

1. Nunca usar a chave `service_role` no navegador.
2. Nunca liberar `select *` nas tabelas `students` ou `guardians`.
3. Operações normais usam o JWT da pessoa autenticada.
4. Funções `security definer` sempre verificam papel e usam `search_path` vazio.
5. CPF, telefone e e-mail não entram em auditoria nem outbox.
6. Mudanças estruturais sempre entram em uma nova migration.
7. Não editar migration já aplicada em ambiente compartilhado.
8. Antes do piloto, testar policies com cada papel e tentativa não autorizada.

## Limitação atual

A API já possui gateway HTTP, adaptador de alunos e composição por requisição. Em `development` e `test`, a ausência das duas configurações Supabase ativa memória de forma explícita; em `preview`, `staging` e `production`, a aplicação recusa iniciar sem persistência remota.

Ainda é necessário aplicar a migration a um projeto Supabase real e exercitar cada RPC/RLS com contas dos quatro papéis antes de autorizar dados reais.

## Validação de sessão no FastAPI

O back-end valida JWTs assimétricos localmente pelo endpoint público `auth/v1/.well-known/jwks.json`. As chaves ficam em cache por dez minutos e são recarregadas imediatamente quando surge um `kid` desconhecido durante rotação.

São obrigatórios e validados:

- assinatura `RS256` ou `ES256`;
- emissor exato do projeto configurado em `SUPABASE_URL`;
- audiência `authenticated`;
- expiração e emissão;
- UUID do usuário;
- papel Supabase `authenticated`;
- nível `aal1` ou `aal2`;
- conta não anônima.

O papel operacional (`coordinator`, `receptionist`, `instructor`, `read_only`) não é confiado a metadados editáveis do usuário. Cada RPC consulta `profiles` no banco antes de executar a operação.

Sem `SUPABASE_URL`, o backend usa um verificador que falha fechado com `503`. Isso impede que uma implantação incompleta libere rotas protegidas anonimamente.

## Terceira migration

`migrations/20261021000300_registration_timestamps.sql` cria a versão atual da RPC de cadastro. Ela devolve `id`, `created_at` e `updated_at` produzidos pelo PostgreSQL, garantindo que a primeira edição compare exatamente a versão persistida. A função anterior perde permissão direta para `authenticated` e permanece apenas como parte interna da transação versionada.
