
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
        (environment_id, environment_id),
    )


def create_user(database, user_id, environment_id):
    database.execute(
        """
        INSERT INTO users (
            id, environment_id, name, email, created_at
        )
        VALUES (?, ?, ?, ?, '2026-11-16')
        """,
        (
            user_id,
            environment_id,
            user_id,
            f"{user_id}@example.com",
        ),
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
        (brand_id, environment_id, brand_id),
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
    database,
    version_id,
    brand_id,
    profile_id,
    created_by=None,
    version_number=1,
):
    database.execute(
        """
        INSERT INTO brand_profile_versions (
            id, brand_id, brand_profile_id,
            version_number, profile_data_json,
            created_at, created_by
        )
        VALUES (?, ?, ?, ?, '{}', '2026-11-16', ?)
        """,
        (
            version_id,
            brand_id,
            profile_id,
            version_number,
            created_by,
        ),
    )



def create_content_request(database, request_id, brand_id):
    database.execute(
        """
        INSERT INTO content_requests (
            id, brand_id, profile_snapshot_json,
            operation, platforms, created_at, updated_at
        )
        VALUES (?, ?, '{}', 'create', '["instagram"]',
                '2026-11-16', '2026-11-16')
        """,
        (request_id, brand_id),
    )


def create_post(database, post_id, request_id, brand_id):
    database.execute(
        """
        INSERT INTO posts (
            id, request_id, brand_id, platform,
            status, created_at, updated_at
        )
        VALUES (?, ?, ?, 'instagram', 'draft',
                '2026-11-16', '2026-11-16')
        """,
        (post_id, request_id, brand_id),
    )


def create_post_version(
    database, version_id, post_id, brand_id, created_by=None
):
    database.execute(
        """
        INSERT INTO post_versions (
            id, post_id, brand_id, version_number,
            content, origin_type, created_at, created_by
        )
        VALUES (?, ?, ?, 1, 'Conteúdo de teste',
                'generated', '2026-11-16', ?)
        """,
        (version_id, post_id, brand_id, created_by),
    )


def create_approval(
    database, approval_id, version_id, created_by=None
):
    database.execute(
        """
        INSERT INTO approvals (
            id, version_id, decision, created_by, created_at
        )
        VALUES (?, ?, 'approved', ?, '2026-11-16')
        """,
        (approval_id, version_id, created_by),
    )


