"""Erros de negócio do contexto de alunos."""


class StudentDomainError(Exception):
    """Erro esperado causado pela violação de uma regra do domínio."""

    code = "student_domain_error"


class InvalidCPFError(StudentDomainError):
    code = "invalid_cpf"

    def __init__(self) -> None:
        super().__init__("O CPF informado é inválido.")


class InvalidPhoneError(StudentDomainError):
    code = "invalid_phone"

    def __init__(self) -> None:
        super().__init__("O telefone deve conter DDD e 10 ou 11 dígitos.")


class InvalidStudentDataError(StudentDomainError):
    code = "invalid_student_data"


class InvalidStatusReasonError(StudentDomainError):
    code = "invalid_status_reason"

    def __init__(self) -> None:
        super().__init__("Informe um motivo entre 10 e 500 caracteres.")


class DuplicateCPFError(StudentDomainError):
    code = "duplicate_cpf"

    def __init__(self) -> None:
        super().__init__("Já existe um aluno cadastrado com este CPF.")


class StudentNotFoundError(StudentDomainError):
    code = "student_not_found"

    def __init__(self) -> None:
        super().__init__("O cadastro do aluno não foi encontrado.")


class StudentVersionConflictError(StudentDomainError):
    code = "student_version_conflict"

    def __init__(self) -> None:
        super().__init__(
            "O cadastro foi alterado por outra pessoa. Atualize os dados e tente novamente."
        )
