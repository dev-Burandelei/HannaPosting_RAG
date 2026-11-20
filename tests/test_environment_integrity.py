
import pytest
import sqlite3


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


def create_user(database, user_id, environment_id):
    database.execute(
        """
        INSERT INTO users (
            id, environment_id, name, status, created_at
        )
        VALUES (?, ?, ?, 'active', '2026-11-16')
        """,
        (user_id, environment_id, f"Usuário {user_id}"),
    )


def test_job_rejects_brand_from_another_environment(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_brand(database, "brand-002", "env-002")

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO jobs (
                id, environment_id, brand_id, job_type,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "job-001",
                "env-001",
                "brand-002",
                "content_generation",
                "2026-11-16",
                "2026-11-16",
            ),
        )


def test_audit_log_rejects_user_from_another_environment(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_user(database, "user-002", "env-002")

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO audit_logs (
                id, environment_id, user_id,
                action, resource_type, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "audit-001",
                "env-001",
                "user-002",
                "update",
                "brand",
                "2026-11-16",
            ),
        )


def test_usage_logs_has_environment_id(database):
    columns = {
        row[1]
        for row in database.execute(
            "PRAGMA table_info(usage_logs)"
        ).fetchall()
    }

    assert "environment_id" in columns, (
        "usage_logs precisa ter environment_id "
        "para garantir a integridade entre ambientes."
    )
    

def create_provider(database, provider_id, environment_id):
    database.execute(
        """
        INSERT INTO provider_configs (
            id, environment_id, provider, model,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            provider_id,
            environment_id,
            "gemini",
            "gemini-flash-latest",
            "2026-11-16",
            "2026-11-16",
        ),
    )


def create_job(database, job_id, environment_id):
    database.execute(
        """
        INSERT INTO jobs (
            id, environment_id, job_type,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            job_id,
            environment_id,
            "content_generation",
            "2026-11-16",
            "2026-11-16",
        ),
    )


def create_usage_log(
    database,
    log_id,
    environment_id,
    provider_id,
    job_id=None,
    brand_id=None,
):
    database.execute(
        """
        INSERT INTO usage_logs (
            id, environment_id, provider_config_id,
            job_id, brand_id, operation, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id,
            environment_id,
            provider_id,
            job_id,
            brand_id,
            "content_generation",
            "success",
            "2026-11-16",
        ),
    )
    
    

def test_usage_log_rejects_provider_from_another_environment(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_provider(database, "provider-002", "env-002")

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            "usage-001",
            "env-001",
            "provider-002",
        )


def test_usage_log_rejects_job_from_another_environment(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_provider(database, "provider-001", "env-001")
    create_job(database, "job-002", "env-002")

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            "usage-001",
            "env-001",
            "provider-001",
            job_id="job-002",
        )


def test_usage_log_rejects_brand_from_another_environment(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_provider(database, "provider-001", "env-001")
    create_brand(database, "brand-002", "env-002")

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            "usage-001",
            "env-001",
            "provider-001",
            brand_id="brand-002",
        )


def test_deleting_job_preserves_usage_log(database):
    create_environment(database, "env-001")
    create_provider(database, "provider-001", "env-001")
    create_job(database, "job-001", "env-001")

    create_usage_log(
        database,
        "usage-001",
        "env-001",
        "provider-001",
        job_id="job-001",
    )

    database.execute(
        "DELETE FROM jobs WHERE id = ?",
        ("job-001",),
    )

    log = database.execute(
        """
        SELECT environment_id, job_id
        FROM usage_logs
        WHERE id = ?
        """,
        ("usage-001",),
    ).fetchone()

    assert log == ("env-001", None)


def test_deleting_user_preserves_audit_log(database):
    create_environment(database, "env-001")
    create_user(database, "user-001", "env-001")

    database.execute(
        """
        INSERT INTO audit_logs (
            id, environment_id, user_id,
            action, resource_type, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "audit-001",
            "env-001",
            "user-001",
            "update",
            "brand",
            "2026-11-16",
        ),
    )

    database.execute(
        "DELETE FROM users WHERE id = ?",
        ("user-001",),
    )

    log = database.execute(
        """
        SELECT environment_id, user_id
        FROM audit_logs
        WHERE id = ?
        """,
        ("audit-001",),
    ).fetchone()

    assert log == ("env-001", None)

