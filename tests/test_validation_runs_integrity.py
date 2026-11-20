
import json
import sqlite3

import pytest


def create_environment(database):
    database.execute(
        """
        INSERT INTO environments (
            id, name, created_at, updated_at
        )
        VALUES (
            'env-001', 'Teste',
            '2026-11-16', '2026-11-16'
        )
        """
    )


def create_user(database):
    database.execute(
        """
        INSERT INTO users (
            id, environment_id, name, created_at
        )
        VALUES (
            'user-001', 'env-001', 'Usuário de teste', '2026-11-16'
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


def create_content_request(database):
    database.execute(
        """
        INSERT INTO content_requests (
            id, brand_id, operation, platforms,
            profile_snapshot_json, created_at, updated_at
        )
        VALUES (
            'request-001', 'brand-001', 'create',
            '["instagram"]', '{}', '2026-11-16', '2026-11-16'
        )
        """
    )


def create_post(database):
    database.execute(
        """
        INSERT INTO posts (
            id, request_id, brand_id, platform,
            created_at, updated_at
        )
        VALUES (
            'post-001', 'request-001', 'brand-001',
            'instagram', '2026-11-16', '2026-11-16'
        )
        """
    )


def create_post_version(database):
    database.execute(
        """
        INSERT INTO post_versions (
            id, post_id, brand_id, version_number,
            content, origin_type, created_at
        )
        VALUES (
            'version-001', 'post-001', 'brand-001',
            1, 'Conteúdo de teste', 'generated', '2026-11-16'
        )
        """
    )

    database.execute(
        """
        UPDATE posts
        SET current_version_id = 'version-001'
        WHERE id = 'post-001'
        """
    )


@pytest.fixture
def validation_context(database):
    create_environment(database)
    create_user(database)
    create_brand(database)
    create_content_request(database)
    create_post(database)
    create_post_version(database)

    return database


def create_validation(
    database,
    results_json='{"checks": []}',
    overall_status='passed',
    version_id='version-001',
):
    database.execute(
        """
        INSERT INTO validation_runs (
            id, version_id, overall_status,
            results_json, validator_version, created_at
        )
        VALUES (
            'validation-001', ?, ?, ?, '1.0.0', '2026-11-16'
        )
        """,
        (version_id, overall_status, results_json),
    )


@pytest.mark.parametrize(
    "status",
    ["passed", "warning", "failed"],
)
def test_validation_accepts_valid_status(validation_context, status):
    create_validation(validation_context, overall_status=status)


def test_validation_rejects_invalid_status(validation_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_validation(validation_context, overall_status="invalid")


def test_validation_accepts_json_object(validation_context):
    create_validation(
        validation_context,
        results_json='{"checks": [], "score": 95}',
    )


@pytest.mark.parametrize(
    "value",
    [
        "[]",
        '"texto"',
        "123",
        "true",
        "null",
    ],
)
def test_validation_rejects_valid_json_non_objects(
    validation_context,
    value,
):
    with pytest.raises(sqlite3.IntegrityError):
        create_validation(validation_context, results_json=value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "texto",
        "{invalid json}",
        '{"checks": }',
    ],
)
def test_validation_rejects_invalid_json(validation_context, value):
    with pytest.raises(sqlite3.IntegrityError):
        create_validation(validation_context, results_json=value)


def test_validation_requires_results_json(validation_context):
    with pytest.raises(sqlite3.IntegrityError):
        validation_context.execute(
            """
            INSERT INTO validation_runs (
                id, version_id, overall_status,
                validator_version, created_at
            )
            VALUES (
                'validation-001', 'version-001',
                'passed', '1.0.0', '2026-11-16'
            )
            """
        )


def test_validation_requires_validator_version(validation_context):
    with pytest.raises(sqlite3.IntegrityError):
        validation_context.execute(
            """
            INSERT INTO validation_runs (
                id, version_id, overall_status,
                results_json, created_at
            )
            VALUES (
                'validation-001', 'version-001',
                'passed', '{}', '2026-11-16'
            )
            """
        )


def test_validation_rejects_nonexistent_version(validation_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_validation(
            validation_context,
            version_id="version-inexistente",
        )


def test_validation_preserves_version_relationship(validation_context):
    create_validation(validation_context)

    with pytest.raises(sqlite3.IntegrityError):
        validation_context.execute(
            "DELETE FROM post_versions WHERE id = 'version-001'"
        )


def test_validation_allows_multiple_runs_for_same_version(
    validation_context,
):
    create_validation(validation_context)

    validation_context.execute(
        """
        INSERT INTO validation_runs (
            id, version_id, overall_status,
            results_json, validator_version, created_at
        )
        VALUES (
            'validation-002', 'version-001',
            'warning', '{"checks": ["warning"]}',
            '1.0.0', '2026-11-16'
        )
        """
    )

    count = validation_context.execute(
        """
        SELECT COUNT(*)
        FROM validation_runs
        WHERE version_id = 'version-001'
        """
    ).fetchone()[0]

    assert count == 2
