
import sqlite3

import pytest


def create_environment(database):
    database.execute(
        """
        INSERT INTO environments (
            id, name, created_at, updated_at
        )
        VALUES (
            'env-001', 'Ambiente de teste',
            '2026-11-16', '2026-11-16'
        )
        """
    )


def create_brand(database):
    database.execute(
        """
        INSERT INTO brands (
            id, environment_id, name, created_at, updated_at
        )
        VALUES (
            'brand-001', 'env-001', 'Marca de teste',
            '2026-11-16', '2026-11-16'
        )
        """
    )


@pytest.fixture
def document_context(database):
    create_environment(database)
    create_brand(database)
    return database


def create_document(
    database,
    document_id="document-001",
    brand_id="brand-001",
    purpose="brand_knowledge",
    status="active",
    file_size_bytes=1024,
):
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
            "documento.pdf",
            "storage/documento.pdf",
            "application/pdf",
            file_size_bytes,
            "hash-de-teste",
            purpose,
            status,
            "2026-11-16",
            "2026-11-16",
        ),
    )


def test_document_accepts_valid_data(document_context):
    create_document(document_context)


@pytest.mark.parametrize(
    "purpose",
    ["brand_knowledge", "writing_example"],
)
def test_document_accepts_valid_purposes(document_context, purpose):
    create_document(document_context, purpose=purpose)


def test_document_rejects_invalid_purpose(document_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_document(document_context, purpose="invalid")


@pytest.mark.parametrize(
    "status",
    ["active", "processing", "error", "deleted"],
)
def test_document_accepts_valid_statuses(document_context, status):
    create_document(document_context, status=status)


def test_document_rejects_invalid_status(document_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_document(document_context, status="invalid")


def test_document_uses_active_as_default_status(document_context):
    document_context.execute(
        """
        INSERT INTO documents (
            id, brand_id, original_filename, storage_path,
            mime_type, file_size_bytes, content_hash,
            purpose, created_at, updated_at
        )
        VALUES (
            'document-001', 'brand-001', 'documento.pdf',
            'storage/documento.pdf', 'application/pdf',
            1024, 'hash-de-teste', 'brand_knowledge',
            '2026-11-16', '2026-11-16'
        )
        """
    )

    status = document_context.execute(
        """
        SELECT status FROM documents
        WHERE id = 'document-001'
        """
    ).fetchone()[0]

    assert status == "active"


@pytest.mark.parametrize(
    "file_size",
    [0, 1, 1024, 1048576],
)
def test_document_accepts_nonnegative_file_sizes(
    document_context,
    file_size,
):
    create_document(document_context, file_size_bytes=file_size)


def test_document_rejects_negative_file_size(document_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_document(document_context, file_size_bytes=-1)


def test_document_requires_brand_id(document_context):
    with pytest.raises(sqlite3.IntegrityError):
        document_context.execute(
            """
            INSERT INTO documents (
                id, original_filename, storage_path, mime_type,
                file_size_bytes, content_hash, purpose,
                created_at, updated_at
            )
            VALUES (
                'document-001', 'documento.pdf',
                'storage/documento.pdf', 'application/pdf',
                1024, 'hash-de-teste', 'brand_knowledge',
                '2026-11-16', '2026-11-16'
            )
            """
        )


@pytest.mark.parametrize(
    "column",
    [
        "original_filename",
        "storage_path",
        "mime_type",
        "content_hash",
        "purpose",
        "created_at",
        "updated_at",
    ],
)
def test_document_requires_mandatory_fields(document_context, column):
    values = {
        "id": "document-001",
        "brand_id": "brand-001",
        "original_filename": "documento.pdf",
        "storage_path": "storage/documento.pdf",
        "mime_type": "application/pdf",
        "file_size_bytes": 1024,
        "content_hash": "hash-de-teste",
        "purpose": "brand_knowledge",
        "created_at": "2026-11-16",
        "updated_at": "2026-11-16",
    }

    values[column] = None

    columns = ", ".join(values.keys())
    placeholders = ", ".join("?" for _ in values)

    with pytest.raises(sqlite3.IntegrityError):
        document_context.execute(
            f"""
            INSERT INTO documents ({columns})
            VALUES ({placeholders})
            """,
            tuple(values.values()),
        )


def test_document_rejects_nonexistent_brand(document_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_document(
            document_context,
            brand_id="brand-inexistente",
        )


def test_document_restricts_brand_deletion(document_context):
    create_document(document_context)

    with pytest.raises(sqlite3.IntegrityError):
        document_context.execute(
            "DELETE FROM brands WHERE id = 'brand-001'"
        )


def test_document_allows_multiple_documents_for_same_brand(
    document_context,
):
    create_document(document_context, document_id="document-001")

    create_document(
        document_context,
        document_id="document-002",
        purpose="writing_example",
    )

    count = document_context.execute(
        """
        SELECT COUNT(*) FROM documents
        WHERE brand_id = 'brand-001'
        """
    ).fetchone()[0]

    assert count == 2


def test_document_allows_null_deleted_at(document_context):
    create_document(document_context)

    deleted_at = document_context.execute(
        """
        SELECT deleted_at FROM documents
        WHERE id = 'document-001'
        """
    ).fetchone()[0]

    assert deleted_at is None


def test_document_can_be_marked_as_deleted(document_context):
    create_document(document_context)

    document_context.execute(
        """
        UPDATE documents
        SET status = 'deleted',
            deleted_at = '2026-11-16'
        WHERE id = 'document-001'
        """
    )

    result = document_context.execute(
        """
        SELECT status, deleted_at
        FROM documents
        WHERE id = 'document-001'
        """
    ).fetchone()

    assert result == ("deleted", "2026-11-16")
