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


class DuplicateCPFError(StudentDomainError):
    code = "duplicate_cpf"

    def __init__(self) -> None:
        super().__init__("Já existe um aluno cadastrado com este CPF.")
