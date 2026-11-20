
import sqlite3
import pytest


def create_environment(database, environment_id):
    database.execute(
        """
        INSERT INTO environments (
            id, name, status, created_at, updated_at
        )
        VALUES (?, ?, 'active', '2026-11-16', '2026-11-16')
        """,
        (environment_id, f"Ambiente {environment_id}"),
    )


def create_brand(database, brand_id, environment_id):
    database.execute(
        """
        INSERT INTO brands (
            id, environment_id, name,
            is_default, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, 0, 1, '2026-11-16', '2026-11-16')
        """,
        (brand_id, environment_id, f"Marca {brand_id}"),
    )


def create_profile(database, profile_id, brand_id):
    database.execute(
        """
        INSERT INTO brand_profiles (
            id, brand_id, created_at, updated_at
        )
        VALUES (?, ?, '2026-11-16', '2026-11-16')
        """,
        (profile_id, brand_id),
    )


def create_profile_version(
    database, version_id, brand_id, profile_id
):
    database.execute(
        """
        INSERT INTO brand_profile_versions (
            id, brand_id, brand_profile_id,
            version_number, profile_data_json, created_at
        )
        VALUES (?, ?, ?, 1, '{}', '2026-11-16')
        """,
        (version_id, brand_id, profile_id),
    )


def create_content_request(
    database, request_id, brand_id, version_id=None
):
    database.execute(
        """
        INSERT INTO content_requests (
            id, brand_id, brand_profile_version_id,
            profile_snapshot_json, operation, platforms,
            created_at, updated_at
        )
        VALUES (?, ?, ?, '{}', 'create', '["instagram"]',
                '2026-11-16', '2026-11-16')
        """,
        (request_id, brand_id, version_id),
    )


def test_profile_version_accepts_its_own_brand(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")
    create_profile(database, "profile-001", "brand-001")

    create_profile_version(
        database,
        "version-001",
        "brand-001",
        "profile-001",
    )

    result = database.execute(
        """
        SELECT brand_id, brand_profile_id
        FROM brand_profile_versions
        WHERE id = ?
        """,
        ("version-001",),
    ).fetchone()

    assert result == ("brand-001", "profile-001")


def test_profile_version_rejects_profile_from_another_brand(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")
    create_brand(database, "brand-002", "env-001")

    create_profile(database, "profile-002", "brand-002")

    with pytest.raises(sqlite3.IntegrityError):
        create_profile_version(
            database,
            "version-001",
            "brand-001",
            "profile-002",
        )


def test_content_request_rejects_version_from_another_brand(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")
    create_brand(database, "brand-002", "env-001")

    create_profile(database, "profile-002", "brand-002")
    create_profile_version(
        database,
        "version-002",
        "brand-002",
        "profile-002",
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_content_request(
            database,
            "request-001",
            "brand-001",
            "version-002",
        )


def test_content_request_accepts_version_from_its_own_brand(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")

    create_profile(database, "profile-001", "brand-001")
    create_profile_version(
        database,
        "version-001",
        "brand-001",
        "profile-001",
    )

    create_content_request(
        database,
        "request-001",
        "brand-001",
        "version-001",
    )

    result = database.execute(
        """
        SELECT brand_id, brand_profile_version_id
        FROM content_requests
        WHERE id = ?
        """,
        ("request-001",),
    ).fetchone()

    assert result == ("brand-001", "version-001")


def test_content_request_accepts_null_profile_version(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")

    create_content_request(
        database,
        "request-001",
        "brand-001",
        None,
    )

    result = database.execute(
        """
        SELECT brand_id, brand_profile_version_id
        FROM content_requests
        WHERE id = ?
        """,
        ("request-001",),
    ).fetchone()

    assert result == ("brand-001", None)
