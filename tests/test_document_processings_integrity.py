
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


def create_document(database):
    database.execute(
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


@pytest.fixture
def processing_context(database):
    create_environment(database)
    create_brand(database)
    create_document(database)
    return database


def create_processing(
    database,
    processing_id="processing-001",
    document_id="document-001",
    attempt_number=1,
    status="queued",
    metadata=None,
):
    database.execute(
        """
        INSERT INTO document_processings (
            id, document_id, attempt_number,
            status, extracted_metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            processing_id,
            document_id,
            attempt_number,
            status,
            metadata,
            "2026-11-16",
        ),
    )


def test_processing_accepts_valid_data(processing_context):
    create_processing(processing_context)


@pytest.mark.parametrize(
    "status",
    ["queued", "processing", "completed", "failed"],
)
def test_processing_accepts_valid_statuses(processing_context, status):
    create_processing(processing_context, status=status)


def test_processing_rejects_invalid_status(processing_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_processing(processing_context, status="invalid")


@pytest.mark.parametrize(
    "attempt_number",
    [1, 2, 3, 10],
)
def test_processing_accepts_positive_attempt_numbers(
    processing_context,
    attempt_number,
):
    create_processing(
        processing_context,
        attempt_number=attempt_number,
    )


@pytest.mark.parametrize(
    "attempt_number",
    [0, -1, -10],
)
def test_processing_rejects_nonpositive_attempt_numbers(
    processing_context,
    attempt_number,
):
    with pytest.raises(sqlite3.IntegrityError):
        create_processing(
            processing_context,
            attempt_number=attempt_number,
        )


def test_processing_requires_document_id(processing_context):
    with pytest.raises(sqlite3.IntegrityError):
        processing_context.execute(
            """
            INSERT INTO document_processings (
                id, attempt_number, status, created_at
            )
            VALUES (
                'processing-001', 1, 'queued', '2026-11-16'
            )
            """
        )


def test_processing_rejects_nonexistent_document(processing_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_processing(
            processing_context,
            document_id="document-inexistente",
        )


def test_processing_accepts_null_metadata(processing_context):
    create_processing(processing_context, metadata=None)


@pytest.mark.parametrize(
    "metadata",
    [
        "{}",
        '{"pages": 10}',
        "[]",
        '"texto"',
        "123",
        "true",
        "null",
    ],
)
def test_processing_accepts_valid_json(processing_context, metadata):
    create_processing(processing_context, metadata=metadata)


@pytest.mark.parametrize(
    "metadata",
    [
        "",
        "texto",
        "{invalid json}",
        '{"pages": }',
    ],
)
def test_processing_rejects_invalid_json(processing_context, metadata):
    with pytest.raises(sqlite3.IntegrityError):
        create_processing(processing_context, metadata=metadata)


def test_processing_requires_attempt_number(processing_context):
    with pytest.raises(sqlite3.IntegrityError):
        processing_context.execute(
            """
            INSERT INTO document_processings (
                id, document_id, status, created_at
            )
            VALUES (
                'processing-001', 'document-001',
                'queued', '2026-11-16'
            )
            """
        )


def test_processing_requires_status(processing_context):
    with pytest.raises(sqlite3.IntegrityError):
        processing_context.execute(
            """
            INSERT INTO document_processings (
                id, document_id, attempt_number, created_at
            )
            VALUES (
                'processing-001', 'document-001',
                1, '2026-11-16'
            )
            """
        )


def test_processing_requires_created_at(processing_context):
    with pytest.raises(sqlite3.IntegrityError):
        processing_context.execute(
            """
            INSERT INTO document_processings (
                id, document_id, attempt_number, status
            )
            VALUES (
                'processing-001', 'document-001',
                1, 'queued'
            )
            """
        )


def test_processing_rejects_duplicate_attempt_for_document(
    processing_context,
):
    create_processing(processing_context, attempt_number=1)

    with pytest.raises(sqlite3.IntegrityError):
        create_processing(
            processing_context,
            processing_id="processing-002",
            attempt_number=1,
        )


def test_processing_allows_different_attempts_for_same_document(
    processing_context,
):
    create_processing(processing_context, attempt_number=1)

    create_processing(
        processing_context,
        processing_id="processing-002",
        attempt_number=2,
        status="failed",
    )

    count = processing_context.execute(
        """
        SELECT COUNT(*)
        FROM document_processings
        WHERE document_id = 'document-001'
        """
    ).fetchone()[0]

    assert count == 2


def test_processing_allows_same_attempt_number_for_different_documents(
    processing_context,
):
    create_document_second = """
        INSERT INTO documents (
            id, brand_id, original_filename, storage_path,
            mime_type, file_size_bytes, content_hash,
            purpose, created_at, updated_at
        )
        VALUES (
            'document-002', 'brand-001', 'outro.pdf',
            'storage/outro.pdf', 'application/pdf',
            2048, 'outro-hash', 'writing_example',
            '2026-11-16', '2026-11-16'
        )
    """

    processing_context.execute(create_document_second)

    create_processing(processing_context, attempt_number=1)

    create_processing(
        processing_context,
        processing_id="processing-002",
        document_id="document-002",
        attempt_number=1,
    )


def test_processing_preserves_document_relationship(processing_context):
    create_processing(processing_context)

    with pytest.raises(sqlite3.IntegrityError):
        processing_context.execute(
            "DELETE FROM documents WHERE id = 'document-001'"
        )


def test_processing_allows_optional_error_and_timestamps(
    processing_context,
):
    create_processing(processing_context)

    result = processing_context.execute(
        """
        SELECT error_message, started_at, finished_at
        FROM document_processings
        WHERE id = 'processing-001'
        """
    ).fetchone()

    assert result == (None, None, None)
