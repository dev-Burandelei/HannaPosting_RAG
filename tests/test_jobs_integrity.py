
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
            id,
            brand_id,
            profile_snapshot_json,
            operation,
            platforms,
            created_at,
            updated_at
        )
        VALUES (?, ?, '{}', 'create', '["instagram"]',
                '2026-11-16', '2026-11-16')
        """,
        (request_id, brand_id),
    )


def create_job(
    database,
    job_id,
    environment_id,
    brand_id=None,
    content_request_id=None,
    resource_type=None,
    resource_id=None,
):
    database.execute(
        """
        INSERT INTO jobs (
            id,
            environment_id,
            brand_id,
            content_request_id,
            job_type,
            resource_type,
            resource_id,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, 'content_generation', ?, ?,
                '2026-11-16', '2026-11-16')
        """,
        (
            job_id,
            environment_id,
            brand_id,
            content_request_id,
            resource_type,
            resource_id,
        ),
    )


@pytest.fixture
def job_context(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_brand(database, "brand-001", "env-001")
    create_brand(database, "brand-002", "env-001")
    create_brand(database, "brand-003", "env-002")

    create_content_request(database, "request-001", "brand-001")
    create_content_request(database, "request-002", "brand-002")

    return database


def test_job_can_exist_without_content_request(job_context):
    database = job_context

    create_job(
        database,
        job_id="job-001",
        environment_id="env-001",
        brand_id="brand-001",
        resource_type="document",
        resource_id="document-001",
    )


@pytest.mark.parametrize(
    "resource_type",
    [
        "content_request",
        "document",
        "post",
        "post_version",
    ],
)
def test_job_accepts_allowed_resource_types(job_context, resource_type):
    database = job_context

    if resource_type == "content_request":
        create_job(
            database,
            job_id=f"job-{resource_type}",
            environment_id="env-001",
            brand_id="brand-001",
            content_request_id="request-001",
            resource_type=resource_type,
            resource_id="request-001",
        )
    else:
        create_job(
            database,
            job_id=f"job-{resource_type}",
            environment_id="env-001",
            brand_id="brand-001",
            resource_type=resource_type,
            resource_id="resource-001",
        )


def test_job_accepts_null_resource_type(job_context):
    database = job_context

    create_job(
        database,
        job_id="job-null-resource-type",
        environment_id="env-001",
        brand_id="brand-001",
        resource_type=None,
        resource_id=None,
    )


@pytest.mark.parametrize(
    ("resource_type", "resource_id", "brand_id"),
    [
        ("document", None, "brand-001"),
        (None, "document-001", "brand-001"),
        ("document", "document-001", None),
    ],
)
def test_job_rejects_incomplete_resource_reference_on_insert(
    job_context, resource_type, resource_id, brand_id
):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        create_job(
            database,
            job_id="job-incomplete-resource",
            environment_id="env-001",
            brand_id=brand_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )



@pytest.mark.parametrize(
    "resource_type",
    ["image", "video", "invalid_type"],
)
def test_job_rejects_invalid_resource_type(job_context, resource_type):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        create_job(
            database,
            job_id=f"job-invalid-{resource_type}",
            environment_id="env-001",
            brand_id="brand-001",
            resource_type=resource_type,
            resource_id="resource-001",
        )


def test_job_can_reference_content_request_from_same_brand(job_context):
    database = job_context

    create_job(
        database,
        job_id="job-002",
        environment_id="env-001",
        brand_id="brand-001",
        content_request_id="request-001",
        resource_type="content_request",
        resource_id="request-001",
    )


def test_job_cannot_reference_request_from_another_brand(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        create_job(
            database,
            job_id="job-003",
            environment_id="env-001",
            brand_id="brand-001",
            content_request_id="request-002",
            resource_type="content_request",
            resource_id="request-002",
        )


def test_job_with_content_request_requires_brand(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        create_job(
            database,
            job_id="job-004",
            environment_id="env-001",
            content_request_id="request-001",
            resource_type="content_request",
            resource_id="request-001",
        )


def test_job_with_content_request_requires_matching_resource_type(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        create_job(
            database,
            job_id="job-005",
            environment_id="env-001",
            brand_id="brand-001",
            content_request_id="request-001",
            resource_type="document",
            resource_id="request-001",
        )


def test_job_with_content_request_requires_matching_resource_id(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        create_job(
            database,
            job_id="job-006",
            environment_id="env-001",
            brand_id="brand-001",
            content_request_id="request-001",
            resource_type="content_request",
            resource_id="request-999",
        )


def test_job_without_content_request_cannot_use_content_request_type(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        create_job(
            database,
            job_id="job-007",
            environment_id="env-001",
            brand_id="brand-001",
            resource_type="content_request",
            resource_id="request-001",
        )


def test_job_cannot_use_brand_from_another_environment(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        create_job(
            database,
            job_id="job-008",
            environment_id="env-001",
            brand_id="brand-003",
        )


def test_jobs_content_request_index_exists(job_context):
    database = job_context

    indexes = database.execute(
        "PRAGMA index_list('jobs')"
    ).fetchall()

    index_names = [row[1] for row in indexes]

    assert "ix_jobs_brand_content_request" in index_names


def test_jobs_content_request_index_is_partial(job_context):
    database = job_context

    result = database.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'index'
          AND name = 'ix_jobs_brand_content_request'
        """
    ).fetchone()

    assert result is not None

    index_sql = result[0].lower().replace(" ", "")

    assert "wherecontent_request_idisnotnull" in index_sql


