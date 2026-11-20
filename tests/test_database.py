import sqlite3

import pytest

import app.database as database


def get_object_counts(connection):
    counts = {}

    for object_type in ("table", "index", "trigger"):
        counts[object_type] = connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = ?
              AND sql IS NOT NULL
              AND name NOT LIKE 'sqlite_%'
            """,
            (object_type,),
        ).fetchone()[0]

    return counts


def test_get_connection_applies_pragmas(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "test.db"

    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    connection = database.get_connection()

    try:
        assert connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()[0] == 1

        assert connection.execute(
            "PRAGMA busy_timeout"
        ).fetchone()[0] == 5000

        assert connection.execute(
            "PRAGMA synchronous"
        ).fetchone()[0] == 2

        assert db_path.exists()

    finally:
        connection.close()


def test_initialize_database_creates_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"

    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    database.initialize_database()

    connection = database.get_connection()

    try:
        counts = get_object_counts(connection)

        assert counts == {
            "table": 21,
            "index": 20,
            "trigger": 9,
        }

        assert connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall() == []

        assert connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0] == "ok"

    finally:
        connection.close()


def test_initialize_database_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"

    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    database.initialize_database()

    connection = database.get_connection()

    try:
        first_counts = get_object_counts(connection)
    finally:
        connection.close()

    database.initialize_database()

    connection = database.get_connection()

    try:
        second_counts = get_object_counts(connection)

        assert second_counts == first_counts

    finally:
        connection.close()


def test_initialize_database_rejects_partial_schema(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "partial.db"

    monkeypatch.setattr(database, "DATABASE_PATH", db_path)

    connection = sqlite3.connect(db_path)

    connection.execute("""
        CREATE TABLE partial_test (
            id INTEGER PRIMARY KEY
        )
    """)

    connection.close()

    with pytest.raises(
        RuntimeError,
        match="Estrutura do banco inconsistente",
    ):
        database.initialize_database()

    connection = sqlite3.connect(db_path)

    try:
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
        """).fetchall()

        assert tables == [("partial_test",)]

    finally:
        connection.close()
