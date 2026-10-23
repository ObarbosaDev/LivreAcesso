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


SUPABASE_TESTS_DIR = PROJECT_ROOT / "supabase" / "tests"
SUPABASE_SQL_TESTS = tuple(sorted(SUPABASE_TESTS_DIR.glob("*.sql")))


@pytest.mark.parametrize("sql_test", SUPABASE_SQL_TESTS, ids=lambda path: path.name)
def test_supabase_sql_tests_have_valid_postgresql_syntax(sql_test: Path) -> None:
    statements = parse_sql(sql_test.read_text(encoding="utf-8"))

    assert statements, f"O teste SQL {sql_test.name} não possui comandos."


@pytest.mark.parametrize("sql_test", SUPABASE_SQL_TESTS, ids=lambda path: path.name)
def test_permission_matrices_always_roll_back(sql_test: Path) -> None:
    sql = sql_test.read_text(encoding="utf-8").strip().lower()

    assert "\nbegin;" in sql
    assert "\nrollback;" in sql
    assert "\ncommit;" not in sql
    assert "permission checks passed" in sql


def test_permission_matrix_counts_are_explicit() -> None:
    student_matrix = (SUPABASE_TESTS_DIR / "role_matrix.sql").read_text(encoding="utf-8")
    profile_matrix = (SUPABASE_TESTS_DIR / "profile_role_matrix.sql").read_text(encoding="utf-8")
    guardian_matrix = (SUPABASE_TESTS_DIR / "guardian_role_matrix.sql").read_text(encoding="utf-8")

    assert "25/25 permission checks passed" in student_matrix
    assert "31/31 profile permission checks passed" in profile_matrix
    assert "35/35 guardian permission checks passed" in guardian_matrix


def test_health_check_is_public_constant_and_security_invoker() -> None:
    migration = MIGRATIONS_DIR / "20261021000500_health_check.sql"
    sql = " ".join(migration.read_text(encoding="utf-8").lower().split())

    assert "function public.health_check()" in sql
    assert "security invoker" in sql
    assert "grant execute on function public.health_check() to anon, authenticated" in sql
    assert "from public.students" not in sql
    assert "from public.profiles" not in sql


def test_profile_management_protects_last_active_coordinator() -> None:
    migration = MIGRATIONS_DIR / "20261021000600_profile_management.sql"
    sql = " ".join(migration.read_text(encoding="utf-8").lower().split())

    assert "private.profile_access_history" in sql
    assert "last_active_coordinator" in sql
    assert "where role = 'coordinator' and active order by id for update" in sql
    assert "p_expected_updated_at" in sql


def test_my_profile_uses_invoker_and_excludes_auth_secrets() -> None:
    migration = MIGRATIONS_DIR / "20261021000600_profile_management.sql"
    sql = " ".join(migration.read_text(encoding="utf-8").lower().split())
    function_start = sql.index("function public.get_my_profile")
    function_body = sql[function_start : function_start + 2_000]

    assert "security invoker" in function_body
    assert "auth.uid()" in function_body
    assert "encrypted_password" not in sql
    assert "raw_user_meta_data" not in sql
    assert "service_role" not in sql


def test_profile_admin_rpcs_have_role_checks_and_no_anon_grants() -> None:
    migration = MIGRATIONS_DIR / "20261021000600_profile_management.sql"
    sql = " ".join(migration.read_text(encoding="utf-8").lower().split())

    for function_name in (
        "get_profile_detail",
        "list_profiles",
        "change_profile_role",
        "change_profile_activation",
    ):
        function_start = sql.index(f"function public.{function_name}")
        function_body = sql[function_start : function_start + 13_000]
        assert "security definer" in function_body
        assert "private.has_any_role" in function_body

    assert "from public, anon" in sql
    assert "grant execute on function public.list_profiles" in sql


def test_pending_profile_cannot_be_active_in_database() -> None:
    migration = MIGRATIONS_DIR / "20261021000600_profile_management.sql"
    sql = " ".join(migration.read_text(encoding="utf-8").lower().split())

    assert "constraint profiles_pending_inactive" in sql
    assert "role <> 'pending' or not active" in sql


def test_guardian_management_preserves_primary_and_history() -> None:
    migration = MIGRATIONS_DIR / "20261022000700_guardian_management.sql"
    sql = " ".join(migration.read_text(encoding="utf-8").lower().split())

    assert "private.guardian_change_history" in sql
    assert "student_guardians_one_active_primary" in sql
    assert "student_guardians_require_primary" in sql
    assert "deferrable initially deferred" in sql
    assert "p_expected_student_updated_at" in sql
    assert "p_expected_guardian_updated_at" in sql
    assert "delete from public.guardians" not in sql
    assert "delete from public.student_guardians" not in sql
    assert "revoke all on function public.update_student_with_guardian" in sql


def test_guardian_rpcs_are_authorized_and_do_not_expose_tables() -> None:
    migration = MIGRATIONS_DIR / "20261022000700_guardian_management.sql"
    sql = " ".join(migration.read_text(encoding="utf-8").lower().split())

    for function_name in (
        "update_student",
        "list_student_guardians",
        "get_student_guardian_detail",
        "add_student_guardian",
        "update_student_guardian",
        "set_primary_student_guardian",
        "unlink_student_guardian",
    ):
        function_start = sql.index(f"function public.{function_name}(")
        function_body = sql[function_start : function_start + 16_000]
        assert "security definer" in function_body
        assert "set search_path = ''" in function_body
        assert "private.has_any_role" in function_body

    assert "grant execute on function public.list_student_guardians" in sql
    assert "grant execute on function public.unlink_student_guardian" in sql
    assert "grant select on table public.guardians" not in sql


def test_guardian_list_is_masked_and_sensitive_detail_is_audited() -> None:
    migration = MIGRATIONS_DIR / "20261022000700_guardian_management.sql"
    sql = " ".join(migration.read_text(encoding="utf-8").lower().split())

    assert "'phone_masked'" in sql
    assert "'email_masked'" in sql
    assert "guardian.sensitive_viewed" in sql
    assert "'student_guardian.' || p_action" in sql
    assert "jsonb_build_object( 'student_id', p_student_id, 'guardian_id', p_guardian_id" in sql
