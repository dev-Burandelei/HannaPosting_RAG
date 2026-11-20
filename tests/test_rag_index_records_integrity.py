
import sqlite3

import pytest


def create_environment(database, environment_id="env-001"):
    database.execute(
        """
        INSERT INTO environments (
            id, name, status, created_at, updated_at
        )
        VALUES (?, ?, 'active', '2026-11-16', '2026-11-16')
        """,
        (environment_id, environment_id),
    )


def create_brand(database, brand_id="brand-001", environment_id="env-001"):
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


def create_document(database, document_id, brand_id):
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
            "2026-11-16",
            "2026-11-16",
        ),
    )


def create_post(database, post_id, request_id, brand_id):
    database.execute(
        """
        INSERT INTO posts (
            id, request_id, brand_id, platform,
            status, created_at, updated_at
        )
        VALUES (?, ?, ?, 'instagram', 'draft', '2026-11-16', '2026-11-16')
        """,
        (post_id, request_id, brand_id),
    )


def create_post_version(database, version_id, post_id, brand_id):
    database.execute(
        """
        INSERT INTO post_versions (
            id, post_id, brand_id, parent_version_id,
            version_number, content, origin_type, created_at
        )
        VALUES (?, ?, ?, NULL, 1, 'Conteúdo de teste',
                'generated', '2026-11-16')
        """,
        (version_id, post_id, brand_id),
    )


def create_rag_record(
    database,
    record_id="rag-001",
    brand_id="brand-001",
    document_id="doc-001",
    post_version_id=None,
    source_type="brand_knowledge",
    collection_name="brand_knowledge",
    vector_ids_json='["vector-001"]',
    index_status="pending",
    indexed_at=None,
    deactivated_at=None,
    last_error=None,
):
    database.execute(
        """
        INSERT INTO rag_index_records (
            id, brand_id, document_id, post_version_id,
            source_type, collection_name, vector_ids_json,
            index_status, indexed_at, deactivated_at,
            last_error, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_id,
            brand_id,
            document_id,
            post_version_id,
            source_type,
            collection_name,
            vector_ids_json,
            index_status,
            indexed_at,
            deactivated_at,
            last_error,
            "2026-11-16",
            "2026-11-16",
        ),
    )


@pytest.fixture
def rag_context(database):
    create_environment(database)
    create_brand(database)

    create_environment(database, "env-002")
    create_brand(database, "brand-002", "env-002")

    create_content_request(database, "request-001", "brand-001")
    create_content_request(database, "request-002", "brand-002")

    create_document(database, "doc-001", "brand-001")
    create_document(database, "doc-002", "brand-002")

    create_post(database, "post-001", "request-001", "brand-001")
    create_post(database, "post-002", "request-002", "brand-002")

    create_post_version(
        database, "version-001", "post-001", "brand-001"
    )
    create_post_version(
        database, "version-002", "post-002", "brand-002"
    )

    return database


def test_rag_record_accepts_document_source(rag_context):
    database = rag_context

    create_rag_record(database)

    result = database.execute(
        """
        SELECT brand_id, document_id, post_version_id, source_type
        FROM rag_index_records
        WHERE id = ?
        """,
        ("rag-001",),
    ).fetchone()

    assert result == (
        "brand-001",
        "doc-001",
        None,
        "brand_knowledge",
    )


def test_rag_record_accepts_post_version_source(rag_context):
    database = rag_context

    create_rag_record(
        database,
        document_id=None,
        post_version_id="version-001",
        source_type="writing_example",
    )

    result = database.execute(
        """
        SELECT brand_id, document_id, post_version_id, source_type
        FROM rag_index_records
        WHERE id = ?
        """,
        ("rag-001",),
    ).fetchone()

    assert result == (
        "brand-001",
        None,
        "version-001",
        "writing_example",
    )


@pytest.mark.parametrize(
    "source_type",
    ["brand_knowledge", "writing_example"],
)
def test_rag_record_accepts_valid_source_types(
    rag_context, source_type
):
    database = rag_context

    create_rag_record(database, source_type=source_type)

    result = database.execute(
        "SELECT source_type FROM rag_index_records"
    ).fetchone()

    assert result[0] == source_type


@pytest.mark.parametrize(
    "source_type",
    ["document", "post", "invalid", "", "BRAND_KNOWLEDGE"],
)
def test_rag_record_rejects_invalid_source_type(
    rag_context, source_type
):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(database, source_type=source_type)


@pytest.mark.parametrize(
    "index_status",
    ["pending", "active", "inactive", "failed", "deleting"],
)
def test_rag_record_accepts_valid_index_status(
    rag_context, index_status
):
    database = rag_context

    create_rag_record(database, index_status=index_status)

    result = database.execute(
        "SELECT index_status FROM rag_index_records"
    ).fetchone()

    assert result[0] == index_status


@pytest.mark.parametrize(
    "index_status",
    ["queued", "processing", "completed", "deleted", "invalid", ""],
)
def test_rag_record_rejects_invalid_index_status(
    rag_context, index_status
):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(database, index_status=index_status)


@pytest.mark.parametrize(
    "column",
    [
        "brand_id",
        "source_type",
        "collection_name",
        "vector_ids_json",
        "index_status",
        "created_at",
        "updated_at",
    ],
)
def test_rag_record_requires_mandatory_fields(
    rag_context, column
):
    database = rag_context

    values = {
        "id": "rag-001",
        "brand_id": "brand-001",
        "document_id": "doc-001",
        "post_version_id": None,
        "source_type": "brand_knowledge",
        "collection_name": "brand_knowledge",
        "vector_ids_json": '["vector-001"]',
        "index_status": "pending",
        "created_at": "2026-11-16",
        "updated_at": "2026-11-16",
    }

    values[column] = None

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO rag_index_records (
                id, brand_id, document_id, post_version_id,
                source_type, collection_name, vector_ids_json,
                index_status, created_at, updated_at
            )
            VALUES (
                :id, :brand_id, :document_id, :post_version_id,
                :source_type, :collection_name, :vector_ids_json,
                :index_status, :created_at, :updated_at
            )
            """,
            values,
        )


