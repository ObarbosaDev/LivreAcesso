"""Erros esperados do catálogo de modalidades e turmas."""


class ClassDomainError(Exception):
    """Base para violações de regras que podem ser explicadas à pessoa usuária."""

    code = "class_domain_error"


class InvalidModalityDataError(ClassDomainError):
    code = "invalid_modality_data"


class InvalidClassDataError(ClassDomainError):
    code = "invalid_class_data"


class InvalidScheduleError(ClassDomainError):
    code = "invalid_class_schedule"


class InvalidCapacityError(ClassDomainError):
    code = "invalid_class_capacity"

    def __init__(self) -> None:
        super().__init__("A capacidade deve estar entre 1 e 500 participantes.")


class InvalidClassChangeReasonError(ClassDomainError):
    code = "invalid_class_change_reason"

    def __init__(self) -> None:
        super().__init__("Informe um motivo entre 10 e 500 caracteres.")


class DuplicateModalityError(ClassDomainError):
    code = "duplicate_modality"

    def __init__(self) -> None:
        super().__init__("Já existe uma modalidade com este nome.")


class DuplicateClassError(ClassDomainError):
    code = "duplicate_class"

    def __init__(self) -> None:
        super().__init__("Já existe uma turma com este nome nesta modalidade.")


class ModalityNotFoundError(ClassDomainError):
    code = "modality_not_found"

    def __init__(self) -> None:
        super().__init__("A modalidade não foi encontrada.")


class ClassNotFoundError(ClassDomainError):
    code = "class_not_found"

    def __init__(self) -> None:
        super().__init__("A turma não foi encontrada.")


class ModalityVersionConflictError(ClassDomainError):
    code = "modality_version_conflict"

    def __init__(self) -> None:
        super().__init__("A modalidade foi alterada. Atualize os dados e tente novamente.")


class ClassVersionConflictError(ClassDomainError):
    code = "class_version_conflict"

    def __init__(self) -> None:
        super().__init__("A turma foi alterada. Atualize os dados e tente novamente.")


class InvalidInstructorAssignmentError(ClassDomainError):
    code = "invalid_instructor_assignment"

    def __init__(self) -> None:
        super().__init__("Toda pessoa atribuída precisa ser um instrutor ativo.")


class ActiveClassesExistError(ClassDomainError):
    code = "active_classes_exist"

    def __init__(self) -> None:
        super().__init__("Desative as turmas ativas antes de desativar a modalidade.")
