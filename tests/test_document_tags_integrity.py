
import sqlite3
import pytest


def create_environment(database, environment_id="env-1"):
    database.execute(
        """
        INSERT INTO environments (
            id, name, created_at, updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            environment_id,
            "Ambiente de teste",
            "2026-01-01T10:00:00",
            "2026-01-01T10:00:00",
        ),
    )


def create_brand(database, brand_id="brand-1", environment_id="env-1"):
    database.execute(
        """
        INSERT INTO brands (
            id, environment_id, name,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            brand_id,
            environment_id,
            f"Marca {brand_id}",
            "2026-01-01T10:00:00",
            "2026-01-01T10:00:00",
        ),
    )


def create_document(database, document_id="doc-1", brand_id="brand-1"):
    database.execute(
        """
        INSERT INTO documents (
            id, brand_id, original_filename, storage_path,
            mime_type, file_size_bytes, content_hash,
            purpose, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            brand_id,
            f"{document_id}.pdf",
            f"documents/{document_id}.pdf",
            "application/pdf",
            1024,
            f"hash-{document_id}",
            "brand_knowledge",
            "active",
            "2026-01-01T10:00:00",
            "2026-01-01T10:00:00",
        ),
    )


def create_tag(database, tag_id="tag-1", brand_id="brand-1"):
    database.execute(
        """
        INSERT INTO tags (
            id, brand_id, name, category, is_custom, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            tag_id,
            brand_id,
            f"Tag {tag_id}",
            "assunto",
            0,
            "2026-01-01T10:00:00",
        ),
    )


def create_document_tag(
    database,
    document_id="doc-1",
    tag_id="tag-1",
    brand_id="brand-1",
):
    database.execute(
        """
        INSERT INTO document_tags (
            document_id, tag_id, brand_id
        )
        VALUES (?, ?, ?)
        """,
        (document_id, tag_id, brand_id),
    )


@pytest.fixture
def document_tag_context(database):
    create_environment(database)
    create_brand(database)
    create_document(database)
    create_tag(database)

    return {
        "document_id": "doc-1",
        "tag_id": "tag-1",
        "brand_id": "brand-1",
    }


def test_document_tag_accepts_valid_relationship(
    database, document_tag_context
):
    create_document_tag(database)

    result = database.execute(
        """
        SELECT document_id, tag_id, brand_id
        FROM document_tags
        """
    ).fetchone()

    assert result == ("doc-1", "tag-1", "brand-1")


@pytest.mark.parametrize(
    "column",
    ["document_id", "tag_id", "brand_id"],
)
def test_document_tag_requires_mandatory_fields(
    database, document_tag_context, column
):
    values = {
        "document_id": "doc-1",
        "tag_id": "tag-1",
        "brand_id": "brand-1",
    }

    values[column] = None

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO document_tags (
                document_id, tag_id, brand_id
            )
            VALUES (
                :document_id, :tag_id, :brand_id
            )
            """,
            values,
        )


def test_document_tag_rejects_nonexistent_document(
    database, document_tag_context
):
    with pytest.raises(sqlite3.IntegrityError):
        create_document_tag(database, document_id="doc-inexistente")


def test_document_tag_rejects_nonexistent_tag(
    database, document_tag_context
):
    with pytest.raises(sqlite3.IntegrityError):
        create_document_tag(database, tag_id="tag-inexistente")


def test_document_tag_rejects_nonexistent_brand(
    database, document_tag_context
):
    with pytest.raises(sqlite3.IntegrityError):
        create_document_tag(database, brand_id="brand-inexistente")


def test_document_tag_rejects_document_from_another_brand(
    database, document_tag_context
):
    create_environment(database, "env-2")
    create_brand(database, "brand-2", "env-2")
    create_document(database, "doc-2", "brand-2")

    with pytest.raises(sqlite3.IntegrityError):
        create_document_tag(
            database,
            document_id="doc-2",
            tag_id="tag-1",
            brand_id="brand-1",
        )


def test_document_tag_rejects_tag_from_another_brand(
    database, document_tag_context
):
    create_environment(database, "env-2")
    create_brand(database, "brand-2", "env-2")
    create_tag(database, "tag-2", "brand-2")

    with pytest.raises(sqlite3.IntegrityError):
        create_document_tag(
            database,
            document_id="doc-1",
            tag_id="tag-2",
            brand_id="brand-1",
        )


def test_document_tag_rejects_brand_different_from_document(
    database, document_tag_context
):
    create_environment(database, "env-2")
    create_brand(database, "brand-2", "env-2")

    with pytest.raises(sqlite3.IntegrityError):
        create_document_tag(
            database,
            document_id="doc-1",
            tag_id="tag-1",
            brand_id="brand-2",
        )


def test_document_tag_rejects_brand_different_from_tag(
    database, document_tag_context
):
    create_environment(database, "env-2")
    create_brand(database, "brand-2", "env-2")

    with pytest.raises(sqlite3.IntegrityError):
        create_document_tag(
            database,
            document_id="doc-1",
            tag_id="tag-1",
            brand_id="brand-2",
        )


def test_document_tag_rejects_duplicate_relationship(
    database, document_tag_context
):
    create_document_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_document_tag(database)


def test_document_allows_multiple_tags(
    database, document_tag_context
):
    create_tag(database, "tag-2")
    create_document_tag(database, tag_id="tag-1")
    create_document_tag(database, tag_id="tag-2")

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM document_tags
        WHERE document_id = ?
        """,
        ("doc-1",),
    ).fetchone()[0]

    assert count == 2


