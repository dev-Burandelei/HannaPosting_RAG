
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


def create_content_request(database, snapshot):
    database.execute("""
        INSERT INTO content_requests (
            id, brand_id, profile_snapshot_json,
            operation, platforms, created_at, updated_at
        )
        VALUES (
            'request-001', 'brand-001', ?,
            'create', '["instagram"]',
            '2026-11-16', '2026-11-16'
        )
    """, (snapshot,))


@pytest.mark.parametrize("snapshot", [
    '{}',
    '{"brand": {}}',
    '{"brand": {}, "platforms": {}}',
])
def test_snapshot_accepts_json_objects(database, snapshot):
    create_brand(database)
    create_content_request(database, snapshot)


@pytest.mark.parametrize("snapshot", [
    '[]',
    '"texto"',
    '123',
    'true',
    'null',
])
def test_snapshot_rejects_non_object_json(database, snapshot):
    create_brand(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_content_request(database, snapshot)


def test_snapshot_rejects_invalid_json(database):
    create_brand(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_content_request(database, '{invalid json')


def test_snapshot_rejects_null(database):
    create_brand(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_content_request(database, None)


def test_snapshot_preserves_original_content(database):
    create_brand(database)

    original_snapshot = '{"brand": {"name": "Marca original"}}'
    create_content_request(database, original_snapshot)

    result = database.execute("""
        SELECT profile_snapshot_json
        FROM content_requests
        WHERE id = 'request-001'
    """).fetchone()

    assert result == (original_snapshot,)



def test_snapshot_rejects_modification(database):
    create_brand(database)

    original_snapshot = '{"brand": {"name": "Marca original"}}'
    create_content_request(database, original_snapshot)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute("""
            UPDATE content_requests
            SET profile_snapshot_json = ?
            WHERE id = 'request-001'
        """, ('{"brand": {"name": "Outra marca"}}',))


def test_snapshot_accepts_update_with_same_content(database):
    create_brand(database)

    original_snapshot = '{"brand": {"name": "Marca original"}}'
    create_content_request(database, original_snapshot)

    database.execute("""
        UPDATE content_requests
        SET profile_snapshot_json = ?
        WHERE id = 'request-001'
    """, (original_snapshot,))

    result = database.execute("""
        SELECT profile_snapshot_json
        FROM content_requests
        WHERE id = 'request-001'
    """).fetchone()

    assert result == (original_snapshot,)
