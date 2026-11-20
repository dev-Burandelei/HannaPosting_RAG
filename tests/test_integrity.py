
import pytest


EXPECTED_TABLES = {
    "environments",
    "users",
    "brands",
    "brand_profiles",
    "brand_platform_profiles",
    "brand_profile_versions",
    "content_requests",
    "posts",
    "post_versions",
    "approvals",
    "validation_runs",
    "documents",
    "document_processings",
    "tags",
    "document_tags",
    "post_tags",
    "rag_index_records",
    "provider_configs",
    "jobs",
    "usage_logs",
    "audit_logs",
}


@pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
def test_table_has_primary_key(database, table_name):
    """Verifica se cada tabela possui pelo menos uma PK."""

    columns = database.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    primary_key_columns = [
        column for column in columns
        if column[5] > 0
    ]

    assert primary_key_columns, (
        f"A tabela {table_name} não possui chave primária."
    )


@pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES))
def test_table_exists(database, table_name):
    """Confirma a existência individual de cada tabela."""

    result = database.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,)
    ).fetchone()[0]

    assert result == 1
