
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


def create_provider_config(database, config_id, environment_id):
    database.execute(
        """
        INSERT INTO provider_configs (
            id, environment_id, provider, model,
            created_at, updated_at
        )
        VALUES (?, ?, 'gemini', 'gemini-flash-latest',
                '2026-11-16', '2026-11-16')
        """,
        (config_id, environment_id),
    )


def create_job(database, job_id, environment_id, brand_id=None):
    database.execute(
        """
        INSERT INTO jobs (
            id, environment_id, brand_id, job_type,
            created_at, updated_at
        )
        VALUES (?, ?, ?, 'content_generation',
                '2026-11-16', '2026-11-16')
        """,
        (job_id, environment_id, brand_id),
    )


def create_usage_log(
    database,
    log_id="log-001",
    environment_id="env-001",
    provider_config_id="config-001",
    job_id=None,
    brand_id=None,
    operation="generation",
    input_tokens=0,
    output_tokens=0,
    estimated_cost=None,
    currency=None,
    latency_ms=None,
    status="success",
    request_id=None,
):
    database.execute(
        """
        INSERT INTO usage_logs (
            id, environment_id, provider_config_id,
            job_id, brand_id, operation,
            input_tokens, output_tokens,
            estimated_cost, currency, latency_ms,
            status, request_id, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id,
            environment_id,
            provider_config_id,
            job_id,
            brand_id,
            operation,
            input_tokens,
            output_tokens,
            estimated_cost,
            currency,
            latency_ms,
            status,
            request_id,
            "2026-11-16",
        ),
    )


@pytest.fixture
def usage_context(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_brand(database, "brand-001", "env-001")
    create_brand(database, "brand-002", "env-001")
    create_brand(database, "brand-003", "env-002")

    create_provider_config(database, "config-001", "env-001")
    create_provider_config(database, "config-002", "env-002")

    create_job(database, "job-001", "env-001", "brand-001")
    create_job(database, "job-002", "env-002", "brand-003")

    return database


# ---------------------------------------------------------
# INSERÇÃO E CAMPOS OBRIGATÓRIOS
# ---------------------------------------------------------

def test_usage_log_accepts_valid_data(usage_context):
    database = usage_context

    create_usage_log(database)

    result = database.execute(
        """
        SELECT id, environment_id, provider_config_id,
               operation, status
        FROM usage_logs
        WHERE id = ?
        """,
        ("log-001",),
    ).fetchone()

    assert result == (
        "log-001",
        "env-001",
        "config-001",
        "generation",
        "success",
    )


@pytest.mark.parametrize(
    "column",
    [
        "environment_id",
        "provider_config_id",
        "operation",
        "status",
        "created_at",
    ],
)
def test_usage_log_requires_mandatory_fields(usage_context, column):
    database = usage_context

    values = {
        "id": "log-001",
        "environment_id": "env-001",
        "provider_config_id": "config-001",
        "operation": "generation",
        "status": "success",
        "created_at": "2026-11-16",
    }

    values[column] = None

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO usage_logs (
                id, environment_id, provider_config_id,
                operation, status, created_at
            )
            VALUES (
                :id, :environment_id, :provider_config_id,
                :operation, :status, :created_at
            )
            """,
            values,
        )


# ---------------------------------------------------------
# VALORES PADRÃO DOS TOKENS
# ---------------------------------------------------------

def test_usage_log_uses_default_input_tokens(usage_context):
    database = usage_context

    create_usage_log(database)

    result = database.execute(
        "SELECT input_tokens FROM usage_logs"
    ).fetchone()

    assert result[0] == 0


def test_usage_log_uses_default_output_tokens(usage_context):
    database = usage_context

    create_usage_log(database)

    result = database.execute(
        "SELECT output_tokens FROM usage_logs"
    ).fetchone()

    assert result[0] == 0


@pytest.mark.parametrize("tokens", [0, 1, 100, 100000])
def test_usage_log_accepts_valid_input_tokens(usage_context, tokens):
    database = usage_context

    create_usage_log(database, input_tokens=tokens)

    result = database.execute(
        "SELECT input_tokens FROM usage_logs"
    ).fetchone()

    assert result[0] == tokens


@pytest.mark.parametrize("tokens", [-1, -10])
def test_usage_log_rejects_negative_input_tokens(usage_context, tokens):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(database, input_tokens=tokens)


@pytest.mark.parametrize("tokens", [0, 1, 100, 100000])
def test_usage_log_accepts_valid_output_tokens(usage_context, tokens):
    database = usage_context

    create_usage_log(database, output_tokens=tokens)

    result = database.execute(
        "SELECT output_tokens FROM usage_logs"
    ).fetchone()

    assert result[0] == tokens


