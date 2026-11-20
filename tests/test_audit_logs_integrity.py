
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


def create_user(database, user_id, environment_id):
    database.execute(
        """
        INSERT INTO users (
            id, environment_id, name, email, status, created_at
        )
        VALUES (?, ?, ?, ?, 'active', '2026-11-16')
        """,
        (user_id, environment_id, user_id, f"{user_id}@example.com"),
    )


def create_audit_log(
    database,
    log_id="audit-001",
    environment_id="env-001",
    user_id=None,
    action="create",
    resource_type="post",
    resource_id=None,
    details_json=None,
):
    database.execute(
        """
        INSERT INTO audit_logs (
            id, environment_id, user_id, action,
            resource_type, resource_id, details_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id,
            environment_id,
            user_id,
            action,
            resource_type,
            resource_id,
            details_json,
            "2026-11-16",
        ),
    )


@pytest.fixture
def audit_context(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_user(database, "user-001", "env-001")
    create_user(database, "user-002", "env-001")
    create_user(database, "user-003", "env-002")

    return database


# ---------------------------------------------------------
# INSERÇÃO E CAMPOS OBRIGATÓRIOS
# ---------------------------------------------------------

def test_audit_log_accepts_valid_data(audit_context):
    database = audit_context

    create_audit_log(
        database,
        user_id="user-001",
        resource_id="post-001",
        details_json='{"source": "test"}',
    )

    result = database.execute(
        """
        SELECT id, environment_id, user_id, action,
               resource_type, resource_id
        FROM audit_logs
        WHERE id = 'audit-001'
        """
    ).fetchone()

    assert result == (
        "audit-001",
        "env-001",
        "user-001",
        "create",
        "post",
        "post-001",
    )


@pytest.mark.parametrize(
    "column",
    [
        "environment_id",
        "action",
        "resource_type",
        "created_at",
    ],
)
def test_audit_log_requires_mandatory_fields(audit_context, column):
    database = audit_context

    values = {
        "id": "audit-001",
        "environment_id": "env-001",
        "action": "create",
        "resource_type": "post",
        "created_at": "2026-11-16",
    }

    values[column] = None

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO audit_logs (
                id, environment_id, action,
                resource_type, created_at
            )
            VALUES (
                :id, :environment_id, :action,
                :resource_type, :created_at
            )
            """,
            values,
        )


# ---------------------------------------------------------
# CAMPOS OPCIONAIS
# ---------------------------------------------------------

def test_audit_log_accepts_null_optional_fields(audit_context):
    database = audit_context

    create_audit_log(database)

    result = database.execute(
        """
        SELECT user_id, resource_id, details_json
        FROM audit_logs
        WHERE id = 'audit-001'
        """
    ).fetchone()

    assert result == (None, None, None)


def test_audit_log_accepts_all_optional_fields(audit_context):
    database = audit_context

    create_audit_log(
        database,
        user_id="user-001",
        resource_id="post-001",
        details_json='{"key": "value"}',
    )

    result = database.execute(
        """
        SELECT user_id, resource_id, details_json
        FROM audit_logs
        WHERE id = 'audit-001'
        """
    ).fetchone()

    assert result == (
        "user-001",
        "post-001",
        '{"key": "value"}',
    )


# ---------------------------------------------------------
# VALIDAÇÃO DO JSON
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "details_json",
    [
        "{}",
        "[]",
        '{"action": "create"}',
        '["item1", "item2"]',
        '"texto"',
        "123",
        "true",
        "false",
        "null",
    ],
)
def test_audit_log_accepts_valid_json(audit_context, details_json):
    database = audit_context

    create_audit_log(database, details_json=details_json)

    result = database.execute(
        "SELECT details_json FROM audit_logs"
    ).fetchone()

    assert result[0] == details_json


def test_audit_log_accepts_null_json(audit_context):
    database = audit_context

    create_audit_log(database, details_json=None)

    result = database.execute(
        "SELECT details_json FROM audit_logs"
    ).fetchone()

    assert result[0] is None


@pytest.mark.parametrize(
    "details_json",
    [
        "",
        "{invalid}",
        '{"key": }',
        "[1, 2,",
        "undefined",
        "not-json",
    ],
)
def test_audit_log_rejects_invalid_json(audit_context, details_json):
    database = audit_context

    with pytest.raises(sqlite3.IntegrityError):
        create_audit_log(database, details_json=details_json)


