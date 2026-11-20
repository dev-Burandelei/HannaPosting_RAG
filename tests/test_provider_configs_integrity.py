
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


def create_provider_config(
    database,
    config_id="config-001",
    environment_id="env-001",
    provider="gemini",
    model="gemini-flash-latest",
    operation=None,
    encrypted_api_key=None,
    parameters_json="{}",
    limits_json="{}",
    is_active=1,
):
    database.execute(
        """
        INSERT INTO provider_configs (
            id, environment_id, provider, model,
            operation, encrypted_api_key,
            parameters_json, limits_json,
            is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            config_id,
            environment_id,
            provider,
            model,
            operation,
            encrypted_api_key,
            parameters_json,
            limits_json,
            is_active,
            "2026-11-16",
            "2026-11-16",
        ),
    )


@pytest.fixture
def provider_context(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    return database


def test_provider_config_accepts_valid_data(provider_context):
    database = provider_context

    create_provider_config(database)

    result = database.execute(
        """
        SELECT id, environment_id, provider, model,
               parameters_json, limits_json, is_active
        FROM provider_configs
        WHERE id = ?
        """,
        ("config-001",),
    ).fetchone()

    assert result == (
        "config-001",
        "env-001",
        "gemini",
        "gemini-flash-latest",
        "{}",
        "{}",
        1,
    )


@pytest.mark.parametrize("is_active", [0, 1])
def test_provider_config_accepts_valid_is_active_values(
    provider_context, is_active
):
    database = provider_context

    create_provider_config(database, is_active=is_active)

    result = database.execute(
        "SELECT is_active FROM provider_configs"
    ).fetchone()

    assert result[0] == is_active


@pytest.mark.parametrize("is_active", [-1, 2, 3, 100])
def test_provider_config_rejects_invalid_is_active_values(
    provider_context, is_active
):
    database = provider_context

    with pytest.raises(sqlite3.IntegrityError):
        create_provider_config(database, is_active=is_active)


def test_provider_config_uses_default_is_active(provider_context):
    database = provider_context

    database.execute(
        """
        INSERT INTO provider_configs (
            id, environment_id, provider, model,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "config-001",
            "env-001",
            "gemini",
            "gemini-flash-latest",
            "2026-11-16",
            "2026-11-16",
        ),
    )

    result = database.execute(
        "SELECT is_active FROM provider_configs"
    ).fetchone()

    assert result[0] == 1


def test_provider_config_uses_default_parameters_json(
    provider_context,
):
    database = provider_context

    database.execute(
        """
        INSERT INTO provider_configs (
            id, environment_id, provider, model,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "config-001",
            "env-001",
            "gemini",
            "gemini-flash-latest",
            "2026-11-16",
            "2026-11-16",
        ),
    )

    result = database.execute(
        "SELECT parameters_json FROM provider_configs"
    ).fetchone()

    assert result[0] == "{}"


def test_provider_config_uses_default_limits_json(provider_context):
    database = provider_context

    database.execute(
        """
        INSERT INTO provider_configs (
            id, environment_id, provider, model,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "config-001",
            "env-001",
            "gemini",
            "gemini-flash-latest",
            "2026-11-16",
            "2026-11-16",
        ),
    )

    result = database.execute(
        "SELECT limits_json FROM provider_configs"
    ).fetchone()

    assert result[0] == "{}"


@pytest.mark.parametrize(
    "column",
    [
        "environment_id",
        "provider",
        "model",
        "parameters_json",
        "limits_json",
        "is_active",
        "created_at",
        "updated_at",
    ],
)
def test_provider_config_requires_mandatory_fields(
    provider_context, column
):
    database = provider_context

    values = {
        "id": "config-001",
        "environment_id": "env-001",
        "provider": "gemini",
        "model": "gemini-flash-latest",
        "parameters_json": "{}",
        "limits_json": "{}",
        "is_active": 1,
        "created_at": "2026-11-16",
        "updated_at": "2026-11-16",
    }

    values[column] = None

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO provider_configs (
                id, environment_id, provider, model,
                parameters_json, limits_json, is_active,
                created_at, updated_at
            )
            VALUES (
                :id, :environment_id, :provider, :model,
                :parameters_json, :limits_json, :is_active,
                :created_at, :updated_at
            )
            """,
            values,
        )


def test_provider_config_rejects_nonexistent_environment(
    provider_context,
):
    database = provider_context

    with pytest.raises(sqlite3.IntegrityError):
        create_provider_config(
            database,
            environment_id="env-inexistente",
        )


def test_provider_config_rejects_duplicate_id(provider_context):
    database = provider_context

    create_provider_config(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_provider_config(
            database,
            config_id="config-001",
            provider="outro-provedor",
        )


def test_provider_config_rejects_duplicate_composite_key(
    provider_context,
):
    database = provider_context

    create_provider_config(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_provider_config(
            database,
            config_id="config-001",
        )


def test_provider_config_allows_multiple_configs_same_environment(
    provider_context,
):
    database = provider_context

    create_provider_config(database, config_id="config-001")
    create_provider_config(
        database,
        config_id="config-002",
        provider="llama",
        model="llama-model",
    )

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM provider_configs
        WHERE environment_id = ?
        """,
        ("env-001",),
    ).fetchone()[0]

    assert count == 2


def test_provider_config_allows_configs_in_different_environments(
    provider_context,
):
    database = provider_context

    create_provider_config(
        database,
        config_id="config-001",
        environment_id="env-001",
    )

    create_provider_config(
        database,
        config_id="config-002",
        environment_id="env-002",
    )

    count = database.execute(
        "SELECT COUNT(*) FROM provider_configs"
    ).fetchone()[0]

    assert count == 2


