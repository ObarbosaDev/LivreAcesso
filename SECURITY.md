# Política de segurança

## Estado de suporte

O Livre Acesso está em desenvolvimento acadêmico e ainda não foi aprovado para operação com dados reais. A versão atual não possui autenticação, autorização nem persistência definitiva e, portanto, não deve ser exposta publicamente.

| Versão | Suporte | Uso permitido |
| --- | --- | --- |
| `0.x` | Desenvolvimento ativo | Ambiente local, com dados totalmente fictícios. |
| Produção | Indisponível | Não autorizado nesta fase. |

## Como relatar uma vulnerabilidade

Não publique detalhes exploráveis, credenciais ou dados pessoais em issues, pull requests, commits, grupos abertos ou capturas de tela.

Relate de forma privada à coordenação da equipe HumaniTec pelos canais internos definidos pela turma. Inclua, quando seguro:

- componente e versão afetados;
- descrição do impacto;
- passos mínimos para reprodução com dados fictícios;
- evidência sanitizada;
- mitigação sugerida, se conhecida.

A equipe deve confirmar o recebimento, avaliar severidade, limitar o acesso ao relato e preparar correção antes de qualquer divulgação.

## Informações proibidas no repositório

- arquivos `.env` de qualquer tipo;
- tokens, senhas, chaves privadas ou strings de conexão;
- CPF, telefone, e-mail, endereço ou dados de saúde reais;
- exportações de banco da instituição;
- logs de produção não sanitizados;
- backups, planilhas, formulários ou screenshots com PII;
- cookies, sessões ou credenciais de provedores.

Se um segredo for versionado, removê-lo do arquivo não é suficiente: ele deve ser revogado/rotacionado imediatamente e o incidente precisa ser registrado.

## Requisitos antes de um piloto

- autenticação e recuperação de acesso;
- autorização por papel no back-end;
- HTTPS obrigatório;
- auditoria de leitura e alteração de dados sensíveis;
- política de senha/sessão e revogação;
- banco com backup e restauração testada;
- proteção contra enumeração e abuso;
- validação de entrada e limites de requisição;
- tratamento seguro de erros;
- dependências verificadas;
- política de retenção e descarte aprovada;
- revisão de integrações externas e contratos;
- teste de segurança e plano de resposta a incidentes.

## Princípios de privacidade

1. **Finalidade:** cada dado coletado precisa de um uso institucional legítimo.
2. **Necessidade:** não coletar “para usar talvez no futuro”.
3. **Acesso mínimo:** cada perfil visualiza apenas o necessário.
4. **Rastreabilidade:** ações sensíveis devem ser auditáveis.
5. **Retenção limitada:** dados não são mantidos indefinidamente sem justificativa.
6. **Ambientes separados:** desenvolvimento e testes usam somente dados sintéticos.
7. **Logs seguros:** identificadores técnicos substituem PII sempre que possível.

## Dependências e integrações

Novas dependências devem possuir versão exata, origem confiável, manutenção ativa e justificativa. Integrações de mensagens não podem prometer “leitura confirmada” sem que o provedor ofereça esse evento de forma contratual e tecnicamente verificável.
