
import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "schema.sql"

load_dotenv(ROOT_DIR / ".env")

DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", "data/post.db")
)

if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = ROOT_DIR / DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """
    Abre uma conexão com o banco SQLite e aplica as configurações.
    """

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=5.0,
    )

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA synchronous = FULL")

    return connection


def initialize_database() -> None:
    """
    Inicializa o banco usando schema.sql.

    Não executa novamente o DDL se o banco já estiver completo.
    Interrompe a operação se encontrar uma estrutura parcial
    ou inesperada.
    """

    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError(
            f"Arquivo SQL não encontrado: {SCHEMA_PATH}"
        )

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8-sig")

    patterns = {
        "table": r"^\s*CREATE\s+TABLE\s+(\w+)",
        "index": r"^\s*CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)",
        "trigger": r"^\s*CREATE\s+TRIGGER\s+(\w+)",
    }

    expected = {
        object_type: set(
            re.findall(pattern, schema_sql, re.IGNORECASE | re.MULTILINE)
        )
        for object_type, pattern in patterns.items()
    }

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT type, name
            FROM sqlite_master
            WHERE
                (type = 'table' AND name NOT LIKE 'sqlite_%')
                OR
                (type IN ('index', 'trigger') AND sql IS NOT NULL)
        """).fetchall()

        existing = {
            object_type: {
                name
                for db_type, name in rows
                if db_type == object_type
            }
            for object_type in patterns
        }

        if not any(existing.values()):
            connection.executescript(schema_sql)

            rows = connection.execute("""
                SELECT type, name
                FROM sqlite_master
                WHERE
                    (type = 'table' AND name NOT LIKE 'sqlite_%')
                    OR
                    (type IN ('index', 'trigger') AND sql IS NOT NULL)
            """).fetchall()

            existing = {
                object_type: {
                    name
                    for db_type, name in rows
                    if db_type == object_type
                }
                for object_type in patterns
            }

        for object_type in patterns:
            missing = expected[object_type] - existing[object_type]
            unexpected = existing[object_type] - expected[object_type]

            if missing or unexpected:
                raise RuntimeError(
                    f"Estrutura do banco inconsistente ({object_type}). "
                    f"Ausentes: {sorted(missing)}. "
                    f"Inesperados: {sorted(unexpected)}."
                )

    finally:
        connection.close()
