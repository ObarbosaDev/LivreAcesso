# Gestão de perfis e acessos

## Separação de responsabilidades

Supabase Auth mantém identidade, senha, sessão e JWT. `public.profiles` mantém apenas o perfil operacional usado pelo Livre Acesso: nome de exibição, papel, ativação e versão.

O backend nunca recebe nem armazena senha de outro usuário e não usa `service_role` nas requisições comuns.

## Ciclo de acesso

```text
Conta criada no Supabase Auth
        ↓
Perfil pending + inativo
        ↓ coordenação escolhe papel e registra motivo
Papel definido + inativo
        ↓ coordenação ativa e registra motivo
Perfil operacional ativo
```

Uma conta pendente pode consultar e corrigir o próprio nome, mas não possui capacidades operacionais. Ativação só é permitida depois de definir um papel.

## Papéis e capacidades atuais

| Papel | Capacidades implementadas |
| --- | --- |
| Coordenador | Administrar perfis e executar todas as operações atuais de alunos. |
| Recepção | Listar, consultar, cadastrar e atualizar alunos. |
| Instrutor | Nenhuma capacidade geral de alunos; receberá apenas turmas atribuídas. |
| Consulta | Listar a projeção mascarada de alunos. |
| Pendente | Nenhuma operação; apenas consulta/correção do próprio perfil. |

A lista de capacidades retornada por `/me` serve para orientar a interface, mas não substitui autorização no caso de uso e na RPC.

## Endpoints

| Método | Rota | Finalidade |
| --- | --- | --- |
| `GET` | `/api/v1/me` | Consultar próprio perfil e capacidades. |
| `PUT` | `/api/v1/me` | Corrigir próprio nome com controle de versão. |
| `GET` | `/api/v1/profiles` | Coordenação pesquisa perfis paginados. |
| `POST` | `/api/v1/profiles/{id}/role` | Coordenação atribui papel com motivo. |
| `POST` | `/api/v1/profiles/{id}/activate` | Coordenação libera acesso. |
| `POST` | `/api/v1/profiles/{id}/deactivate` | Coordenação bloqueia acesso sem excluir conta. |

## Regras críticas

- `pending` nunca pode estar ativo;
- o papel `pending` não pode ser atribuído como papel operacional;
- toda mudança administrativa exige motivo entre 10 e 500 caracteres;
- toda escrita usa `expected_updated_at` para impedir sobrescrita concorrente;
- o último coordenador ativo não pode ser desativado nem rebaixado;
- mudanças concorrentes de coordenação bloqueiam as mesmas linhas em ordem estável;
- motivo fica no histórico privado e não entra em evento ou log;
- eventos carregam somente UUID e transição mínima;
- listagem não devolve e-mail, senha, telefone Auth ou metadados do provedor;
- criação de conta continua no Supabase Auth; este módulo administra perfis existentes.

## Concorrência do último coordenador

As RPCs bloqueiam todos os coordenadores ativos em ordem de UUID antes de contar. Isso serializa duas tentativas simultâneas de remoção: a primeira pode prosseguir apenas se outra coordenação permanecer; a segunda reavalia o estado e é bloqueada quando se tornaria a última.

## Auditoria

`private.profile_access_history` preserva papel/ativação anterior e novo, motivo, ator, request ID e instante. `private.audit_entries` registra somente ação e campos alterados, sem copiar nomes, e-mails ou justificativas.

Eventos duráveis:

- `ProfileRoleChanged`;
- `ProfileActivationChanged`.

O nome atualizado é auditado, mas não precisa de outbox nesta fase.
