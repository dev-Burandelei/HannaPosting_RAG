
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


def create_document(database, document_id, brand_id):
    database.execute(
        """
        INSERT INTO documents (
            id, brand_id, original_filename, storage_path,
            mime_type, file_size_bytes, content_hash,
            purpose, status, created_at, updated_at
        )
        VALUES (?, ?, 'teste.pdf', '/teste.pdf',
                'application/pdf', 100, 'hash-teste',
                'brand_knowledge', 'active',
                '2026-11-16', '2026-11-16')
        """,
        (document_id, brand_id),
    )


def create_tag(database, tag_id, brand_id):
    database.execute(
        """
        INSERT INTO tags (
            id, brand_id, name, category, is_custom, created_at
        )
        VALUES (?, ?, 'Institucional', 'assunto', 0, '2026-11-16')
        """,
        (tag_id, brand_id),
    )


def test_brand_rejects_nonexistent_environment(database):
    with pytest.raises(sqlite3.IntegrityError):
        create_brand(database, "brand-001", "env-inexistente")


def test_environment_cannot_be_deleted_if_brand_exists(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM environments WHERE id = ?",
            ("env-001",),
        )


def test_document_tag_rejects_cross_brand_relationship(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")
    create_brand(database, "brand-002", "env-001")

    create_document(database, "doc-001", "brand-001")
    create_tag(database, "tag-002", "brand-002")

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO document_tags (document_id, tag_id, brand_id)
            VALUES (?, ?, ?)
            """,
            ("doc-001", "tag-002", "brand-001"),
        )


def test_document_tag_accepts_same_brand_relationship(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")

    create_document(database, "doc-001", "brand-001")
    create_tag(database, "tag-001", "brand-001")

    database.execute(
        """
        INSERT INTO document_tags (document_id, tag_id, brand_id)
        VALUES (?, ?, ?)
        """,
        ("doc-001", "tag-001", "brand-001"),
    )

    result = database.execute(
        "SELECT COUNT(*) FROM document_tags"
    ).fetchone()[0]

    assert result == 1


def test_tag_rejects_duplicate_name_and_category(database):
    create_environment(database, "env-001")
    create_brand(database, "brand-001", "env-001")

    create_tag(database, "tag-001", "brand-001")

    with pytest.raises(sqlite3.IntegrityError):
        create_tag(database, "tag-002", "brand-001")
