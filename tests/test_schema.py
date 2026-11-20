
import sqlite3
from pathlib import Path

import pytest


# Localiza o arquivo SQL na raiz do projeto
ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT_DIR / "schema.sql"


# Tabelas esperadas no modelo lógico 1.0
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


@pytest.fixture
def database(tmp_path):
    """Cria um banco temporário e executa o DDL."""

    if not SCHEMA_FILE.exists():
        pytest.fail(f"Arquivo SQL não encontrado: {SCHEMA_FILE}")

    # Lê o DDL como UTF-8
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8-sig")

    # Cria banco temporário
    db_path = tmp_path / "test_database.db"
    connection = sqlite3.connect(db_path)

    try:
        # Executa as instruções SQL
        connection.executescript(schema_sql)

        yield connection

    finally:
        connection.close()


def test_schema_creation(database):
    """Verifica se todas as tabelas esperadas foram criadas."""

    cursor = database.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
    """)

    created_tables = {row[0] for row in cursor.fetchall()}

    assert created_tables == EXPECTED_TABLES


def test_foreign_keys_enabled(database):
    """Verifica se as chaves estrangeiras estão habilitadas."""

    result = database.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    assert result == 1


def test_database_integrity(database):
    """Verifica a integridade estrutural do banco."""

    result = database.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    assert result == "ok"


def test_foreign_key_integrity(database):
    """Verifica se existem violações de chaves estrangeiras."""

    violations = database.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    assert violations == []