def test_tag_allows_multiple_documents(
    database, document_tag_context
):
    create_document(database, "doc-2")
    create_document_tag(database, document_id="doc-1")
    create_document_tag(database, document_id="doc-2")

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM document_tags
        WHERE tag_id = ?
        """,
        ("tag-1",),
    ).fetchone()[0]

    assert count == 2


def test_document_tag_allows_same_document_with_different_tags(
    database, document_tag_context
):
    create_tag(database, "tag-2")

    create_document_tag(database, tag_id="tag-1")
    create_document_tag(database, tag_id="tag-2")

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM document_tags
        WHERE document_id = ?
        """,
        ("doc-1",),
    ).fetchone()[0]

    assert count == 2


def test_document_tag_allows_same_tag_with_different_documents(
    database, document_tag_context
):
    create_document(database, "doc-2")

    create_document_tag(database, document_id="doc-1")
    create_document_tag(database, document_id="doc-2")

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM document_tags
        WHERE tag_id = ?
        """,
        ("tag-1",),
    ).fetchone()[0]

    assert count == 2


def test_document_tag_preserves_document_relationship(
    database, document_tag_context
):
    create_document_tag(database)

    result = database.execute(
        """
        SELECT d.id
        FROM document_tags dt
        JOIN documents d
          ON d.id = dt.document_id
         AND d.brand_id = dt.brand_id
        WHERE dt.document_id = ?
        """,
        ("doc-1",),
    ).fetchone()

    assert result[0] == "doc-1"


def test_document_tag_preserves_tag_relationship(
    database, document_tag_context
):
    create_document_tag(database)

    result = database.execute(
        """
        SELECT t.id
        FROM document_tags dt
        JOIN tags t
          ON t.id = dt.tag_id
         AND t.brand_id = dt.brand_id
        WHERE dt.tag_id = ?
        """,
        ("tag-1",),
    ).fetchone()

    assert result[0] == "tag-1"


def test_document_tag_prevents_deleting_referenced_document(
    database, document_tag_context
):
    create_document_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM documents WHERE id = ?",
            ("doc-1",),
        )


def test_document_tag_prevents_deleting_referenced_tag(
    database, document_tag_context
):
    create_document_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM tags WHERE id = ?",
            ("tag-1",),
        )


def test_document_tag_allows_deleting_relationship(
    database, document_tag_context
):
    create_document_tag(database)

    database.execute(
        """
        DELETE FROM document_tags
        WHERE document_id = ? AND tag_id = ?
        """,
        ("doc-1", "tag-1"),
    )

    count = database.execute(
        "SELECT COUNT(*) FROM document_tags"
    ).fetchone()[0]

    assert count == 0


def test_document_tag_allows_same_ids_for_different_brands(
    database, document_tag_context
):
    create_environment(database, "env-2")
    create_brand(database, "brand-2", "env-2")
    create_document(database, "doc-2", "brand-2")
    create_tag(database, "tag-2", "brand-2")

    create_document_tag(database)

    create_document_tag(
        database,
        document_id="doc-2",
        tag_id="tag-2",
        brand_id="brand-2",
    )

    count = database.execute(
        "SELECT COUNT(*) FROM document_tags"
    ).fetchone()[0]

    assert count == 2