def test_audit_log_rejects_invalid_json_on_update(audit_context):
    database = audit_context

    create_audit_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE audit_logs
            SET details_json = '{invalid}'
            WHERE id = 'audit-001'
            """
        )


# ---------------------------------------------------------
# INTEGRIDADE REFERENCIAL DO AMBIENTE
# ---------------------------------------------------------

def test_audit_log_rejects_nonexistent_environment(audit_context):
    database = audit_context

    with pytest.raises(sqlite3.IntegrityError):
        create_audit_log(
            database,
            environment_id="env-inexistente",
        )


def test_audit_log_prevents_deleting_referenced_environment(
    audit_context,
):
    database = audit_context

    create_audit_log(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM environments WHERE id = 'env-001'"
        )


def test_audit_log_rejects_environment_from_another_record(
    audit_context,
):
    database = audit_context

    with pytest.raises(sqlite3.IntegrityError):
        create_audit_log(
            database,
            environment_id="env-002",
            user_id="user-001",
        )


# ---------------------------------------------------------
# INTEGRIDADE REFERENCIAL DO USUÁRIO
# ---------------------------------------------------------

def test_audit_log_accepts_user_from_same_environment(audit_context):
    database = audit_context

    create_audit_log(database, user_id="user-001")

    result = database.execute(
        "SELECT user_id FROM audit_logs"
    ).fetchone()

    assert result[0] == "user-001"


def test_audit_log_rejects_nonexistent_user(audit_context):
    database = audit_context

    with pytest.raises(sqlite3.IntegrityError):
        create_audit_log(
            database,
            user_id="user-inexistente",
        )


def test_audit_log_rejects_user_from_another_environment(
    audit_context,
):
    database = audit_context

    with pytest.raises(sqlite3.IntegrityError):
        create_audit_log(
            database,
            user_id="user-003",
        )


def test_audit_log_accepts_null_user(audit_context):
    database = audit_context

    create_audit_log(database, user_id=None)

    result = database.execute(
        "SELECT user_id FROM audit_logs"
    ).fetchone()

    assert result[0] is None


def test_audit_log_rejects_user_from_another_environment_on_update(
    audit_context,
):
    database = audit_context

    create_audit_log(database, user_id="user-001")

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE audit_logs
            SET user_id = 'user-003'
            WHERE id = 'audit-001'
            """
        )


def test_audit_log_rejects_environment_change_incompatible_with_user(
    audit_context,
):
    database = audit_context

    create_audit_log(database, user_id="user-001")

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE audit_logs
            SET environment_id = 'env-002'
            WHERE id = 'audit-001'
            """
        )


# ---------------------------------------------------------
# TRIGGER DE PRESERVAÇÃO DO HISTÓRICO
# ---------------------------------------------------------

def test_deleting_user_preserves_audit_log(audit_context):
    database = audit_context

    create_audit_log(
        database,
        user_id="user-001",
        resource_id="post-001",
        details_json='{"source": "test"}',
    )

    database.execute(
        "DELETE FROM users WHERE id = 'user-001'"
    )

    result = database.execute(
        """
        SELECT id, environment_id, user_id,
               action, resource_type, resource_id, details_json
        FROM audit_logs
        WHERE id = 'audit-001'
        """
    ).fetchone()

    assert result == (
        "audit-001",
        "env-001",
        None,
        "create",
        "post",
        "post-001",
        '{"source": "test"}',
    )


def test_deleting_user_does_not_delete_audit_log(audit_context):
    database = audit_context

    create_audit_log(
        database,
        user_id="user-001",
    )

    database.execute(
        "DELETE FROM users WHERE id = 'user-001'"
    )

    count = database.execute(
        "SELECT COUNT(*) FROM audit_logs"
    ).fetchone()[0]

    assert count == 1


def test_deleting_user_preserves_other_users_audit_logs(
    audit_context,
):
    database = audit_context

    create_audit_log(
        database,
        log_id="audit-001",
        user_id="user-001",
    )

    create_audit_log(
        database,
        log_id="audit-002",
        user_id="user-002",
    )

    database.execute(
        "DELETE FROM users WHERE id = 'user-001'"
    )

    results = database.execute(
        """
        SELECT id, user_id
        FROM audit_logs
        ORDER BY id
        """
    ).fetchall()

    assert results == [
        ("audit-001", None),
        ("audit-002", "user-002"),
    ]


def test_deleting_user_does_not_affect_other_environment_logs(
    audit_context,
):
    database = audit_context

    create_audit_log(
        database,
        log_id="audit-001",
        user_id="user-001",
    )

    create_audit_log(
        database,
        log_id="audit-002",
        environment_id="env-002",
        user_id="user-003",
    )

    database.execute(
        "DELETE FROM users WHERE id = 'user-001'"
    )

    results = database.execute(
        """
        SELECT id, user_id
        FROM audit_logs
        ORDER BY id
        """
    ).fetchall()

    assert results == [
        ("audit-001", None),
        ("audit-002", "user-003"),
    ]


# ---------------------------------------------------------
# ATUALIZAÇÕES E RELACIONAMENTOS
# ---------------------------------------------------------

def test_audit_log_accepts_update_of_action(audit_context):
    database = audit_context

    create_audit_log(database)

    database.execute(
        """
        UPDATE audit_logs
        SET action = 'update'
        WHERE id = 'audit-001'
        """
    )

    result = database.execute(
        "SELECT action FROM audit_logs"
    ).fetchone()

    assert result[0] == "update"


def test_audit_log_accepts_update_of_resource_id(audit_context):
    database = audit_context

    create_audit_log(database)

    database.execute(
        """
        UPDATE audit_logs
        SET resource_id = 'post-002'
        WHERE id = 'audit-001'
        """
    )

    result = database.execute(
        "SELECT resource_id FROM audit_logs"
    ).fetchone()

    assert result[0] == "post-002"


def test_audit_log_accepts_update_of_user_to_null(audit_context):
    database = audit_context

    create_audit_log(database, user_id="user-001")

    database.execute(
        """
        UPDATE audit_logs
        SET user_id = NULL
        WHERE id = 'audit-001'
        """
    )

    result = database.execute(
        "SELECT user_id FROM audit_logs"
    ).fetchone()

    assert result[0] is None
