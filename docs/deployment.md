# Deploy do backend — Vercel

## Alvo

- projeto Vercel separado: `livre-acesso-api`;
- repositório: `ObarbosaDev/LivreAcesso`;
- entrada ASGI: `main.py:app`;
- runtime: Python 3.12;
- compute: `gru1` — São Paulo;
- dados/Auth: Supabase São Paulo;
- front-end: outro projeto, criado somente na etapa final.

A Vercel reconhece instâncias FastAPI chamadas `app` em entrypoints suportados e permite declarar um módulo customizado em `tool.vercel.entrypoint` no `pyproject.toml`: [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi).

O runtime Python aceita `pyproject.toml`; a versão padrão atual é 3.12. Arquivos não necessários devem ser excluídos para manter o bundle pequeno: [Python runtime](https://vercel.com/docs/functions/runtimes/python).

`gru1` corresponde a São Paulo, e funções devem ficar próximas do banco para reduzir latência: [Vercel regions](https://vercel.com/docs/regions).

Content was rephrased for compliance with licensing restrictions.

## Configuração versionada

- `.python-version` fixa Python 3.12 no deploy;
- `pyproject.toml` declara `main.py:app`;
- `vercel.json` fixa `gru1`, adiciona headers básicos e exclui testes, PDFs, migrations, caches e documentação do bundle;
- nenhum arquivo `.env` é usado ou versionado.

## Variáveis no painel

Cadastrar em **Project Settings → Environment Variables**:

| Nome | Ambiente | Observação |
| --- | --- | --- |
| `APP_ENV` | Production | Valor `production`. |
| `APP_NAME` | Production | Valor `Livre Acesso API`. |
| `APP_VERSION` | Production | Versão da entrega. |
| `APP_DEBUG` | Production | Valor `false`. |
| `APP_CORS_ORIGINS` | Production | Vazio até existir domínio oficial do front. |
| `SUPABASE_URL` | Production | URL do projeto de São Paulo. |
| `SUPABASE_PUBLISHABLE_KEY` | Production | Somente a chave `sb_publishable_`. |

Não cadastrar `service_role`, senha do banco, senha da conta coordenadora ou token JWT.

## Primeiro deploy

1. autenticar a CLI com `npx vercel@65.2.0 login`;
2. importar/conectar o repositório como `livre-acesso-api`;
3. conferir Root Directory na raiz do repositório;
4. cadastrar variáveis pelo painel;
5. executar `npx vercel@65.2.0 deploy` para preview;
6. validar `/health/live` e `/health/ready`;
7. executar `livre-acesso-verify-supabase` informando a URL preview;
8. promover com `npx vercel@65.2.0 deploy --prod`;
9. repetir o smoke test na URL de produção.

## Critérios de sucesso

```text
GET /health/live  -> 200, status=alive
GET /health/ready -> 200, status=ready, persistence=up
GET /api/v1/students com JWT coordenador -> 200
GET /api/v1/students sem JWT -> 401
```

Todas as respostas precisam de `X-Request-ID`. Nenhuma pode revelar chave, token, URL interna ou mensagem do PostgreSQL.

## Rollback

Se o deploy falhar:

1. não alterar o banco para “acompanhar” um build quebrado;
2. usar rollback/redeploy da última versão saudável na Vercel;
3. confirmar liveness e readiness;
4. registrar o incidente sem PII;
5. corrigir em novo commit — nunca alterar migration já aplicada.

## Quinta migration

`20261021000500_health_check.sql` cria apenas `public.health_check()`. Ela é `security invoker`, retorna um JSON constante, não lê tabelas e pode ser executada por `anon` e `authenticated`. Precisa ser aplicada antes de readiness ficar verde no ambiente remoto.
