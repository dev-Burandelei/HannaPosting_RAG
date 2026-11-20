
import sqlite3
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT_DIR / "schema.sql"


@pytest.fixture
def database(tmp_path):
    """
    Cria um banco SQLite temporário e executa o DDL.
    O banco é descartado ao final de cada teste.
    """

    if not SCHEMA_FILE.exists():
        pytest.fail(f"Arquivo SQL não encontrado: {SCHEMA_FILE}")

    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8-sig")

    db_path = tmp_path / "test_database.db"
    connection = sqlite3.connect(db_path)

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema_sql)

        yield connection

    finally:
        connection.close()
