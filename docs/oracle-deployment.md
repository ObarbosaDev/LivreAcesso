# Deploy 100% na Oracle (self-hosted)

O Livre Acesso roda inteiramente na VM gratuita da Oracle (Always Free, forma
Ampere A1): banco, autenticação e API deixam de depender do Supabase Cloud.
O domínio, os contratos HTTP e o código do backend não mudam — apenas quem
hospeda Postgres, Auth e PostgREST.

> [!IMPORTANT]
> Isto substitui o modelo anterior ("API na Oracle, banco no Supabase Cloud").
> A motivação foi o plano gratuito do Supabase Cloud pausar o projeto por
> inatividade. Auto-hospedar a mesma stack open-source elimina essa pausa
> sem reescrever JWT, RLS ou RPCs.

## Componentes

| Camada | Serviço | Imagem |
| --- | --- | --- |
| Banco | `db` | `supabase/postgres` (papéis `anon`/`authenticated`/`service_role` e `auth.uid()` já incluídos) |
| Autenticação | `auth` | `supabase/gotrue`, assinando sessões com chave assimétrica ES256 |
| API de dados | `rest` | `postgrest/postgrest`, expõe as RPCs em `/rest/v1/rpc/*` |
| Gateway | `kong` | roteia `/auth/v1/*` e `/rest/v1/*`; config em [`supabase/self-hosted/kong.yml`](../supabase/self-hosted/kong.yml) |
| TLS/edge | `caddy` | termina HTTPS e distribui para frontend, API e gateway |
| API | `api` | `Dockerfile` da raiz, FastAPI na porta 8000 |
| Worker | `communication-worker` | mesma imagem da API, roda `livre-acesso-process-communications` |
| Frontend | `frontend` | `frontend/Dockerfile`, Nginx na porta 8080 |

Studio, Storage, Realtime, Functions, Analytics e Vector do stack oficial do
Supabase **não são usados** — a API só fala com Auth e PostgREST — e ficam
fora da lista de serviços iniciados, para poupar RAM na VM gratuita.

## Por que isso não quebra o verificador de JWT

`backend/app/modules/identity/infrastructure/supabase_jwt.py` só aceita
tokens assinados com `ES256`/`RS256` e busca a chave pública em
`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`. O Supabase Auth self-hosted
expõe exatamente esse caminho quando configurado com `JWT_KEYS` assimétrico —
é o que `utils/generate-keys.sh` e `utils/add-new-auth-keys.sh` do stack
oficial fazem. Nenhuma linha do verificador de JWT, do gateway de RPC
(`shared/infrastructure/supabase_rpc.py`) ou das políticas RLS precisa mudar.

## Bootstrap de uma VM nova

1. Crie a instância Ampere A1 (Always Free) na Oracle Cloud, Ubuntu 24.04,
   libere as portas 22, 80 e 443 na Security List/NSG.
2. Clone este repositório na VM.
3. Aponte os três subdomínios (frontend, API, gateway) para o IP público da
   VM antes de continuar — o Caddy pede certificado Let's Encrypt na
   primeira subida e falha sem DNS resolvendo.
4. Execute:

   ```bash
   bash scripts/setup_oracle_vm.sh
   ```

   O script instala Docker se faltar, busca o stack oficial do Supabase
   (`github.com/supabase/supabase`, pasta `docker/`) para `.supabase-stack/`
   (ignorado pelo Git), gera as chaves JWT assimétricas, sobe `db` primeiro,
   aplica as migrations de `supabase/migrations/` via `psql` e só então sobe
   `auth`, `rest`, `kong`, `caddy`, `api`, `communication-worker` e
   `frontend`. É idempotente: pode ser executado de novo após uma falha.

5. Depois do script, à mão:
   - preencha `.env.oracle.local` com `SUPABASE_URL=https://<dominio-gateway>`,
     `SUPABASE_PUBLISHABLE_KEY` (valor de `ANON_KEY` em
     `.supabase-stack/.env`) e `SUPABASE_SERVICE_ROLE_KEY` (valor de
     `SERVICE_ROLE_KEY` no mesmo arquivo);
   - crie a primeira conta pelo Auth e promova a coordenação seguindo
     ["Primeiro coordenador"](../supabase/README.md#primeiro-coordenador);
   - rode `python scripts/validate_oracle_env.py` e o smoke test abaixo.

Nenhum segredo gerado (`JWT_KEYS`, `ANON_KEY`, `SERVICE_ROLE_KEY`, senha do
Postgres) deve ser versionado. `.supabase-stack/` e qualquer `.env*` já
estão no `.gitignore`.

## Variáveis obrigatórias da API (`.env.oracle.local`)

`APP_ENV=production`, `APP_HOST=0.0.0.0`, `APP_PORT=8000`, `APP_DEBUG=false`,
`APP_CORS_ORIGINS`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` e, para o
worker, `SUPABASE_SERVICE_ROLE_KEY`, `COMMUNICATION_WEBHOOK_URL`,
`COMMUNICATION_WEBHOOK_TOKEN` e `COMMUNICATION_BATCH_SIZE`.

`APP_RATE_LIMIT_PER_MINUTE` controla o limite por IP da API e assume `120`
quando não informado. Healthchecks e requisições `OPTIONS` não consomem
limite.

## Variáveis do stack Supabase (`.supabase-stack/.env`)

Geradas por `generate-keys.sh`/`add-new-auth-keys.sh`: senha do Postgres,
`JWT_KEYS` (par assimétrico ES256 usado para assinar sessões), `JWT_SECRET`
legado, `ANON_KEY` e `SERVICE_ROLE_KEY`. O script `setup_oracle_vm.sh`
acrescenta `APP_DOMAIN`, `API_DOMAIN`, `GATEWAY_DOMAIN` e `ACME_EMAIL`, lidos
pelo Caddy para TLS e roteamento.

## Verificação pós-deploy

```text
GET /health/live                      -> 200
GET /health/ready                     -> 200 e persistence=up
GET /api/v1/students sem JWT           -> 401
GET https://<dominio-gateway>/auth/v1/.well-known/jwks.json -> 200
GET /health no frontend                -> 200
```

```powershell
python scripts/verify_oracle_deployment.py `
  --api-url https://<dominio-api> `
  --frontend-url https://<dominio-frontend>
```

O comando confirma saúde da API, prontidão com persistência, bloqueio de uma
rota sem JWT e disponibilidade do frontend. Não envia credenciais, não cria
dados e não imprime respostas da aplicação.

Antes de iniciar os containers, valide o ambiente da API:

```powershell
python scripts/validate_oracle_env.py
python scripts/validate_oracle_env.py --worker
```

## Backup

O único estado durável que não vem do código é o volume `livreacesso-db-data`
do Postgres. Programe `pg_dump` periódico para fora da VM (outra região,
Object Storage da Oracle ou similar) — uma VM Always Free não tem SLA de
disco e não substitui um backup externo.

## Rollback

Promover a imagem anterior da API e do frontend. Migrations não são
revertidas automaticamente; qualquer correção de banco entra em uma migration
nova. Regenerar `JWT_KEYS` invalida todas as sessões ES256 ativas — planeje
uma janela de manutenção se isso for necessário.
