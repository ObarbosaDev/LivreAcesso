"""Erros estáveis do domínio de matrículas."""

from backend.app.shared.application.exceptions import ApplicationError


class EnrollmentError(ApplicationError):
    code = "enrollment_error"
    status_code = 422


class EnrollmentNotFoundError(EnrollmentError):
    code = "enrollment_not_found"
    status_code = 404


class DuplicateEnrollmentError(EnrollmentError):
    code = "duplicate_enrollment"
    status_code = 409


class ClassCapacityReachedError(EnrollmentError):
    code = "class_capacity_reached"
    status_code = 409


class EnrollmentVersionConflictError(EnrollmentError):
    code = "enrollment_version_conflict"
    status_code = 409