@pytest.mark.parametrize("tokens", [-1, -10])
def test_usage_log_rejects_negative_output_tokens(usage_context, tokens):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(database, output_tokens=tokens)


def test_usage_log_rejects_null_input_tokens(usage_context):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(database, input_tokens=None)


def test_usage_log_rejects_null_output_tokens(usage_context):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(database, output_tokens=None)


# ---------------------------------------------------------
# CUSTO ESTIMADO
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "cost",
    [0, 0.01, 1, 10.5, 1000],
)
def test_usage_log_accepts_valid_estimated_cost(usage_context, cost):
    database = usage_context

    create_usage_log(database, estimated_cost=cost)

    result = database.execute(
        "SELECT estimated_cost FROM usage_logs"
    ).fetchone()

    assert float(result[0]) == pytest.approx(float(cost))


def test_usage_log_accepts_null_estimated_cost(usage_context):
    database = usage_context

    create_usage_log(database, estimated_cost=None)

    result = database.execute(
        "SELECT estimated_cost FROM usage_logs"
    ).fetchone()

    assert result[0] is None


@pytest.mark.parametrize("cost", [-0.01, -1, -100])
def test_usage_log_rejects_negative_estimated_cost(usage_context, cost):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(database, estimated_cost=cost)


# ---------------------------------------------------------
# MOEDA
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "currency",
    ["BRL", "USD", "EUR", "JPY"],
)
def test_usage_log_accepts_three_character_currency(
    usage_context, currency
):
    database = usage_context

    create_usage_log(database, currency=currency)

    result = database.execute(
        "SELECT currency FROM usage_logs"
    ).fetchone()

    assert result[0] == currency


def test_usage_log_accepts_null_currency(usage_context):
    database = usage_context

    create_usage_log(database, currency=None)

    result = database.execute(
        "SELECT currency FROM usage_logs"
    ).fetchone()

    assert result[0] is None


@pytest.mark.parametrize(
    "currency",
    ["", "B", "BR", "BRLL", "USDD"],
)
def test_usage_log_rejects_invalid_currency_length(
    usage_context, currency
):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(database, currency=currency)


# ---------------------------------------------------------
# LATÊNCIA
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "latency",
    [0, 1, 100, 1000, 60000],
)
def test_usage_log_accepts_valid_latency(usage_context, latency):
    database = usage_context

    create_usage_log(database, latency_ms=latency)

    result = database.execute(
        "SELECT latency_ms FROM usage_logs"
    ).fetchone()

    assert result[0] == latency


def test_usage_log_accepts_null_latency(usage_context):
    database = usage_context

    create_usage_log(database, latency_ms=None)

    result = database.execute(
        "SELECT latency_ms FROM usage_logs"
    ).fetchone()

    assert result[0] is None


@pytest.mark.parametrize("latency", [-1, -100])
def test_usage_log_rejects_negative_latency(usage_context, latency):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(database, latency_ms=latency)


# ---------------------------------------------------------
# CAMPOS OPCIONAIS
# ---------------------------------------------------------

def test_usage_log_accepts_null_optional_fields(usage_context):
    database = usage_context

    create_usage_log(
        database,
        job_id=None,
        brand_id=None,
        estimated_cost=None,
        currency=None,
        latency_ms=None,
        request_id=None,
    )

    result = database.execute(
        """
        SELECT job_id, brand_id, estimated_cost,
               currency, latency_ms, request_id
        FROM usage_logs
        """
    ).fetchone()

    assert result == (None, None, None, None, None, None)


def test_usage_log_accepts_optional_fields(usage_context):
    database = usage_context

    create_usage_log(
        database,
        job_id="job-001",
        brand_id="brand-001",
        estimated_cost=1.25,
        currency="BRL",
        latency_ms=500,
        request_id="request-001",
    )

    result = database.execute(
        """
        SELECT job_id, brand_id, estimated_cost,
               currency, latency_ms, request_id
        FROM usage_logs
        """
    ).fetchone()

    assert result == (
        "job-001",
        "brand-001",
        1.25,
        "BRL",
        500,
        "request-001",
    )


# ---------------------------------------------------------
# STATUS E OPERATION
# ---------------------------------------------------------

def test_usage_log_accepts_arbitrary_status(usage_context):
    database = usage_context

    create_usage_log(database, status="custom_status")

    result = database.execute(
        "SELECT status FROM usage_logs"
    ).fetchone()

    assert result[0] == "custom_status"


def test_usage_log_accepts_arbitrary_operation(usage_context):
    database = usage_context

    create_usage_log(database, operation="custom_operation")

    result = database.execute(
        "SELECT operation FROM usage_logs"
    ).fetchone()

    assert result[0] == "custom_operation"


