
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


def create_content_request(database, status=None):
    if status is None:
        database.execute("""
            INSERT INTO content_requests (
                id, brand_id, profile_snapshot_json,
                operation, platforms, created_at, updated_at
            )
            VALUES (
                'request-001', 'brand-001', '{}',
                'create', '["instagram"]',
                '2026-11-16', '2026-11-16'
            )
        """)
    else:
        database.execute("""
            INSERT INTO content_requests (
                id, brand_id, profile_snapshot_json,
                operation, platforms, status,
                created_at, updated_at
            )
            VALUES (
                'request-001', 'brand-001', '{}',
                'create', '["instagram"]', ?,
                '2026-11-16', '2026-11-16'
            )
        """, (status,))


@pytest.mark.parametrize("status", [
    "pending",
    "processing",
    "completed",
    "failed",
    "cancelled",
])
def test_content_request_accepts_valid_status(database, status):
    create_brand(database)
    create_content_request(database, status)

    result = database.execute("""
        SELECT status FROM content_requests
        WHERE id = 'request-001'
    """).fetchone()

    assert result == (status,)


@pytest.mark.parametrize("status", [
    "approved",
    "waiting",
    "error",
    "invalid",
])
def test_content_request_rejects_invalid_status(database, status):
    create_brand(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_content_request(database, status)


def test_content_request_uses_pending_as_default_status(database):
    create_brand(database)
    create_content_request(database)

    result = database.execute("""
        SELECT status FROM content_requests
        WHERE id = 'request-001'
    """).fetchone()

    assert result == ("pending",)


def test_content_request_rejects_invalid_status_update(database):
    create_brand(database)
    create_content_request(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute("""
            UPDATE content_requests
            SET status = 'approved'
            WHERE id = 'request-001'
        """)
