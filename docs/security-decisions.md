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
