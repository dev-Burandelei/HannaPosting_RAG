
import sqlite3

import pytest


def create_environment(database):
    database.execute(
        """
        INSERT INTO environments (
            id, name, status, created_at, updated_at
        )
        VALUES (
            'env-001', 'Ambiente de teste',
            'active', '2026-11-16', '2026-11-16'
        )
        """
    )


def create_brand(database):
    database.execute(
        """
        INSERT INTO brands (
            id, environment_id, name,
            is_default, is_active, created_at, updated_at
        )
        VALUES (
            'brand-001', 'env-001', 'Marca de teste',
            0, 1, '2026-11-16', '2026-11-16'
        )
        """
    )


def create_user(database):
    database.execute(
        """
        INSERT INTO users (
            id, environment_id, name, email, created_at
        )
        VALUES (
            'user-001', 'env-001', 'Usuário de teste',
            'teste@example.com', '2026-11-16'
        )
        """
    )


def create_content_request(database):
    database.execute(
        """
        INSERT INTO content_requests (
            id, brand_id, profile_snapshot_json,
            operation, platforms, created_at, updated_at
        )
        VALUES (
            'request-001', 'brand-001', '{}',
            'create', '["instagram"]',
            '2026-11-16', '2026-11-16'
        )
        """
    )


def create_post(database):
    database.execute(
        """
        INSERT INTO posts (
            id, request_id, brand_id, platform,
            status, created_at, updated_at
        )
        VALUES (
            'post-001', 'request-001', 'brand-001',
            'instagram', 'draft',
            '2026-11-16', '2026-11-16'
        )
        """
    )


def create_post_version(database):
    database.execute(
        """
        INSERT INTO post_versions (
            id, post_id, brand_id, version_number,
            content, origin_type, created_at, created_by
        )
        VALUES (
            'version-001', 'post-001', 'brand-001',
            1, 'Conteúdo de teste', 'generated',
            '2026-11-16', NULL
        )
        """
    )


@pytest.fixture
def approval_context(database):
    create_environment(database)
    create_brand(database)
    create_user(database)
    create_content_request(database)
    create_post(database)
    create_post_version(database)

    return database


def create_approval(
    database,
    approval_id,
    decision="approved",
    version_id="version-001",
    created_by=None,
):
    database.execute(
        """
        INSERT INTO approvals (
            id, version_id, decision,
            comment, created_by, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            approval_id,
            version_id,
            decision,
            "Comentário de teste",
            created_by,
            "2026-11-16",
        ),
    )


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_approval_accepts_valid_decisions(approval_context, decision):
    database = approval_context

    create_approval(database, f"approval-{decision}", decision)


def test_approval_rejects_invalid_decision(approval_context):
    database = approval_context

    with pytest.raises(sqlite3.IntegrityError):
        create_approval(database, "approval-invalid", "pending")


def test_approval_requires_version_id(approval_context):
    database = approval_context

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO approvals (
                id, version_id, decision, created_at
            )
            VALUES ('approval-001', NULL, 'approved', '2026-11-16')
            """
        )


def test_approval_rejects_nonexistent_version(approval_context):
    database = approval_context

    with pytest.raises(sqlite3.IntegrityError):
        create_approval(
            database,
            "approval-002",
            version_id="version-inexistente",
        )


def test_approval_accepts_existing_user(approval_context):
    database = approval_context

    create_approval(
        database,
        "approval-003",
        created_by="user-001",
    )


def test_approval_rejects_nonexistent_user(approval_context):
    database = approval_context

    with pytest.raises(sqlite3.IntegrityError):
        create_approval(
            database,
            "approval-004",
            created_by="user-inexistente",
        )


def test_approval_can_exist_without_user(approval_context):
    database = approval_context

    create_approval(
        database,
        "approval-005",
        created_by=None,
    )


def test_deleting_user_preserves_approval(approval_context):
    database = approval_context

    create_approval(
        database,
        "approval-006",
        created_by="user-001",
    )

    database.execute(
        "DELETE FROM users WHERE id = ?",
        ("user-001",),
    )

    result = database.execute(
        """
        SELECT created_by
        FROM approvals
        WHERE id = ?
        """,
        ("approval-006",),
    ).fetchone()

    assert result[0] is None


def test_approval_history_allows_multiple_decisions(approval_context):
    database = approval_context

    create_approval(database, "approval-007", "approved")
    create_approval(database, "approval-008", "rejected")

    result = database.execute(
        """
        SELECT COUNT(*)
        FROM approvals
        WHERE version_id = ?
        """,
        ("version-001",),
    ).fetchone()

    assert result[0] == 2


def test_approval_cannot_be_deleted_with_version(approval_context):
    database = approval_context

    create_approval(database, "approval-009")

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM post_versions WHERE id = ?",
            ("version-001",),
        )
