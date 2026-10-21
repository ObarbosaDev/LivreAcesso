# Como contribuir com o Livre Acesso

Este guia define o fluxo mínimo para manter o repositório compreensível, seguro e evolutivo. Toda contribuição — código, teste, arquitetura ou documentação — deve preservar as regras aqui descritas.

## 1. Antes de começar

1. Leia o [`README.md`](README.md).
2. Consulte [`docs/architecture.md`](docs/architecture.md).
3. Confirme a linguagem do domínio em [`docs/domain-glossary.md`](docs/domain-glossary.md).
4. Verifique se a necessidade já possui uma issue ou decisão registrada.
5. Nunca copie dados reais da instituição para o ambiente de desenvolvimento.

## 2. Preparação local

```powershell
git clone https://github.com/ObarbosaDev/LivreAcesso.git
Set-Location LivreAcesso
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

O projeto não versiona nenhum arquivo `.env`. Configure valores somente na sessão local do terminal ou no cofre da plataforma de hospedagem.

## 3. Fluxo Git

Nunca faça push direto para `main`.

```powershell
git checkout main
git pull
git checkout -b feat/cadastro-responsavel
```

Padrões de branch:

- `feat/<assunto>` — funcionalidade;
- `fix/<assunto>` — correção;
- `refactor/<assunto>` — refatoração;
- `docs/<assunto>` — documentação;
- `test/<assunto>` — testes;
- `chore/<assunto>` — manutenção.

Use nomes curtos, descritivos, em minúsculas e separados por hífen.

## 4. Commits

Formato recomendado:

```text
<tipo>: <descrição objetiva no imperativo>
```

Exemplos:

```text
feat: adiciona cadastro de responsável
fix: impede matrícula acima da capacidade
refactor: separa mapper de aluno
 test: cobre cpf duplicado
 docs: documenta fluxo de chamada
```

Evite commits com mensagens vagas como `alterações`, `ajustes` ou `final`.

## 5. Regras arquiteturais

### Domínio

- não importa FastAPI, ORM, SDKs ou detalhes de interface;
- contém regras, entidades, agregados, value objects, eventos e portas;
- não serializa respostas HTTP;
- não acessa variáveis de ambiente diretamente.

### Aplicação

- coordena casos de uso;
- depende de portas, não de bancos concretos;
- usa DTOs explícitos nas fronteiras;
- publica eventos somente depois da operação principal bem-sucedida.

### Infraestrutura

- implementa portas;
- concentra SQL, SDKs, filas e integrações externas;
- não define regra de negócio;
- preserva transações e idempotência.

### Apresentação

- valida protocolo e autenticação;
- traduz erros para HTTP;
- não executa SQL nem contém decisões do domínio;
- não retorna entidade diretamente.

## 6. Código Python

- Python 3.12 ou superior;
- type hints obrigatórios em código de produção;
- limite de 100 caracteres por linha;
- nomes internos em inglês e linguagem apresentada ao usuário em português;
- funções pequenas e com uma responsabilidade;
- dependências novas somente quando justificadas e com versão fixada;
- imports absolutos dentro do projeto;
- nada de credenciais, PII ou dados reais em código, testes, comentários ou logs.

## 7. Testes e validação

Antes de abrir um pull request:

```powershell
ruff check .
ruff format --check .
mypy backend
pytest
pytest --cov=backend --cov-report=term-missing
```

Uma correção deve incluir um teste que falhava antes da correção sempre que o comportamento puder ser automatizado. Uma nova regra deve cobrir sucesso, limite e falha relevante.

## 8. Eventos

- nomeie fatos no passado: `StudentRegistered`, não `RegisterStudent`;
- não inclua CPF, telefone, e-mail ou endereço no payload sem justificativa formal;
- handlers devem ser idempotentes quando puderem ser repetidos;
- integrações externas confiáveis devem evoluir para outbox transacional;
- não use evento para esconder uma chamada direta necessária ao fluxo principal.

## 9. Banco e migrations

- toda alteração estrutural deve possuir migration;
- nunca edite uma migration já aplicada em ambiente compartilhado;
- use constraints e índices para regras estruturais;
- timestamps são armazenados em UTC;
- scripts e seeds usam somente dados fictícios;
- exclusão definitiva de dados exige política de retenção aprovada.

## 10. Pull request

O PR deve explicar:

1. problema resolvido;
2. decisão adotada;
3. comportamento antes e depois;
4. testes executados e resultado;
5. impacto em API, banco e interface;
6. risco de segurança ou privacidade;
7. screenshots quando houver mudança visual;
8. pendências conhecidas.

Checklist:

- [ ] a alteração está limitada ao escopo descrito;
- [ ] arquitetura e linguagem do domínio foram preservadas;
- [ ] testes relevantes foram adicionados/atualizados;
- [ ] lint, tipos e testes passaram;
- [ ] documentação e OpenAPI foram atualizados;
- [ ] não há segredo, `.env`, PII ou arquivo local;
- [ ] mudanças de banco possuem migration e rollback avaliado;
- [ ] acessibilidade e responsividade foram verificadas quando aplicável.

## 11. Revisão

Revisores devem priorizar:

1. comportamento e regra de negócio;
2. segurança, autorização e privacidade;
3. integridade e concorrência;
4. contratos e compatibilidade;
5. testes e observabilidade;
6. legibilidade e consistência.

Preferência estética não deve bloquear um PR se as ferramentas e os padrões do projeto já forem respeitados.

## 12. Dúvidas e decisões

Se uma regra estiver ambígua — especialmente faltas, inatividade, vagas, responsáveis adultos ou comunicação — não invente silenciosamente. Registre a dúvida e obtenha validação da instituição antes de transformá-la em comportamento definitivo.
