
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
):
    database.execute(
        """
        INSERT INTO posts (
            id, request_id, brand_id, platform,
            status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, 'draft', '2026-11-16', '2026-11-16')
        """,
        (post_id, request_id, brand_id, platform),
    )


def create_tag(database, tag_id, brand_id):
    database.execute(
        """
        INSERT INTO tags (
            id, brand_id, name, category,
            is_custom, created_at
        )
        VALUES (?, ?, ?, 'assunto', 0, '2026-11-16')
        """,
        (tag_id, brand_id, f"Tag {tag_id}"),
    )


def create_post_tag(
    database,
    post_id="post-001",
    tag_id="tag-001",
    brand_id="brand-001",
):
    database.execute(
        """
        INSERT INTO post_tags (
            post_id, tag_id, brand_id
        )
        VALUES (?, ?, ?)
        """,
        (post_id, tag_id, brand_id),
    )


@pytest.fixture
def post_tag_context(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_brand(database, "brand-001", "env-001")
    create_brand(database, "brand-002", "env-002")

    create_content_request(database, "request-001", "brand-001")
    create_content_request(database, "request-002", "brand-001")
    create_content_request(database, "request-003", "brand-002")

    create_post(database, "post-001", "request-001", "brand-001")
    create_post(database, "post-002", "request-002", "brand-001")
    create_post(database, "post-003", "request-003", "brand-002")

    create_tag(database, "tag-001", "brand-001")
    create_tag(database, "tag-002", "brand-001")
    create_tag(database, "tag-003", "brand-002")

    return database


def test_post_tag_accepts_valid_relationship(post_tag_context):
    database = post_tag_context

    create_post_tag(database)

    result = database.execute(
        """
        SELECT post_id, tag_id, brand_id
        FROM post_tags
        """
    ).fetchone()

    assert result == ("post-001", "tag-001", "brand-001")


@pytest.mark.parametrize(
    "column",
    ["post_id", "tag_id", "brand_id"],
)
def test_post_tag_requires_mandatory_fields(
    post_tag_context, column
):
    database = post_tag_context

    values = {
        "post_id": "post-001",
        "tag_id": "tag-001",
        "brand_id": "brand-001",
    }

    values[column] = None

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO post_tags (
                post_id, tag_id, brand_id
            )
            VALUES (
                :post_id, :tag_id, :brand_id
            )
            """,
            values,
        )


def test_post_tag_rejects_nonexistent_post(post_tag_context):
    database = post_tag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post_tag(database, post_id="post-inexistente")


def test_post_tag_rejects_nonexistent_tag(post_tag_context):
    database = post_tag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post_tag(database, tag_id="tag-inexistente")


def test_post_tag_rejects_nonexistent_brand(post_tag_context):
    database = post_tag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post_tag(database, brand_id="brand-inexistente")


def test_post_tag_rejects_tag_from_another_brand(
    post_tag_context,
):
    database = post_tag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post_tag(
            database,
            post_id="post-001",
            tag_id="tag-003",
            brand_id="brand-001",
        )


def test_post_tag_rejects_post_from_another_brand(
    post_tag_context,
):
    database = post_tag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post_tag(
            database,
            post_id="post-003",
            tag_id="tag-001",
            brand_id="brand-001",
        )


def test_post_tag_rejects_brand_different_from_post(
    post_tag_context,
):
    database = post_tag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post_tag(
            database,
            post_id="post-001",
            tag_id="tag-003",
            brand_id="brand-002",
        )


def test_post_tag_rejects_brand_different_from_tag(
    post_tag_context,
):
    database = post_tag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_post_tag(
            database,
            post_id="post-003",
            tag_id="tag-003",
            brand_id="brand-001",
        )


def test_post_tag_rejects_duplicate_relationship(
    post_tag_context,
):
    database = post_tag_context

    create_post_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_post_tag(database)


def test_post_allows_multiple_tags(post_tag_context):
    database = post_tag_context

    create_post_tag(database, tag_id="tag-001")
    create_post_tag(database, tag_id="tag-002")

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM post_tags
        WHERE post_id = ?
        """,
        ("post-001",),
    ).fetchone()[0]

    assert count == 2


def test_tag_allows_multiple_posts(post_tag_context):
    database = post_tag_context

    create_post_tag(database, post_id="post-001")
    create_post_tag(database, post_id="post-002")

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM post_tags
        WHERE tag_id = ?
        """,
        ("tag-001",),
    ).fetchone()[0]

    assert count == 2


def test_post_tag_preserves_post_relationship(post_tag_context):
    database = post_tag_context

    create_post_tag(database)

    result = database.execute(
        """
        SELECT p.id
        FROM post_tags pt
        JOIN posts p
          ON p.id = pt.post_id
         AND p.brand_id = pt.brand_id
        WHERE pt.post_id = ?
        """,
        ("post-001",),
    ).fetchone()

    assert result[0] == "post-001"


def test_post_tag_preserves_tag_relationship(post_tag_context):
    database = post_tag_context

    create_post_tag(database)

    result = database.execute(
        """
        SELECT t.id
        FROM post_tags pt
        JOIN tags t
          ON t.id = pt.tag_id
         AND t.brand_id = pt.brand_id
        WHERE pt.tag_id = ?
        """,
        ("tag-001",),
    ).fetchone()

    assert result[0] == "tag-001"


def test_post_tag_prevents_deleting_referenced_post(
    post_tag_context,
):
    database = post_tag_context

    create_post_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM posts WHERE id = ?",
            ("post-001",),
        )


def test_post_tag_prevents_deleting_referenced_tag(
    post_tag_context,
):
    database = post_tag_context

    create_post_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM tags WHERE id = ?",
            ("tag-001",),
        )


def test_post_tag_allows_deleting_relationship(post_tag_context):
    database = post_tag_context

    create_post_tag(database)

    database.execute(
        """
        DELETE FROM post_tags
        WHERE post_id = ? AND tag_id = ?
        """,
        ("post-001", "tag-001"),
    )

    count = database.execute(
        "SELECT COUNT(*) FROM post_tags"
    ).fetchone()[0]

    assert count == 0