@pytest.fixture
def context(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_user(database, "user-001", "env-001")
    create_user(database, "user-002", "env-002")

    create_brand(database, "brand-001", "env-001")
    create_brand(database, "brand-002", "env-002")

    create_profile(database, "profile-001", "brand-001")
    create_profile(database, "profile-002", "brand-002")

    create_profile_version(
        database, "profile-version-001",
        "brand-001", "profile-001"
    )

    create_content_request(database, "request-001", "brand-001")
    create_post(database, "post-001", "request-001", "brand-001")

    return database


# BRAND PROFILE VERSIONS


def test_profile_version_accepts_user_from_same_environment(context):
    create_profile_version(
        context, "profile-version-004",
        "brand-001", "profile-001", None,
        version_number=3,
)


def test_profile_version_rejects_user_from_another_environment(context):
    with pytest.raises(sqlite3.IntegrityError):
        create_profile_version(
            context, "profile-version-003",
            "brand-001", "profile-001", "user-002"
        )


def test_profile_version_accepts_null_created_by(context):
    create_profile_version(
        context, "profile-version-004",
        "brand-001", "profile-001", None,
        version_number=3,
)


def test_profile_version_update_rejects_user_from_another_environment(
    context,
):
    create_profile_version(
        context, "profile-version-005",
        "brand-001", "profile-001", "user-001",
        version_number=4,
    )

    with pytest.raises(sqlite3.IntegrityError):
        context.execute(
            """
            UPDATE brand_profile_versions
            SET created_by = ?
            WHERE id = ?
            """,
            ("user-002", "profile-version-005"),
        )


# POST VERSIONS


def test_post_version_accepts_user_from_same_environment(context):
    create_post_version(
        context, "version-001", "post-001",
        "brand-001", "user-001"
    )


def test_post_version_rejects_user_from_another_environment(context):
    with pytest.raises(sqlite3.IntegrityError):
        create_post_version(
            context, "version-002", "post-001",
            "brand-001", "user-002"
        )


def test_post_version_accepts_null_created_by(context):
    create_post_version(
        context, "version-003", "post-001",
        "brand-001", None
    )


def test_post_version_update_rejects_user_from_another_environment(
    context,
):
    create_post_version(
        context, "version-004", "post-001",
        "brand-001", "user-001"
    )

    with pytest.raises(sqlite3.IntegrityError):
        context.execute(
            """
            UPDATE post_versions
            SET created_by = ?
            WHERE id = ?
            """,
            ("user-002", "version-004"),
        )


# APPROVALS


def test_approval_accepts_user_from_same_environment(context):
    create_post_version(
        context, "version-approval-001",
        "post-001", "brand-001"
    )

    create_approval(
        context, "approval-001",
        "version-approval-001", "user-001"
    )


def test_approval_rejects_user_from_another_environment(context):
    create_post_version(
        context, "version-approval-002",
        "post-001", "brand-001"
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_approval(
            context, "approval-002",
            "version-approval-002", "user-002"
        )


def test_approval_accepts_null_created_by(context):
    create_post_version(
        context, "version-approval-003",
        "post-001", "brand-001"
    )

    create_approval(
        context, "approval-003",
        "version-approval-003", None
    )


def test_approval_update_rejects_user_from_another_environment(
    context,
):
    create_post_version(
        context, "version-approval-004",
        "post-001", "brand-001"
    )

    create_approval(
        context, "approval-004",
        "version-approval-004", "user-001"
    )

    with pytest.raises(sqlite3.IntegrityError):
        context.execute(
            """
            UPDATE approvals
            SET created_by = ?
            WHERE id = ?
            """,
            ("user-002", "approval-004"),
        )


# USER DELETION


def test_deleting_user_preserves_created_by_history(context):
    create_post_version(
        context, "version-delete-001",
        "post-001", "brand-001", "user-001"
    )

    create_approval(
        context, "approval-delete-001",
        "version-delete-001", "user-001"
    )

    context.execute(
        "DELETE FROM users WHERE id = ?",
        ("user-001",),
    )

    version_user = context.execute(
        """
        SELECT created_by
        FROM post_versions
        WHERE id = ?
        """,
        ("version-delete-001",),
    ).fetchone()[0]

    approval_user = context.execute(
        """
        SELECT created_by
        FROM approvals
        WHERE id = ?
        """,
        ("approval-delete-001",),
    ).fetchone()[0]

    assert version_user is None
    assert approval_user is None


def test_profile_version_update_rejects_brand_from_another_environment(
    context,
):
    with pytest.raises(sqlite3.IntegrityError):
        context.execute(
            """
            UPDATE brand_profile_versions
            SET brand_id = ?
            WHERE id = ?
            """,
            ("brand-002", "profile-version-001"),
        )


def test_post_version_update_rejects_post_from_another_environment(
    context,
):
    create_content_request(context, "request-002", "brand-002")
    create_post(context, "post-002", "request-002", "brand-002")

    create_post_version(
        context, "version-transfer-001",
        "post-001", "brand-001", "user-001"
    )

    with pytest.raises(sqlite3.IntegrityError):
        context.execute(
            """
            UPDATE post_versions
            SET post_id = ?, brand_id = ?
            WHERE id = ?
            """,
            (
                "post-002",
                "brand-002",
                "version-transfer-001",
            ),
        )


def test_approval_update_rejects_version_from_another_environment(
    context,
):
    create_content_request(context, "request-002", "brand-002")
    create_post(context, "post-002", "request-002", "brand-002")

    create_post_version(
        context, "version-001",
        "post-001", "brand-001"
    )

    create_post_version(
        context, "version-002",
        "post-002", "brand-002"
    )

    create_approval(
        context, "approval-transfer-001",
        "version-001", "user-001"
    )

    with pytest.raises(sqlite3.IntegrityError):
        context.execute(
            """
            UPDATE approvals
            SET version_id = ?
            WHERE id = ?
            """,
            ("version-002", "approval-transfer-001"),
        )
