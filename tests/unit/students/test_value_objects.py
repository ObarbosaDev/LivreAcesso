"""Testes unitários dos objetos de valor do módulo de alunos."""

import pytest

from backend.app.modules.students.domain.exceptions import InvalidCPFError, InvalidPhoneError
from backend.app.modules.students.domain.value_objects import CPF, Phone


def test_cpf_is_normalized_and_masked() -> None:
    cpf = CPF("529.982.247-25")

    assert cpf.value == "52998224725"
    assert cpf.masked == "***.***.***-25"


@pytest.mark.parametrize("value", ["", "111.111.111-11", "529.982.247-24"])
def test_invalid_cpf_is_rejected(value: str) -> None:
    with pytest.raises(InvalidCPFError):
        CPF(value)


def test_phone_is_normalized_without_exposing_full_number() -> None:
    phone = Phone("(61) 99999-1234")

    assert phone.value == "61999991234"
    assert phone.masked == "(61) *****-1234"


def test_invalid_phone_is_rejected() -> None:
    with pytest.raises(InvalidPhoneError):
        Phone("1234")