@pytest.mark.parametrize(
    "json_value",
    [
        "{}",
        "[]",
        '["vector-001", "vector-002"]',
        '{"ids": ["vector-001"]}',
        '"texto"',
        "123",
        "true",
        "null",
    ],
)
def test_rag_record_accepts_valid_json(rag_context, json_value):
    database = rag_context

    create_rag_record(database, vector_ids_json=json_value)

    result = database.execute(
        "SELECT vector_ids_json FROM rag_index_records"
    ).fetchone()

    assert result[0] == json_value


@pytest.mark.parametrize(
    "json_value",
    [
        "",
        "texto",
        "{invalid json}",
        '{"ids": }',
        "[1, 2,]",
    ],
)
def test_rag_record_rejects_invalid_json(rag_context, json_value):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(database, vector_ids_json=json_value)


def test_rag_record_requires_exactly_one_source(rag_context):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(
            database,
            document_id=None,
            post_version_id=None,
        )


def test_rag_record_rejects_both_sources_at_same_time(rag_context):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(
            database,
            document_id="doc-001",
            post_version_id="version-001",
        )


def test_rag_record_rejects_nonexistent_brand(rag_context):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(database, brand_id="brand-inexistente")


def test_rag_record_rejects_nonexistent_document(rag_context):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(database, document_id="doc-inexistente")


def test_rag_record_rejects_nonexistent_post_version(rag_context):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(
            database,
            document_id=None,
            post_version_id="version-inexistente",
            source_type="writing_example",
        )


def test_rag_record_rejects_document_from_another_brand(rag_context):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(
            database,
            brand_id="brand-001",
            document_id="doc-002",
        )


def test_rag_record_rejects_post_version_from_another_brand(
    rag_context,
):
    database = rag_context

    with pytest.raises(sqlite3.IntegrityError):
        create_rag_record(
            database,
            brand_id="brand-001",
            document_id=None,
            post_version_id="version-002",
            source_type="writing_example",
        )


