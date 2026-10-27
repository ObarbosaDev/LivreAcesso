# Livre Acesso — Frontend

Interface web da equipe do Instituto Livre Acesso (coordenação, recepção e instrutores). Consome
exclusivamente a API em `../backend`; nunca acessa o Supabase diretamente além da autenticação.

## Stack

- React 19 + TypeScript, Vite
- React Router para navegação e proteção de rotas
- Tailwind CSS v4 para estilo
- `@supabase/supabase-js` só para sessão (login, logout, token) — dados de negócio vêm da API
- Vitest + Testing Library para testes

## Variáveis de ambiente

Todas são públicas (entram no bundle do navegador) e vão em um arquivo `.env.local` **não
versionado** (o `.gitignore` da raiz já bloqueia qualquer `.env*`):

| Variável | Finalidade |
| --- | --- |
| `VITE_SUPABASE_URL` | URL do projeto Supabase usada pelo cliente de autenticação. |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Chave `sb_publishable_...`; nunca a `service_role`. |
| `VITE_API_BASE_URL` | URL base da API FastAPI (`http://127.0.0.1:8000` em desenvolvimento). |

Sem essas três variáveis a aplicação mostra uma tela de configuração indisponível em vez de
travar em branco — a mesma filosofia de falha fechada do backend.

## Comandos

```powershell
npm install
npm run dev        # servidor local
npm run lint        # ESLint, incluindo regras de acessibilidade (jsx-a11y)
npm run typecheck   # checagem de tipos sem gerar build
npm run test        # Vitest
npm run build        # tsc -b && vite build
```

## Estrutura

Organização por responsabilidade, descrita em `../docs/architecture.md`:

```text
src/
├── app/        # providers (autenticação), rotas protegidas, estilos globais
├── pages/      # composição de cada rota
├── widgets/    # layout e navegação
├── features/   # ações compostas por caso de uso (a crescer)
├── entities/   # tipos e regras de cada entidade de domínio (perfil, aluno, turma…)
├── shared/     # cliente HTTP, cliente Supabase, UI reutilizável, utilitários
└── tests/      # setup compartilhado de testes
```

## Autenticação

O login usa `supabase.auth.signInWithPassword`. O token da sessão ativa é anexado em toda chamada
à API pelo cliente HTTP (`shared/api/httpClient.ts`). O frontend nunca decide sozinho o que uma
pessoa pode fazer: o menu e os botões refletem o papel do perfil, mas cada ação só é aceita se a
API autorizar — um `403` da API sempre é tratado, mesmo que o botão não devesse aparecer.

A recuperação de senha (`/esqueci-senha` → `/redefinir-senha`) usa
`supabase.auth.resetPasswordForEmail` e `supabase.auth.updateUser`. Para que o link do e-mail volte
para a tela certa, o Supabase precisa ter `<origem-do-frontend>/redefinir-senha` na lista de Redirect
URLs (**Authentication → URL Configuration**).

### Criar a primeira conta (bootstrap)

Toda conta nova no Supabase Auth começa `pending` e inativa — isso é proposital, para que um
cadastro público nunca ganhe acesso operacional sozinho. Para ter uma conta de coordenação para
testar o frontend:

1. No painel do Supabase: **Authentication → Users → Add user**, com um e-mail e senha de teste.
2. Copie o UUID da conta criada.
3. No **SQL Editor** do projeto, rode (trocando o UUID):

   ```sql
   update public.profiles
   set role = 'coordinator',
       active = true
   where id = '<uuid-da-conta>';
   ```

4. Preencha `.env.local` com a URL e a chave `sb_publishable_...` do projeto (veja
   [Variáveis de ambiente](#variáveis-de-ambiente)) e rode `npm run dev`.

Essa promoção é uma operação de bootstrap feita manualmente pela coordenação — nunca deve virar um
endpoint público (mesma regra já documentada em `../supabase/README.md`).
