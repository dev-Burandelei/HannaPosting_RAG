
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


def create_content_request(database, request_id, brand_id):
    database.execute(
        """
        INSERT INTO content_requests (
            id, brand_id, profile_snapshot_json,
            operation, platforms, created_at, updated_at
        )
        VALUES (?, ?, '{}', 'create', '["instagram","linkedin"]',
                '2026-11-16', '2026-11-16')
        """,
        (request_id, brand_id),
    )


def create_post(
    database,
    post_id,
    request_id,
    brand_id,
    platform="instagram",
    status="draft",
    current_version_id=None,
    discarded_at=None,
):
    database.execute(
        """
        INSERT INTO posts (
            id, request_id, brand_id, platform,
            status, current_version_id,
            created_at, updated_at, discarded_at
        )
        VALUES (?, ?, ?, ?, ?, ?, '2026-11-16', '2026-11-16', ?)
        """,
        (
            post_id,
            request_id,
            brand_id,
            platform,
            status,
            current_version_id,
            discarded_at,
        ),
    )


def create_post_version(
    database,
    version_id,
    post_id,
    brand_id,
    version_number=1,
    parent_version_id=None,
):
    database.execute(
        """
        INSERT INTO post_versions (
            id, post_id, brand_id, parent_version_id,
            version_number, content, origin_type, created_at
        )
        VALUES (?, ?, ?, ?, ?, 'Conteúdo de teste',
                'generated', '2026-11-16')
        """,
        (
            version_id,
            post_id,
            brand_id,
            parent_version_id,
            version_number,
        ),
    )