def insert_job(database, **overrides):
    values = {
        "id": "job-extra",
        "environment_id": "env-001",
        "job_type": "content_generation",
        "created_at": "2026-11-16",
        "updated_at": "2026-11-16",
    }

    values.update(overrides)

    columns = ", ".join(values.keys())
    placeholders = ", ".join(f":{column}" for column in values)

    database.execute(
        f"""
        INSERT INTO jobs ({columns})
        VALUES ({placeholders})
        """,
        values,
    )


# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "status",
    ["queued", "processing", "completed", "failed", "cancelled"],
)
def test_job_accepts_valid_status(job_context, status):
    database = job_context

    insert_job(database, status=status)

    result = database.execute(
        "SELECT status FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == status


@pytest.mark.parametrize(
    "status",
    ["pending", "active", "done", "invalid", ""],
)
def test_job_rejects_invalid_status(job_context, status):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, status=status)


def test_job_uses_default_status(job_context):
    database = job_context

    insert_job(database)

    result = database.execute(
        "SELECT status FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == "queued"


def test_job_rejects_null_status(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, status=None)


# ---------------------------------------------------------
# PROGRESS
# ---------------------------------------------------------

@pytest.mark.parametrize("progress", [0, 1, 50, 99, 100])
def test_job_accepts_valid_progress(job_context, progress):
    database = job_context

    insert_job(database, progress=progress)

    result = database.execute(
        "SELECT progress FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == progress


@pytest.mark.parametrize("progress", [-1, 101, 200])
def test_job_rejects_invalid_progress(job_context, progress):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, progress=progress)


def test_job_uses_default_progress(job_context):
    database = job_context

    insert_job(database)

    result = database.execute(
        "SELECT progress FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == 0


def test_job_rejects_null_progress(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, progress=None)


# ---------------------------------------------------------
# ATTEMPTS
# ---------------------------------------------------------

@pytest.mark.parametrize("attempts", [0, 1, 2, 10])
def test_job_accepts_valid_attempts(job_context, attempts):
    database = job_context

    insert_job(database, attempts=attempts)

    result = database.execute(
        "SELECT attempts FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == attempts


@pytest.mark.parametrize("attempts", [-1, -10])
def test_job_rejects_negative_attempts(job_context, attempts):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, attempts=attempts)


def test_job_uses_default_attempts(job_context):
    database = job_context

    insert_job(database)

    result = database.execute(
        "SELECT attempts FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == 0


def test_job_rejects_null_attempts(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, attempts=None)


# ---------------------------------------------------------
# MAX ATTEMPTS
# ---------------------------------------------------------

@pytest.mark.parametrize("max_attempts", [1, 2, 3, 10])
def test_job_accepts_valid_max_attempts(job_context, max_attempts):
    database = job_context

    insert_job(database, max_attempts=max_attempts)

    result = database.execute(
        "SELECT max_attempts FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == max_attempts


@pytest.mark.parametrize("max_attempts", [0, -1, -10])
def test_job_rejects_invalid_max_attempts(job_context, max_attempts):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, max_attempts=max_attempts)


def test_job_uses_default_max_attempts(job_context):
    database = job_context

    insert_job(database)

    result = database.execute(
        "SELECT max_attempts FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == 3


def test_job_rejects_null_max_attempts(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, max_attempts=None)


# ---------------------------------------------------------
# PAYLOAD JSON
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        "[]",
        '{"task": "generation"}',
        '"texto"',
        "123",
        "true",
        "null",
    ],
)
def test_job_accepts_valid_payload_json(job_context, payload):
    database = job_context

    insert_job(database, payload_json=payload)

    result = database.execute(
        "SELECT payload_json FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == payload


@pytest.mark.parametrize(
    "payload",
    ["", "texto", "{invalid json}", '{"task": }', "[1, 2,]"],
)
def test_job_rejects_invalid_payload_json(job_context, payload):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, payload_json=payload)


def test_job_uses_default_payload_json(job_context):
    database = job_context

    insert_job(database)

    result = database.execute(
        "SELECT payload_json FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == "{}"


def test_job_rejects_null_payload_json(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, payload_json=None)


# ---------------------------------------------------------
# RESULT JSON
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "result_json",
    [
        "{}",
        "[]",
        '{"success": true}',
        '"resultado"',
        "123",
        "false",
        "null",
    ],
)
def test_job_accepts_valid_result_json(job_context, result_json):
    database = job_context

    insert_job(database, result_json=result_json)

    result = database.execute(
        "SELECT result_json FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] == result_json


@pytest.mark.parametrize(
    "result_json",
    ["", "texto", "{invalid json}", '{"success": }', "[1, 2,]"],
)
def test_job_rejects_invalid_result_json(job_context, result_json):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, result_json=result_json)


def test_job_accepts_null_result_json(job_context):
    database = job_context

    insert_job(database, result_json=None)

    result = database.execute(
        "SELECT result_json FROM jobs WHERE id = 'job-extra'"
    ).fetchone()

    assert result[0] is None


# ---------------------------------------------------------
# CAMPOS OBRIGATÓRIOS
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "column",
    [
        "environment_id",
        "job_type",
        "status",
        "progress",
        "attempts",
        "max_attempts",
        "payload_json",
        "created_at",
        "updated_at",
    ],
)
def test_job_requires_mandatory_fields(job_context, column):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, **{column: None})