# ---------------------------------------------------------
# INTEGRIDADE REFERENCIAL
# ---------------------------------------------------------

def test_usage_log_rejects_nonexistent_environment(usage_context):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            environment_id="env-inexistente",
        )


def test_usage_log_rejects_nonexistent_provider_config(usage_context):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            provider_config_id="config-inexistente",
        )


def test_usage_log_rejects_provider_from_another_environment(
    usage_context,
):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            provider_config_id="config-002",
        )


def test_usage_log_rejects_nonexistent_job(usage_context):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            job_id="job-inexistente",
        )


def test_usage_log_rejects_job_from_another_environment(
    usage_context,
):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            job_id="job-002",
        )


def test_usage_log_rejects_nonexistent_brand(usage_context):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            brand_id="brand-inexistente",
        )


def test_usage_log_rejects_brand_from_another_environment(
    usage_context,
):
    database = usage_context

    with pytest.raises(sqlite3.IntegrityError):
        create_usage_log(
            database,
            brand_id="brand-003",
        )


def test_usage_log_preserves_environment_relationship(usage_context):
    database = usage_context

    create_usage_log(database)

    result = database.execute(
        """
        SELECT e.id
        FROM usage_logs ul
        JOIN environments e
          ON e.id = ul.environment_id
        WHERE ul.id = 'log-001'
        """
    ).fetchone()

    assert result[0] == "env-001"


def test_usage_log_prevents_deleting_referenced_environment(
    usage_context,
):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM environments WHERE id = 'env-001'"
        )


def test_usage_log_prevents_deleting_referenced_provider_config(
    usage_context,
):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM provider_configs WHERE id = 'config-001'"
        )


def test_usage_log_prevents_deleting_referenced_brand(usage_context):
    database = usage_context

    create_usage_log(
        database,
        brand_id="brand-001",
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM brands WHERE id = 'brand-001'"
        )


# ---------------------------------------------------------
# TRIGGER DE PRESERVAÇÃO DE USAGE LOGS
# ---------------------------------------------------------

def test_deleting_job_preserves_usage_log(usage_context):
    database = usage_context

    create_usage_log(
        database,
        job_id="job-001",
        brand_id="brand-001",
    )

    database.execute(
        "DELETE FROM jobs WHERE id = 'job-001'"
    )

    result = database.execute(
        """
        SELECT id, job_id, brand_id
        FROM usage_logs
        WHERE id = 'log-001'
        """
    ).fetchone()

    assert result == ("log-001", None, "brand-001")


def test_deleting_job_does_not_delete_usage_log(usage_context):
    database = usage_context

    create_usage_log(
        database,
        job_id="job-001",
        brand_id="brand-001",
    )

    database.execute(
        "DELETE FROM jobs WHERE id = 'job-001'"
    )

    count = database.execute(
        "SELECT COUNT(*) FROM usage_logs"
    ).fetchone()[0]

    assert count == 1


def test_usage_log_without_job_does_not_require_trigger(usage_context):
    database = usage_context

    create_usage_log(database, job_id=None)

    count = database.execute(
        "SELECT COUNT(*) FROM usage_logs"
    ).fetchone()[0]

    assert count == 1


# ---------------------------------------------------------
# ATUALIZAÇÕES
# ---------------------------------------------------------

def test_usage_log_rejects_negative_input_tokens_on_update(
    usage_context,
):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE usage_logs
            SET input_tokens = -1
            WHERE id = 'log-001'
            """
        )


def test_usage_log_rejects_negative_output_tokens_on_update(
    usage_context,
):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE usage_logs
            SET output_tokens = -1
            WHERE id = 'log-001'
            """
        )


def test_usage_log_rejects_negative_cost_on_update(usage_context):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE usage_logs
            SET estimated_cost = -1
            WHERE id = 'log-001'
            """
        )


def test_usage_log_rejects_invalid_currency_on_update(usage_context):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE usage_logs
            SET currency = 'BRLL'
            WHERE id = 'log-001'
            """
        )


def test_usage_log_rejects_negative_latency_on_update(usage_context):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE usage_logs
            SET latency_ms = -1
            WHERE id = 'log-001'
            """
        )


def test_usage_log_rejects_provider_from_another_environment_on_update(
    usage_context,
):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE usage_logs
            SET provider_config_id = 'config-002'
            WHERE id = 'log-001'
            """
        )


def test_usage_log_rejects_job_from_another_environment_on_update(
    usage_context,
):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE usage_logs
            SET job_id = 'job-002'
            WHERE id = 'log-001'
            """
        )


def test_usage_log_rejects_brand_from_another_environment_on_update(
    usage_context,
):
    database = usage_context

    create_usage_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE usage_logs
            SET brand_id = 'brand-003'
            WHERE id = 'log-001'
            """
        )