@pytest.fixture
def post_context(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_brand(database, "brand-001", "env-001")
    create_brand(database, "brand-002", "env-001")
    create_brand(database, "brand-003", "env-002")

    create_content_request(database, "request-001", "brand-001")
    create_content_request(database, "request-002", "brand-002")

    return database


def test_post_accepts_valid_platform(post_context):
    database = post_context

    create_post(
        database, "post-001", "request-001",
        "brand-001", platform="instagram"
    )

    create_post(
        database, "post-002", "request-001",
        "brand-001", platform="linkedin"
    )


def test_post_rejects_invalid_platform(post_context):
    database = post_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post(
            database, "post-003", "request-001",
            "brand-001", platform="facebook"
        )



@pytest.mark.parametrize(
    "status",
    ["draft", "in_review", "editing", "discarded"],
)
def test_post_accepts_valid_status(post_context, status):
    database = post_context

    discarded_at = (
        "2026-11-16T10:00:00"
        if status == "discarded"
        else None
    )

    create_post(
        database,
        f"post-{status}",
        "request-001",
        "brand-001",
        platform="instagram",
        status=status,
        discarded_at=discarded_at,
    )


def test_post_rejects_invalid_status(post_context):
    database = post_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post(
            database, "post-004", "request-001",
            "brand-001", status="approved"
        )


def test_post_rejects_duplicate_request_platform(post_context):
    database = post_context

    create_post(
        database, "post-005", "request-001",
        "brand-001", platform="instagram"
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_post(
            database, "post-006", "request-001",
            "brand-001", platform="instagram"
        )


def test_post_accepts_different_platform_for_same_request(post_context):
    database = post_context

    create_post(
        database, "post-007", "request-001",
        "brand-001", platform="instagram"
    )

    create_post(
        database, "post-008", "request-001",
        "brand-001", platform="linkedin"
    )


def test_post_rejects_request_from_another_brand(post_context):
    database = post_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post(
            database, "post-009", "request-002",
            "brand-001"
        )


def test_post_rejects_brand_from_another_environment(post_context):
    database = post_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post(
            database, "post-010", "request-001",
            "brand-003"
        )


def test_post_accepts_current_version_from_same_post(post_context):
    database = post_context

    create_post(
        database, "post-011", "request-001",
        "brand-001"
    )

    create_post_version(
        database, "version-011", "post-011", "brand-001"
    )

    database.execute(
        """
        UPDATE posts
        SET current_version_id = ?
        WHERE id = ?
        """,
        ("version-011", "post-011"),
    )



def test_post_rejects_current_version_from_another_post(post_context):
    database = post_context

    create_post(
        database, "post-012", "request-001",
        "brand-001"
    )

    create_post(
        database, "post-013", "request-001",
        "brand-001", platform="linkedin"
    )

    create_post_version(
        database, "version-013", "post-013", "brand-001"
    )

    database.execute(
        """
        UPDATE posts
        SET current_version_id = ?
        WHERE id = ?
        """,
        ("version-013", "post-012"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.commit()



def test_post_rejects_nonexistent_current_version(post_context):
    database = post_context

    create_post(
        database, "post-014", "request-001",
        "brand-001"
    )

    database.execute(
        """
        UPDATE posts
        SET current_version_id = ?
        WHERE id = ?
        """,
        ("version-inexistente", "post-014"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.commit()


def test_post_version_accepts_positive_version_number(post_context):
    database = post_context

    create_post(
        database, "post-015", "request-001",
        "brand-001"
    )

    create_post_version(
        database, "version-015", "post-015",
        "brand-001", version_number=1
    )


@pytest.mark.parametrize("version_number", [0, -1])
def test_post_version_rejects_nonpositive_version_number(
    post_context, version_number
):
    database = post_context

    create_post(
        database, "post-016", "request-001",
        "brand-001"
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_post_version(
            database, "version-invalid", "post-016",
            "brand-001", version_number=version_number
        )


def test_post_version_rejects_duplicate_version_number(post_context):
    database = post_context

    create_post(
        database, "post-017", "request-001",
        "brand-001"
    )

    create_post_version(
        database, "version-017-a", "post-017",
        "brand-001", version_number=1
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_post_version(
            database, "version-017-b", "post-017",
            "brand-001", version_number=1
        )


def test_post_version_accepts_parent_from_same_post(post_context):
    database = post_context

    create_post(
        database, "post-018", "request-001",
        "brand-001"
    )

    create_post_version(
        database, "version-018-a", "post-018",
        "brand-001", version_number=1
    )

    create_post_version(
        database, "version-018-b", "post-018",
        "brand-001", version_number=2,
        parent_version_id="version-018-a"
    )


def test_post_version_rejects_parent_from_another_post(post_context):
    database = post_context

    create_post(
        database, "post-019", "request-001",
        "brand-001"
    )

    create_post(
        database, "post-020", "request-001",
        "brand-001", platform="linkedin"
    )

    create_post_version(
        database, "version-019-a", "post-019", "brand-001"
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_post_version(
            database, "version-020-a", "post-020",
            "brand-001", version_number=2,
            parent_version_id="version-019-a"
        )


def test_post_cannot_be_deleted_while_versions_exist(post_context):
    database = post_context

    create_post(
        database, "post-021", "request-001",
        "brand-001"
    )

    create_post_version(
        database, "version-021", "post-021", "brand-001"
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM posts WHERE id = ?",
            ("post-021",),
        )


def test_post_version_cannot_be_deleted_when_current(post_context):
    database = post_context

    create_post(
        database, "post-022", "request-001",
        "brand-001"
    )

    create_post_version(
        database, "version-022", "post-022", "brand-001"
    )

    database.execute(
        """
        UPDATE posts
        SET current_version_id = ?
        WHERE id = ?
        """,
        ("version-022", "post-022"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM post_versions WHERE id = ?",
            ("version-022",),
        )


def test_post_can_reference_version_created_later_in_same_transaction(
    post_context,
):
    database = post_context

    # 1. Cria o post apontando para uma versão que ainda não existe.
    create_post(
        database,
        "post-deferred-001",
        "request-001",
        "brand-001",
        current_version_id="version-deferred-001",
    )

    # 2. Cria a versão posteriormente, dentro da mesma transação.
    create_post_version(
        database,
        "version-deferred-001",
        "post-deferred-001",
        "brand-001",
    )

    # 3. A transação deve ser confirmada sem violação de FK.
    database.commit()

    # 4. Confirma que o vínculo foi persistido corretamente.
    result = database.execute(
        """
        SELECT current_version_id
        FROM posts
        WHERE id = ?
        """,
        ("post-deferred-001",),
    ).fetchone()

    assert result[0] == "version-deferred-001"


def test_post_accepts_discarded_status_with_timestamp(post_context):
    database = post_context

    create_post(
        database,
        "post-discarded-001",
        "request-001",
        "brand-001",
        status="discarded",
        discarded_at="2026-11-16T10:00:00",
    )


def test_post_accepts_non_discarded_status_without_timestamp(post_context):
    database = post_context

    create_post(
        database,
        "post-discarded-002",
        "request-001",
        "brand-001",
        status="draft",
        discarded_at=None,
    )


def test_post_rejects_discarded_status_without_timestamp(post_context):
    database = post_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post(
            database,
            "post-discarded-003",
            "request-001",
            "brand-001",
            status="discarded",
            discarded_at=None,
        )


def test_post_rejects_non_discarded_status_with_timestamp(post_context):
    database = post_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post(
            database,
            "post-discarded-004",
            "request-001",
            "brand-001",
            status="draft",
            discarded_at="2026-11-16T10:00:00",
        )
