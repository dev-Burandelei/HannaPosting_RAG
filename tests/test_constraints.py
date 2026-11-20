
import sqlite3
import pytest


def create_environment(database, environment_id="env-001"):
    database.execute(
        """
        INSERT INTO environments (
            id, name, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            environment_id,
            "Ambiente de teste",
            "active",
            "2026-11-16",
            "2026-11-16",
        ),
    )


def create_brand(
    database,
    brand_id,
    environment_id="env-001",
    is_default=0,
):
    database.execute(
        """
        INSERT INTO brands (
            id, environment_id, name, is_default,
            is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brand_id,
            environment_id,
            f"Marca {brand_id}",
            is_default,
            1,
            "2026-11-16",
            "2026-11-16",
        ),
    )


def test_environment_rejects_invalid_status(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO environments (
                id, name, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "env-invalid",
                "Ambiente inválido",
                "deleted",
                "2026-11-16",
                "2026-11-16",
            ),
        )


def test_environment_rejects_null_name(database):
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO environments (
                id, name, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "env-null",
                None,
                "active",
                "2026-11-16",
                "2026-11-16",
            ),
        )


def test_brand_rejects_invalid_boolean(database):
    create_environment(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_brand(
            database,
            brand_id="brand-invalid",
            is_default=2,
        )


def test_only_one_default_brand_per_environment(database):
    create_environment(database)

    create_brand(
        database,
        brand_id="brand-001",
        is_default=1,
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_brand(
            database,
            brand_id="brand-002",
            is_default=1,
        )


def test_multiple_non_default_brands_are_allowed(database):
    create_environment(database)

    create_brand(database, "brand-001", is_default=0)
    create_brand(database, "brand-002", is_default=0)

    result = database.execute(
        "SELECT COUNT(*) FROM brands"
    ).fetchone()[0]

    assert result == 2