def test_rag_record_prevents_deleting_referenced_document(rag_context):
    database = rag_context

    create_rag_record(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM documents WHERE id = ?",
            ("doc-001",),
        )


def test_rag_record_prevents_deleting_referenced_post_version(
    rag_context,
):
    database = rag_context

    create_rag_record(
        database,
        document_id=None,
        post_version_id="version-001",
        source_type="writing_example",
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM post_versions WHERE id = ?",
            ("version-001",),
        )


def test_rag_record_prevents_deleting_referenced_brand(rag_context):
    database = rag_context

    create_rag_record(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM brands WHERE id = ?",
            ("brand-001",),
        )


def test_rag_record_allows_null_optional_fields(rag_context):
    database = rag_context

    create_rag_record(
        database,
        indexed_at=None,
        deactivated_at=None,
        last_error=None,
    )

    result = database.execute(
        """
        SELECT indexed_at, deactivated_at, last_error
        FROM rag_index_records
        WHERE id = ?
        """,
        ("rag-001",),
    ).fetchone()

    assert result == (None, None, None)


def test_rag_record_accepts_optional_fields(rag_context):
    database = rag_context

    create_rag_record(
        database,
        indexed_at="2026-11-16T10:00:00",
        deactivated_at="2026-11-16T11:00:00",
        last_error="Erro de teste",
    )

    result = database.execute(
        """
        SELECT indexed_at, deactivated_at, last_error
        FROM rag_index_records
        WHERE id = ?
        """,
        ("rag-001",),
    ).fetchone()

    assert result == (
        "2026-11-16T10:00:00",
        "2026-11-16T11:00:00",
        "Erro de teste",
    )


def test_rag_record_allows_multiple_records_for_same_document(
    rag_context,
):
    database = rag_context

    create_rag_record(database, record_id="rag-001")
    create_rag_record(database, record_id="rag-002")

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM rag_index_records
        WHERE document_id = ?
        """,
        ("doc-001",),
    ).fetchone()[0]

    assert count == 2


def test_rag_record_allows_multiple_records_for_same_post_version(
    rag_context,
):
    database = rag_context

    create_rag_record(
        database,
        record_id="rag-001",
        document_id=None,
        post_version_id="version-001",
        source_type="writing_example",
    )

    create_rag_record(
        database,
        record_id="rag-002",
        document_id=None,
        post_version_id="version-001",
        source_type="writing_example",
    )

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM rag_index_records
        WHERE post_version_id = ?
        """,
        ("version-001",),
    ).fetchone()[0]

    assert count == 2


def test_rag_record_allows_updating_index_status(rag_context):
    database = rag_context

    create_rag_record(database)

    database.execute(
        """
        UPDATE rag_index_records
        SET index_status = 'active'
        WHERE id = ?
        """,
        ("rag-001",),
    )

    result = database.execute(
        "SELECT index_status FROM rag_index_records WHERE id = ?",
        ("rag-001",),
    ).fetchone()

    assert result[0] == "active"


def test_rag_record_rejects_invalid_status_on_update(rag_context):
    database = rag_context

    create_rag_record(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE rag_index_records
            SET index_status = 'completed'
            WHERE id = ?
            """,
            ("rag-001",),
        )


def test_rag_record_rejects_invalid_json_on_update(rag_context):
    database = rag_context

    create_rag_record(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE rag_index_records
            SET vector_ids_json = ?
            WHERE id = ?
            """,
            ("{invalid json}", "rag-001"),
        )


def test_rag_record_rejects_removing_both_sources_on_update(
    rag_context,
):
    database = rag_context

    create_rag_record(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE rag_index_records
            SET document_id = NULL
            WHERE id = ?
            """,
            ("rag-001",),
        )


def test_rag_record_rejects_adding_second_source_on_update(
    rag_context,
):
    database = rag_context

    create_rag_record(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE rag_index_records
            SET post_version_id = ?
            WHERE id = ?
            """,
            ("version-001", "rag-001"),
        )
