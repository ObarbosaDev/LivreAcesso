# Deploy na Oracle

Este projeto pode ser hospedado na Oracle mantendo o Supabase como banco e autenticação durante a primeira etapa. A migração de hospedagem não exige reescrever o domínio ou os contratos HTTP.

## Componentes

- API: imagem raiz `Dockerfile`, executando FastAPI na porta 8000.
- Frontend: `frontend/Dockerfile`, servido pelo Nginx na porta 8080.
- Worker: mesma imagem da API, executando `livre-acesso-process-communications`.
- Banco e autenticação: Supabase enquanto a migração de infraestrutura é validada.
- Segredos: Oracle Vault ou variáveis secretas do serviço de execução.

## Variáveis obrigatórias da API

`APP_ENV=production`, `APP_HOST=0.0.0.0`, `APP_PORT=8000`, `APP_DEBUG=false`, `APP_CORS_ORIGINS`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` e, para o worker, `SUPABASE_SERVICE_ROLE_KEY`, `COMMUNICATION_WEBHOOK_URL`, `COMMUNICATION_WEBHOOK_TOKEN` e `COMMUNICATION_BATCH_SIZE`.

Nunca versionar `.env.oracle.local`, service role, senha, token JWT ou credencial do provedor.

As três variáveis `VITE_*` são públicas, mas precisam ser passadas como `--build-arg` na construção da imagem do frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` e `VITE_API_BASE_URL`.

## Verificação pós-deploy

```text
GET /health/live  -> 200
GET /health/ready -> 200 e persistence=up
GET /api/v1/students sem JWT -> 401
GET /health no frontend -> 200
```

O Load Balancer deve usar `/health/live` para a API e `/health` para o frontend. O worker deve ser executado como job agendado, com uma execução por lote, evitando múltiplas instâncias concorrentes sem necessidade.

## Rollback

Promover a imagem anterior da API e do frontend. Migrations do Supabase não são revertidas automaticamente; qualquer correção de banco deve entrar em uma migration nova.
