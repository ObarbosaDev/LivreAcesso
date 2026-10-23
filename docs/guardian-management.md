# Gestão de responsáveis do aluno

## Objetivo

O BL-03 amplia o cadastro inicial para permitir vários responsáveis por aluno sem duplicar a mesma pessoa quando irmãos compartilham contato. O vínculo guarda parentesco, preferência de comunicação e qual contato é o principal.

Responsável não é matrícula, usuário do sistema nem papel de autorização. Senhas continuam exclusivamente no Supabase Auth.

## Invariantes

- todo aluno mantém exatamente um responsável principal ativo;
- um responsável pode estar ligado a vários alunos pelo mesmo UUID;
- somente vínculo ativo aparece nas consultas operacionais;
- desvinculação é lógica e exige motivo entre 10 e 500 caracteres;
- o responsável principal não pode ser desvinculado antes da promoção de outro;
- CPF e status do aluno não são alterados por operações de responsável;
- contato compartilhado e vínculo possuem controles de concorrência independentes;
- eventos e logs transportam somente IDs e nomes de campos, nunca nome, telefone, e-mail ou motivo.

A constraint trigger `student_guardians_require_primary` é diferida até o fim da transação. Isso permite rebaixar o principal antigo e promover o novo atomicamente, sem aceitar um estado final sem principal.

## Parentescos aceitos

| API | PostgreSQL | Uso |
| --- | --- | --- |
| `contato_responsavel` | `responsible_contact` | Contato inicial sem presumir guarda legal. |
| `responsavel_legal` | `legal_guardian` | Guarda legal confirmada pela instituição. |
| `pai_ou_mae` | `parent` | Pai ou mãe informado no cadastro. |
| `contato_emergencia` | `emergency_contact` | Pessoa acionada em emergência. |
| `proprio` | `self` | Participante responsável pelo próprio contato. |
| `outro` | `other` | Relação válida não coberta pelas anteriores. |

O cadastro inicial usa `contato_responsavel`. Uma pessoa autorizada deve alterar o parentesco somente após confirmação; o sistema não presume relação familiar.

## Contratos HTTP

Todas as rotas usam o prefixo `/api/v1/students/{student_id}/guardians` e exigem Bearer JWT.

| Método e caminho | Finalidade | Dados sensíveis |
| --- | --- | --- |
| `GET /` | Lista vínculos ativos, principal primeiro. | Telefone e e-mail mascarados. |
| `POST /` | Cria contato ou reutiliza `existing_guardian_id`. | Retorna o contato integral criado/vinculado. |
| `GET /{guardian_id}` | Consulta um vínculo específico. | Telefone e e-mail integrais; leitura auditada. |
| `PUT /{guardian_id}` | Atualiza contato e propriedades do vínculo. | Exige versões do aluno e responsável. |
| `POST /{guardian_id}/primary` | Troca o contato principal. | Não altera dados pessoais. |
| `POST /{guardian_id}/unlink` | Desvincula contato não principal. | Motivo fica somente no histórico privado. |

Para adicionar, o cliente informa exatamente uma origem:

- `guardian`: cria um contato com UUID gerado pelo backend; ou
- `existing_guardian_id`: reutiliza uma pessoa já conhecida, sem reenviar ou sobrescrever seus dados.

## Concorrência

`expected_student_updated_at` protege parentesco, comunicação, principal e conjunto de vínculos. `expected_guardian_updated_at` protege nome, telefone e e-mail, pois essas informações podem ser compartilhadas por irmãos.

Uma versão obsoleta retorna `409` com `student_version_conflict` ou `guardian_version_conflict`. A interface futura deve atualizar os dados e pedir confirmação antes de reenviar.

## Privacidade e autorização

Coordenação e recepção podem consultar detalhes e administrar vínculos. Consulta pode usar somente a lista mascarada. Instrutor e perfil pendente/inativo são recusados pelas RPCs.

As tabelas `students`, `guardians` e `student_guardians` continuam sem grants diretos para `anon` ou `authenticated`. `private.guardian_change_history`, auditoria e outbox permanecem fora da Data API comum.

## Persistência e evidências

A migration `20261022000700_guardian_management.sql` foi aplicada ao projeto de São Paulo. Ela cria o ciclo lógico do vínculo, histórico privado, RPC de edição exclusiva do aluno e as RPCs de responsáveis. A RPC antiga que editava aluno e responsável em conjunto perdeu permissão de `authenticated`.

A matriz `guardian_role_matrix.sql` aprovou 35/35 combinações e o ciclo completo de inclusão, edição, troca de principal, mascaramento e desvinculação. O rollback foi confirmado: zero alunos, zero responsáveis, zero vínculos, zero históricos e uma coordenação ativa.

O deployment de produção `dpl_8Lgdnu3EGQFwCV74FePscWCCtGiu` está Ready em `gru1`; live, ready e bloqueio 401 da nova rota foram aprovados. O smoke final com JWT real permanece pendente antes de encerrar o bloco.
