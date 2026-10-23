# Decisões de segurança — Supabase

## RPCs `security definer` expostas a usuários autenticados

**Estado:** risco conhecido e aceito com controles compensatórios.

O advisor do Supabase alerta sempre que `authenticated` pode executar uma função `security definer`. No Livre Acesso, esse uso é intencional: as tabelas com dados pessoais não concedem acesso direto a `anon` ou `authenticated`; funções específicas retornam projeções mínimas ou executam transações controladas.

Trocar essas funções para `security invoker` exigiria liberar privilégios diretos nas tabelas. Isso permitiria consultar colunas pessoais pela Data API e enfraqueceria a restrição por finalidade.

### Controles obrigatórios

- `anon` não executa nenhuma RPC operacional;
- a função de cadastro antiga não é executável diretamente por `authenticated`;
- cada RPC externa valida papéis ativos por `private.has_any_role`;
- contas novas começam `pending` e inativas;
- `search_path` é vazio em todas as funções privilegiadas;
- nomes de tabela e função são estáticos; não há SQL dinâmico;
- detalhes retornam CPF mascarado na API;
- leitura de telefone/e-mail integral gera auditoria;
- atualização usa concorrência otimista;
- mudança de status exige coordenação e motivo;
- auditoria e outbox ficam no schema `private` sem grants para clientes;
- payloads de eventos carregam IDs, não CPF ou contatos.

### Evidência remota esperada

| RPC | `anon` | `authenticated` |
| --- | --- | --- |
| `register_student_with_guardian` | negado | negado |
| `register_student_with_guardian_v2` | negado | permitido com verificação interna |
| `list_students` | negado | permitido com verificação interna |
| `get_student_detail` | negado | permitido com verificação interna |
| `update_student_with_guardian` | negado | permitido com verificação interna |
| `change_student_status` | negado | permitido com verificação interna |

Se uma RPC nova usar `security definer`, ela deve entrar nesta análise e nos testes antes da migration ser aplicada.

## Policy de perfis e `auth.uid()`

**Estado:** corrigido pela migration `20261021000400_optimize_profile_policy.sql`.

O advisor de desempenho detectou reavaliação de `auth.uid()` para cada linha de `profiles`. A policy passou a envolver `auth.uid()` e `private.has_any_role()` em subconsultas, permitindo que o PostgreSQL as execute como initplans uma vez por consulta.

A autorização permanece idêntica: a pessoa lê o próprio perfil, e coordenação ativa pode ler os demais.

## Dados de produção

Dados reais continuam proibidos até concluir:

1. criação de contas de teste para cada papel;
2. execução da matriz de permissões por JWT real;
3. confirmação de auditoria e outbox;
4. limpeza dos registros sintéticos;
5. revisão final dos advisors;
6. definição de backup e restauração.

## Evidência de produção — 21 de outubro de 2026

Projeto homologado estruturalmente: `LivreAcesso`, região `South America (São Paulo)`.

Verificações concluídas:

- cinco migrations locais e remotas sincronizadas;
- tabelas públicas com RLS ativo;
- tabelas pessoais sem grants diretos para `anon` ou `authenticated`;
- RPC de cadastro antiga sem permissão externa;
- cinco RPCs atuais executáveis somente por `authenticated` e com validação interna;
- triggers de perfil e timestamps presentes;
- JWKS público disponível com assinatura `ES256`;
- advisor de desempenho sem problemas após a quarta migration;
- cinco avisos de segurança restantes correspondem somente às RPCs privilegiadas analisadas acima.

A homologação funcional por papel ainda depende de contas sintéticas do Supabase Auth. Nenhum dado real deve entrar antes dessa matriz passar.

## Matriz de autorização remota — 21 de outubro de 2026

O script `supabase/tests/role_matrix.sql` foi executado no projeto de São Paulo e concluiu `25/25 permission checks passed; transaction rolled back`.

Foram exercitadas as cinco RPCs de alunos como coordenação, recepção, consulta, instrutor e perfil pendente/inativo. Após o rollback, a verificação confirmou:

- uma coordenação ativa;
- nenhum outro estado de perfil;
- zero alunos, responsáveis e vínculos;
- zero históricos de status;
- zero eventos na outbox.

A matriz valida autorização dentro do PostgreSQL com contexto JWT simulado. A etapa restante é autenticar pela API do Supabase e percorrer FastAPI → PostgREST com um JWT real.

## Smoke autenticado de produção — 21 de outubro de 2026

O fluxo completo Supabase Auth → JWT ES256 → FastAPI na Vercel → validação JWKS → RPC PostgREST foi homologado em `https://livre-acesso-api.vercel.app` com a única conta sintética de coordenação.

O resultado confirmou autenticação, autorização, persistência disponível e zero alunos. Chave, senha e token permaneceram somente em memória e não foram exibidos ou gravados.

## Matriz de perfis — 21 de outubro de 2026

A sexta migration foi aplicada e a matriz transacional de perfis concluiu 31/31 verificações. Foram testados perfil próprio, renomeação e quatro ações administrativas sob coordenação, recepção, consulta, instrutor e conta pendente/inativa.

O rollback foi confirmado: uma coordenação ativa, nenhum outro estado, histórico de acesso vazio e zero alunos. Os advisors permaneceram sem problemas de desempenho e sem erros críticos de segurança.
