# Glossário do domínio — Livre Acesso

Este documento mantém uma linguagem comum entre instituição, análise, design, desenvolvimento e testes. Termos ambíguos devem ser resolvidos aqui antes de virarem nomes de tabela, endpoint ou componente.

## Termos principais

### Participante / aluno (`Student`)

Pessoa que participa ou pretende participar de uma atividade. O termo de interface preferido é **aluno**, acompanhando a linguagem atual do projeto. Pode ser criança, adolescente, jovem ou adulto.

### Responsável (`Guardian`)

Pessoa de referência legal ou operacional para contato. Para participantes adultos, deve ser decidido se o próprio aluno pode assumir esse papel ou se haverá um conceito separado de contato de emergência.

### Modalidade (`Modality`)

Tipo de atividade oferecida, como balé, jiu-jítsu ou bateria. Modalidade não é sinônimo de turma: uma modalidade pode possuir várias turmas.

### Turma (`Class`)

Oferta concreta de uma modalidade, com capacidade, faixa/nível, horário, local, instrutores e situação próprios.

### Matrícula (`Enrollment`)

Vínculo entre aluno e turma. Deve possuir período e situação, preservando o histórico em vez de apagar o vínculo anterior.

Situações candidatas: `ACTIVE`, `WAITING`, `PAUSED`, `CANCELLED`, `COMPLETED`. A lista definitiva será validada com a instituição.

### Sessão de chamada (`AttendanceSession`)

Ocorrência de uma aula de determinada turma em uma data. É aberta, preenchida, revisada e concluída.

### Registro de presença (`AttendanceRecord`)

Situação de um aluno em uma sessão de chamada: presente, ausente ou ausência justificada. Alterações posteriores devem ser auditadas.

### Falta consecutiva

Sequência de ausências segundo uma regra aprovada. Ainda precisa ser definido se falta justificada interrompe, conta ou é ignorada na sequência.

### Inatividade

Condição que exige revisão humana quando o aluno permanece sem presença por um período. Inatividade detectada não deve cancelar matrícula automaticamente sem uma regra institucional formal.

### Capacidade

Quantidade máxima de matrículas ativas permitida em uma turma. Não deve ser confundida com quantidade de pessoas presentes em uma aula específica.

### Vaga

Capacidade disponível para uma nova matrícula. Uma ausência isolada não cria vaga.

### Lista de espera (`WaitingList`)

Conjunto ordenado de candidatos a uma vaga de uma turma/modalidade. Deve registrar data de entrada, situação, critérios aplicados e histórico.

### Processo de preenchimento de vaga (`VacancyProcess`)

Processo auditável iniciado quando existe vaga confirmada. Pode usar ordem de inscrição, critérios ou seleção definida pela instituição. A palavra “sorteio” só deve ser usada se o método oficial for realmente aleatório e aprovado.

### Comunicado (`Communication`)

Mensagem institucional enviada a um público definido, por exemplo responsáveis de uma turma. O sistema precisa distinguir criação, envio, entrega e leitura.

### Entrega

Confirmação técnica de que o provedor aceitou ou entregou a mensagem. Não significa necessariamente leitura humana.

### Leitura

Evento fornecido pelo canal quando tecnicamente disponível. Não deve ser inferido apenas porque a mensagem foi enviada.

### Alerta

Sinal de que uma situação merece análise da equipe. Um alerta não deve executar automaticamente uma decisão de alto impacto, como cancelar matrícula, sem autorização explícita.

### Auditoria (`AuditEntry`)

Registro de quem realizou uma ação relevante, quando, sobre qual entidade e com qual resultado. Não deve copiar desnecessariamente o conteúdo sensível alterado.

## Regras já adotadas na fundação

1. CPF é normalizado para 11 dígitos e validado por dígitos verificadores.
2. CPF duplicado é rejeitado no caso de uso e também deverá possuir constraint única no banco.
3. CPF e telefone são mascarados na listagem inicial.
4. logs de evento não contêm nome, CPF, telefone ou e-mail.
5. eventos representam fatos passados.
6. datas de nascimento futuras ou incompatíveis com idade humana são rejeitadas.
7. dados atuais vivem somente em memória e não podem ser considerados persistidos.

## Decisões pendentes com a instituição

- CPF é obrigatório para todas as idades?
- quais dados do responsável são indispensáveis?
- como representar participante adulto?
- uma pessoa pode ser responsável por vários alunos?
- um aluno pode possuir mais de um responsável?
- qual é a regra de falta consecutiva?
- qual prazo caracteriza possível inatividade?
- quem confirma cancelamento e abertura de vaga?
- qual critério define a ordem da lista de espera?
- existe sorteio real ou apenas seleção por regra?
- quais canais de comunicação são oficiais?
- o provedor escolhido comprova entrega e leitura?
- quais perfis podem ver CPF e contato completo?
- por quanto tempo cada categoria de dado deve ser mantida?

Nenhuma dessas decisões deve ser preenchida por suposição técnica. O sistema deve refletir uma política validada pela instituição.
