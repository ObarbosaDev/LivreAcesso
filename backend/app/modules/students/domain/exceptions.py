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


class InvalidGuardianUnlinkReasonError(StudentDomainError):
    code = "invalid_guardian_unlink_reason"

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


class GuardianNotFoundError(StudentDomainError):
    code = "guardian_not_found"

    def __init__(self) -> None:
        super().__init__("O responsável vinculado não foi encontrado.")


class GuardianAlreadyLinkedError(StudentDomainError):
    code = "guardian_already_linked"

    def __init__(self) -> None:
        super().__init__("Este responsável já está vinculado ao aluno.")


class PrimaryGuardianRequiredError(StudentDomainError):
    code = "primary_guardian_required"

    def __init__(self) -> None:
        super().__init__("Defina outro responsável principal antes de desvincular este contato.")


class StudentVersionConflictError(StudentDomainError):
    code = "student_version_conflict"

    def __init__(self) -> None:
        super().__init__(
            "O cadastro foi alterado por outra pessoa. Atualize os dados e tente novamente."
        )


class GuardianVersionConflictError(StudentDomainError):
    code = "guardian_version_conflict"

    def __init__(self) -> None:
        super().__init__(
            "O responsável foi alterado por outra pessoa. Atualize os dados e tente novamente."
        )
