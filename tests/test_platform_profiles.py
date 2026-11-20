
import sqlite3
import pytest


def create_brand(database):
    database.execute("""
        INSERT INTO environments (
            id, name, status, created_at, updated_at
        )
        VALUES (
            'env-001', 'Ambiente de teste',
            'active', '2026-11-16', '2026-11-16'
        )
    """)

    database.execute("""
        INSERT INTO brands (
            id, environment_id, name,
            is_default, is_active, created_at, updated_at
        )
        VALUES (
            'brand-001', 'env-001', 'Marca de teste',
            0, 1, '2026-11-16', '2026-11-16'
        )
    """)


def create_platform_profile(database, preferred_formats):
    database.execute("""
        INSERT INTO brand_platform_profiles (
            id, brand_id, platform,
            preferred_formats, created_at, updated_at
        )
        VALUES (
            'platform-001', 'brand-001', 'instagram',
            ?, '2026-11-16', '2026-11-16'
        )
    """, (preferred_formats,))


@pytest.mark.parametrize("formats", [
    '["carrossel", "reels"]',
    '[]',
])
def test_platform_profile_accepts_json_arrays(database, formats):
    create_brand(database)
    create_platform_profile(database, formats)


@pytest.mark.parametrize("formats", [
    '{}',
    '"carrossel"',
    '123',
    'true',
])
def test_platform_profile_rejects_non_array_json(database, formats):
    create_brand(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_platform_profile(database, formats)


def test_platform_profile_accepts_null_preferred_formats(database):
    create_brand(database)
    create_platform_profile(database, None)

    result = database.execute("""
        SELECT preferred_formats
        FROM brand_platform_profiles
        WHERE id = 'platform-001'
    """).fetchone()

    assert result == (None,)


def test_platform_profile_rejects_invalid_json(database):
    create_brand(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_platform_profile(database, 'carrossel')
