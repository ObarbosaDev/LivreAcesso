"""Guardas arquiteturais para migrations do Supabase."""

import re
from pathlib import Path

import pytest
from pglast import parse_sql

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "supabase" / "migrations"
MIGRATIONS = tuple(sorted(MIGRATIONS_DIR.glob("*.sql")))


@pytest.mark.parametrize("migration", MIGRATIONS, ids=lambda path: path.name)
def test_migration_has_valid_postgresql_syntax(migration: Path) -> None:
    """Garante que cada arquivo é aceito pelo parser oficial do PostgreSQL."""

    statements = parse_sql(migration.read_text(encoding="utf-8"))

    assert statements, f"A migration {migration.name} não possui comandos SQL."


def test_migration_names_are_orderable_timestamps() -> None:
    """Evita migrations fora de ordem ou com nomes que o CLI não reconhece."""

    assert MIGRATIONS, "O projeto precisa possuir ao menos uma migration."
    assert all(re.match(r"^\d{14}_[a-z0-9_]+\.sql$", path.name) for path in MIGRATIONS)


def test_migrations_are_explicit_transactions() -> None:
    """Uma falha de estrutura não pode deixar metade da migration aplicada."""

    for migration in MIGRATIONS:
        sql = migration.read_text(encoding="utf-8").strip().lower()
        assert sql.startswith("--") and "\nbegin;" in sql
        assert sql.endswith("commit;")


def test_personal_tables_are_not_granted_directly_to_client_roles() -> None:
    """Dados pessoais devem sair por RPC autorizada e mascarada, não por tabela."""

    unsafe_grant = re.compile(
        r"grant\b[^;]*\bon\s+table\s+public\."
        r"(?:students|guardians|student_guardians)\b[^;]*\bto\s+"
        r"(?:anon|authenticated)\b",
        flags=re.IGNORECASE,
    )

    for migration in MIGRATIONS:
        sql = migration.read_text(encoding="utf-8")
        assert unsafe_grant.search(sql) is None, (
            f"{migration.name} concede tabela pessoal diretamente a um papel cliente."
        )


def test_private_schema_is_revoked_from_client_roles() -> None:
    """Auditoria e outbox não podem ser consultadas pelo cliente autenticado."""

    expected_revoke = "revoke all on all tables in schema private from public, anon, authenticated;"

    for migration in MIGRATIONS:
        normalized_sql = " ".join(migration.read_text(encoding="utf-8").lower().split())
        if "create table private." in normalized_sql:
            assert expected_revoke in normalized_sql


def test_cpf_is_validated_inside_postgresql() -> None:
    sql = " ".join(
        " ".join(path.read_text(encoding="utf-8").lower().split()) for path in MIGRATIONS
    )

    assert "function private.is_valid_cpf" in sql
    assert "private.is_valid_cpf(cpf)" in sql
    assert "private.is_valid_cpf(v_cpf)" in sql


def test_student_search_preserves_total_for_empty_pages() -> None:
    sql = " ".join(
        " ".join(path.read_text(encoding="utf-8").lower().split()) for path in MIGRATIONS
    )

    assert "function public.list_students" in sql
    assert "returns jsonb" in sql
    assert "'items'" in sql
    assert "'total'" in sql


def test_student_management_uses_soft_lifecycle_and_optimistic_locking() -> None:
    sql = " ".join(
        " ".join(path.read_text(encoding="utf-8").lower().split()) for path in MIGRATIONS
    )

    assert "function public.get_student_detail" in sql
    assert "function public.update_student_with_guardian" in sql
    assert "function public.change_student_status" in sql
    assert "p_expected_updated_at" in sql
    assert "private.student_status_history" in sql
    assert "delete from public.students" not in sql


def test_sensitive_detail_and_status_change_are_audited() -> None:
    sql = " ".join(
        " ".join(path.read_text(encoding="utf-8").lower().split()) for path in MIGRATIONS
    )

    assert "student.sensitive_viewed" in sql
    assert "student.status_changed" in sql
    assert "student.updated" in sql
    assert "array['status']" in sql


def test_registration_returns_authoritative_database_timestamps() -> None:
    sql = " ".join(
        " ".join(path.read_text(encoding="utf-8").lower().split()) for path in MIGRATIONS
    )

    assert "function public.register_student_with_guardian_v2" in sql
    assert "'created_at'" in sql
    assert "'updated_at'" in sql
    assert "from authenticated" in sql


def test_profile_policy_uses_initplans_for_auth_checks() -> None:
    sql = " ".join(
        " ".join(path.read_text(encoding="utf-8").lower().split()) for path in MIGRATIONS
    )

    assert "id = (select auth.uid())" in sql
    assert "select private.has_any_role" in sql


def test_privileged_rpcs_have_empty_search_path_and_internal_role_checks() -> None:
    sql = " ".join(
        " ".join(path.read_text(encoding="utf-8").lower().split()) for path in MIGRATIONS
    )
    privileged_functions = (
        "register_student_with_guardian",
        "list_students",
        "get_student_detail",
        "update_student_with_guardian",
        "change_student_status",
    )

    for function_name in privileged_functions:
        function_start = sql.index(f"function public.{function_name}")
        function_body = sql[function_start : function_start + 12_000]
        assert "security definer" in function_body
        assert "set search_path = ''" in function_body
        assert "private.has_any_role" in function_body