def test_provider_config_id_is_globally_unique(provider_context):
    database = provider_context

    create_provider_config(
        database,
        config_id="config-001",
        environment_id="env-001",
    )

    with pytest.raises(sqlite3.IntegrityError):
        create_provider_config(
            database,
            config_id="config-001",
            environment_id="env-002",
        )


def test_provider_config_accepts_null_optional_fields(
    provider_context,
):
    database = provider_context

    create_provider_config(
        database,
        operation=None,
        encrypted_api_key=None,
    )

    result = database.execute(
        """
        SELECT operation, encrypted_api_key
        FROM provider_configs
        WHERE id = ?
        """,
        ("config-001",),
    ).fetchone()

    assert result == (None, None)


def test_provider_config_accepts_optional_fields(provider_context):
    database = provider_context

    create_provider_config(
        database,
        operation="generation",
        encrypted_api_key="encrypted-test-key",
    )

    result = database.execute(
        """
        SELECT operation, encrypted_api_key
        FROM provider_configs
        WHERE id = ?
        """,
        ("config-001",),
    ).fetchone()

    assert result == ("generation", "encrypted-test-key")


@pytest.mark.parametrize(
    "json_value",
    [
        "{}",
        "[]",
        '{"temperature": 0.3}',
        '{"max_tokens": 1024}',
        '"texto"',
        "123",
        "true",
        "null",
    ],
)
def test_provider_config_accepts_valid_parameters_json(
    provider_context, json_value
):
    database = provider_context

    create_provider_config(
        database,
        parameters_json=json_value,
    )

    result = database.execute(
        "SELECT parameters_json FROM provider_configs"
    ).fetchone()

    assert result[0] == json_value


@pytest.mark.parametrize(
    "json_value",
    ["", "texto", "{invalid json}", '{"temperature": }', "[1, 2,]"],
)
def test_provider_config_rejects_invalid_parameters_json(
    provider_context, json_value
):
    database = provider_context

    with pytest.raises(sqlite3.IntegrityError):
        create_provider_config(
            database,
            parameters_json=json_value,
        )


@pytest.mark.parametrize(
    "json_value",
    [
        "{}",
        "[]",
        '{"requests_per_minute": 60}',
        '{"daily_limit": 1000}',
        '"texto"',
        "123",
        "true",
        "null",
    ],
)
def test_provider_config_accepts_valid_limits_json(
    provider_context, json_value
):
    database = provider_context

    create_provider_config(
        database,
        limits_json=json_value,
    )

    result = database.execute(
        "SELECT limits_json FROM provider_configs"
    ).fetchone()

    assert result[0] == json_value


@pytest.mark.parametrize(
    "json_value",
    ["", "texto", "{invalid json}", '{"limit": }', "[1, 2,]"],
)
def test_provider_config_rejects_invalid_limits_json(
    provider_context, json_value
):
    database = provider_context

    with pytest.raises(sqlite3.IntegrityError):
        create_provider_config(
            database,
            limits_json=json_value,
        )


def test_provider_config_preserves_environment_relationship(
    provider_context,
):
    database = provider_context

    create_provider_config(database)

    result = database.execute(
        """
        SELECT e.id
        FROM provider_configs pc
        JOIN environments e
          ON e.id = pc.environment_id
        WHERE pc.id = ?
        """,
        ("config-001",),
    ).fetchone()

    assert result[0] == "env-001"


def test_provider_config_prevents_deleting_referenced_environment(
    provider_context,
):
    database = provider_context

    create_provider_config(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM environments WHERE id = ?",
            ("env-001",),
        )


def test_provider_config_allows_updating_model(provider_context):
    database = provider_context

    create_provider_config(database)

    database.execute(
        """
        UPDATE provider_configs
        SET model = ?
        WHERE id = ?
        """,
        ("gemini-pro", "config-001"),
    )

    result = database.execute(
        "SELECT model FROM provider_configs WHERE id = ?",
        ("config-001",),
    ).fetchone()

    assert result[0] == "gemini-pro"


def test_provider_config_allows_updating_is_active(provider_context):
    database = provider_context

    create_provider_config(database)

    database.execute(
        """
        UPDATE provider_configs
        SET is_active = 0
        WHERE id = ?
        """,
        ("config-001",),
    )

    result = database.execute(
        "SELECT is_active FROM provider_configs WHERE id = ?",
        ("config-001",),
    ).fetchone()

    assert result[0] == 0


def test_provider_config_rejects_invalid_is_active_on_update(
    provider_context,
):
    database = provider_context

    create_provider_config(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE provider_configs
            SET is_active = 2
            WHERE id = ?
            """,
            ("config-001",),
        )


def test_provider_config_rejects_invalid_parameters_on_update(
    provider_context,
):
    database = provider_context

    create_provider_config(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE provider_configs
            SET parameters_json = ?
            WHERE id = ?
            """,
            ("{invalid json}", "config-001"),
        )


def test_provider_config_rejects_invalid_limits_on_update(
    provider_context,
):
    database = provider_context

    create_provider_config(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE provider_configs
            SET limits_json = ?
            WHERE id = ?
            """,
            ("{invalid json}", "config-001"),
        )
def test_provider_config_rejects_null_id(provider_context):
    database = provider_context

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO provider_configs (
                id, environment_id, provider, model,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                "env-001",
                "gemini",
                "gemini-flash-latest",
                "2026-11-16",
                "2026-11-16",
            ),
        )