# ---------------------------------------------------------
# INTEGRIDADE REFERENCIAL
# ---------------------------------------------------------

def test_job_rejects_nonexistent_environment(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(database, environment_id="env-inexistente")


def test_job_rejects_nonexistent_brand(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(
            database,
            brand_id="brand-inexistente",
        )


def test_job_rejects_nonexistent_content_request(job_context):
    database = job_context

    with pytest.raises(sqlite3.IntegrityError):
        insert_job(
            database,
            brand_id="brand-001",
            content_request_id="request-inexistente",
            resource_type="content_request",
            resource_id="request-inexistente",
        )


def test_job_prevents_deleting_referenced_brand(job_context):
    database = job_context

    insert_job(
        database,
        brand_id="brand-001",
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM brands WHERE id = 'brand-001'"
        )


def test_job_prevents_deleting_referenced_content_request(job_context):
    database = job_context

    insert_job(
        database,
        brand_id="brand-001",
        content_request_id="request-001",
        resource_type="content_request",
        resource_id="request-001",
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM content_requests WHERE id = 'request-001'"
        )


# ---------------------------------------------------------
# ATUALIZAÇÕES
# ---------------------------------------------------------

def test_job_rejects_invalid_status_on_update(job_context):
    database = job_context

    insert_job(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "UPDATE jobs SET status = 'invalid' WHERE id = 'job-extra'"
        )


def test_job_rejects_invalid_progress_on_update(job_context):
    database = job_context

    insert_job(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "UPDATE jobs SET progress = 101 WHERE id = 'job-extra'"
        )


def test_job_rejects_negative_attempts_on_update(job_context):
    database = job_context

    insert_job(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "UPDATE jobs SET attempts = -1 WHERE id = 'job-extra'"
        )


def test_job_rejects_invalid_max_attempts_on_update(job_context):
    database = job_context

    insert_job(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "UPDATE jobs SET max_attempts = 0 WHERE id = 'job-extra'"
        )


def test_job_rejects_invalid_payload_json_on_update(job_context):
    database = job_context

    insert_job(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE jobs
            SET payload_json = '{invalid json}'
            WHERE id = 'job-extra'
            """
        )


def test_job_rejects_invalid_result_json_on_update(job_context):
    database = job_context

    insert_job(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE jobs
            SET result_json = '{invalid json}'
            WHERE id = 'job-extra'
            """
        )


def test_job_rejects_inconsistent_content_request_on_update(job_context):
    database = job_context

    insert_job(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE jobs
            SET content_request_id = 'request-001'
            WHERE id = 'job-extra'
            """
        )


def test_job_rejects_mismatched_resource_id_on_update(job_context):
    database = job_context

    insert_job(
        database,
        brand_id="brand-001",
        content_request_id="request-001",
        resource_type="content_request",
        resource_id="request-001",
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE jobs
            SET resource_id = 'request-999'
            WHERE id = 'job-extra'
            """
        )


@pytest.mark.parametrize(
    ("sql", "parameters"),
    [
        (
            "UPDATE jobs SET resource_id = NULL WHERE id = ?",
            ("job-update-resource",),
        ),
        (
            "UPDATE jobs SET resource_type = NULL WHERE id = ?",
            ("job-update-resource",),
        ),
        (
            "UPDATE jobs SET brand_id = NULL WHERE id = ?",
            ("job-update-resource",),
        ),
    ],
)
def test_job_rejects_incomplete_resource_reference_on_update(
    job_context, sql, parameters
):
    database = job_context

    create_job(
        database,
        job_id="job-update-resource",
        environment_id="env-001",
        brand_id="brand-001",
        resource_type="document",
        resource_id="document-001",
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(sql, parameters)
