"""Objetos de valor validados do contexto de alunos."""

from dataclasses import dataclass

from backend.app.modules.students.domain.exceptions import InvalidCPFError, InvalidPhoneError


def _only_digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


@dataclass(frozen=True, slots=True)
class CPF:
    """CPF normalizado e validado pelos dígitos verificadores."""

    value: str

    def __post_init__(self) -> None:
        normalized = _only_digits(self.value)
        if not self._is_valid(normalized):
            raise InvalidCPFError
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def _is_valid(value: str) -> bool:
        if len(value) != 11 or value == value[0] * 11:
            return False

        numbers = [int(digit) for digit in value]
        first_digit = CPF._verification_digit(numbers[:9], range(10, 1, -1))
        second_digit = CPF._verification_digit(numbers[:10], range(11, 1, -1))
        return numbers[9] == first_digit and numbers[10] == second_digit

    @staticmethod
    def _verification_digit(numbers: list[int], weights: range) -> int:
        remainder = sum(number * weight for number, weight in zip(numbers, weights)) % 11
        return 0 if remainder < 2 else 11 - remainder

    @property
    def masked(self) -> str:
        return f"***.***.***-{self.value[-2:]}"


@dataclass(frozen=True, slots=True)
class Phone:
    """Telefone brasileiro armazenado somente com dígitos."""

    value: str

    def __post_init__(self) -> None:
        normalized = _only_digits(self.value)
        if len(normalized) not in {10, 11}:
            raise InvalidPhoneError
        object.__setattr__(self, "value", normalized)

    @property
    def masked(self) -> str:
        return f"({self.value[:2]}) *****-{self.value[-4:]}"
