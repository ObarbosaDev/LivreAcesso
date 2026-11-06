"""Conceitos do instituto compartilhados entre módulos de domínio."""

from enum import StrEnum


class Unit(StrEnum):
    """Unidade física onde uma turma acontece."""

    CEILANDIA = "ceilandia"
    AGUA_QUENTE = "agua_quente"
