# Deploy do backend — Vercel

## Alvo

- projeto Vercel separado: `livre-acesso-api`;
- repositório: `ObarbosaDev/LivreAcesso`;
- entrada ASGI: `main:app`;
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
- `pyproject.toml` declara `main:app`;
- `vercel.json` fixa o preset FastAPI e `gru1`, além de adicionar headers básicos;
- `.vercelignore` remove testes, PDFs, migrations, caches e documentação do upload;
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
2. criar e vincular localmente o projeto `livre-acesso-api`;
3. manter a integração Git desconectada enquanto a equipe puder enviar direto à `main`;
4. conferir Root Directory na raiz do repositório;
5. cadastrar variáveis pelo painel/CLI sem imprimir valores;
6. executar `npx vercel@65.2.0 deploy` para preview;
7. validar `/health/live`, `/health/ready` e 401 sem JWT;
8. executar `livre-acesso-verify-supabase` informando a URL preview ou produção;
9. promover manualmente com `npx vercel@65.2.0 deploy --prod`;
10. repetir o smoke test na URL de produção.

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

`20261021000500_health_check.sql` cria apenas `public.health_check()`. Ela é `security invoker`, retorna um JSON constante, não lê tabelas e pode ser executada por `anon` e `authenticated`. A migration foi aplicada e o Preview confirmou readiness contra o PostgreSQL real.

## Evidência do Preview

- preset remoto: FastAPI;
- runtime: Python 3.12;
- função: `fastapi`, 15,03 MB;
- região: `gru1`;
- liveness: `200`, estado `alive`;
- readiness: `200`, persistência `up`;
- listagem sem JWT: `401`, `authentication_required`;
- `X-Request-ID` e headers de segurança: presentes;
- deploy automático do GitHub: desconectado;
- promoção para produção: pendente de revisão final.
