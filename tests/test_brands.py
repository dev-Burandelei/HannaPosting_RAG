import json

import pytest

import sqlite3

from app.services.brand_profiles import build_empty_profile_snapshot

from app.services.brands import (
    create_brand,
    get_brand,
    list_brands,
    update_brand,
    deactivate_brand,
    reactivate_brand,
    soft_delete_brand,
    set_default_brand,
)


def create_environment(database, environment_id="env-001", status="active"):
    database.execute(
        """
        INSERT INTO environments (
            id, name, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            environment_id,
            "Ambiente de teste",
            status,
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )


def test_create_brand_successfully(database):
    create_environment(database)

    brand_id = create_brand(
        database,
        environment_id="env-001",
        name="Marca de teste",
        description="Descrição da marca",
    )

    result = database.execute(
        """
        SELECT id, environment_id, name, description,
               is_default, is_active, deleted_at
        FROM brands
        WHERE id = ?
        """,
        (brand_id,),
    ).fetchone()

    assert result is not None
    assert result[0] == brand_id
    assert result[1] == "env-001"
    assert result[2] == "Marca de teste"
    assert result[3] == "Descrição da marca"
    assert result[4] == 0
    assert result[5] == 1
    assert result[6] is None


def test_create_brand_without_description(database):
    create_environment(database)

    brand_id = create_brand(
        database,
        environment_id="env-001",
        name="Marca sem descrição",
    )

    result = database.execute(
        "SELECT description FROM brands WHERE id = ?",
        (brand_id,),
    ).fetchone()

    assert result[0] is None


@pytest.mark.parametrize("name", ["", " ", "   "])
def test_create_brand_rejects_empty_name(database, name):
    create_environment(database)

    with pytest.raises(ValueError, match="nome da marca é obrigatório"):
        create_brand(database, "env-001", name)


def test_create_brand_rejects_nonexistent_environment(database):
    with pytest.raises(LookupError, match="Ambiente não encontrado"):
        create_brand(database, "env-inexistente", "Marca de teste")


def test_create_brand_rejects_inactive_environment(database):
    create_environment(database, status="inactive")

    with pytest.raises(ValueError, match="ambiente inativo"):
        create_brand(database, "env-001", "Marca de teste")


def test_create_brand_generates_unique_ids(database):
    create_environment(database)

    first_id = create_brand(database, "env-001", "Marca 1")
    second_id = create_brand(database, "env-001", "Marca 2")

    assert first_id != second_id
    
def test_get_brand_successfully(database):
    create_environment(database)

    brand_id = create_brand(
        database,
        "env-001",
        "Marca de teste",
        "Descrição da marca",
    )

    result = get_brand(database, brand_id, "env-001")

    assert result is not None
    assert result["id"] == brand_id
    assert result["environment_id"] == "env-001"
    assert result["name"] == "Marca de teste"
    assert result["description"] == "Descrição da marca"
    assert result["is_active"] == 1
    assert result["deleted_at"] is None


def test_get_brand_returns_none_for_nonexistent_brand(database):
    create_environment(database)

    result = get_brand(database, "brand-inexistente", "env-001")

    assert result is None


def test_get_brand_respects_environment_isolation(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    brand_id = create_brand(database, "env-001", "Marca de teste")

    result = get_brand(database, brand_id, "env-002")

    assert result is None


def test_get_brand_ignores_soft_deleted_brands(database):
    create_environment(database)

    brand_id = create_brand(database, "env-001", "Marca excluída")

    database.execute(
        """
        UPDATE brands
        SET deleted_at = ?
        WHERE id = ?
        """,
        ("2026-01-01T00:00:00+00:00", brand_id),
    )

    result = get_brand(database, brand_id, "env-001")

    assert result is None


def test_get_brand_returns_inactive_brands(database):
    create_environment(database)

    brand_id = create_brand(database, "env-001", "Marca inativa")

    database.execute(
        """
        UPDATE brands
        SET is_active = 0
        WHERE id = ?
        """,
        (brand_id,),
    )

    result = get_brand(database, brand_id, "env-001")

    assert result is not None
    assert result["is_active"] == 0
    
    

    
def test_list_brands_successfully(database):
    create_environment(database)

    create_brand(database, "env-001", "Marca A")
    create_brand(database, "env-001", "Marca B")
    create_brand(database, "env-001", "Marca C")

    results = list_brands(database, "env-001")

    assert len(results) == 3
    assert [brand["name"] for brand in results] == [
        "Marca A",
        "Marca B",
        "Marca C",
    ]


def test_list_brands_returns_empty_list_when_no_brands_exist(database):
    create_environment(database)

    results = list_brands(database, "env-001")

    assert results == []


def test_list_brands_respects_environment_isolation(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    create_brand(database, "env-001", "Marca A")
    create_brand(database, "env-002", "Marca B")

    results = list_brands(database, "env-001")

    assert len(results) == 1
    assert results[0]["name"] == "Marca A"
    assert results[0]["environment_id"] == "env-001"


def test_list_brands_ignores_soft_deleted_brands(database):
    create_environment(database)

    active_brand_id = create_brand(
        database, "env-001", "Marca ativa"
    )
    deleted_brand_id = create_brand(
        database, "env-001", "Marca excluída"
    )

    database.execute(
        """
        UPDATE brands
        SET deleted_at = ?
        WHERE id = ?
        """,
        ("2026-01-01T00:00:00+00:00", deleted_brand_id),
    )

    results = list_brands(database, "env-001")

    assert len(results) == 1
    assert results[0]["id"] == active_brand_id


def test_list_brands_includes_inactive_brands(database):
    create_environment(database)

    brand_id = create_brand(
        database, "env-001", "Marca inativa"
    )

    database.execute(
        """
        UPDATE brands
        SET is_active = 0
        WHERE id = ?
        """,
        (brand_id,),
    )

    results = list_brands(database, "env-001")

    assert len(results) == 1
    assert results[0]["is_active"] == 0


def test_list_brands_orders_names_without_case_sensitivity(database):
    create_environment(database)

    create_brand(database, "env-001", "beta")
    create_brand(database, "env-001", "Alfa")
    create_brand(database, "env-001", "Charlie")

    results = list_brands(database, "env-001")

    assert [brand["name"] for brand in results] == [
        "Alfa",
        "beta",
        "Charlie",
    ]
    
def test_update_brand_name_successfully(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca original")

    result = update_brand(
        database,
        brand_id,
        "env-001",
        name="Marca atualizada",
    )

    assert result is not None
    assert result["name"] == "Marca atualizada"


def test_update_brand_description_successfully(database):
    create_environment(database)
    brand_id = create_brand(
        database, "env-001", "Marca", "Descrição original"
    )

    result = update_brand(
        database,
        brand_id,
        "env-001",
        description="Nova descrição",
    )

    assert result["description"] == "Nova descrição"


def test_update_brand_removes_description(database):
    create_environment(database)
    brand_id = create_brand(
        database, "env-001", "Marca", "Descrição original"
    )

    result = update_brand(
        database,
        brand_id,
        "env-001",
        description=None,
    )

    assert result["description"] is None


def test_update_brand_preserves_description_when_not_informed(database):
    create_environment(database)
    brand_id = create_brand(
        database, "env-001", "Marca", "Descrição original"
    )

    result = update_brand(
        database,
        brand_id,
        "env-001",
        name="Novo nome",
    )

    assert result["name"] == "Novo nome"
    assert result["description"] == "Descrição original"


def test_update_brand_updates_both_fields(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca original")

    result = update_brand(
        database,
        brand_id,
        "env-001",
        name="Marca atualizada",
        description="Nova descrição",
    )

    assert result["name"] == "Marca atualizada"
    assert result["description"] == "Nova descrição"


@pytest.mark.parametrize("name", ["", " ", "   "])
def test_update_brand_rejects_empty_name(database, name):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca original")

    with pytest.raises(ValueError, match="nome da marca é obrigatório"):
        update_brand(
            database,
            brand_id,
            "env-001",
            name=name,
        )


def test_update_brand_rejects_when_no_fields_are_informed(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca original")

    with pytest.raises(ValueError, match="pelo menos um campo"):
        update_brand(database, brand_id, "env-001")


def test_update_brand_returns_none_for_nonexistent_brand(database):
    create_environment(database)

    result = update_brand(
        database,
        "brand-inexistente",
        "env-001",
        name="Nova marca",
    )

    assert result is None


def test_update_brand_respects_environment_isolation(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    brand_id = create_brand(database, "env-001", "Marca original")

    result = update_brand(
        database,
        brand_id,
        "env-002",
        name="Tentativa de alteração",
    )

    assert result is None

    original = get_brand(database, brand_id, "env-001")
    assert original["name"] == "Marca original"


def test_update_brand_ignores_soft_deleted_brands(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca original")

    database.execute(
        """
        UPDATE brands
        SET deleted_at = ?
        WHERE id = ?
        """,
        ("2026-01-01T00:00:00+00:00", brand_id),
    )

    result = update_brand(
        database,
        brand_id,
        "env-001",
        name="Tentativa de alteração",
    )

    assert result is None


def test_update_brand_allows_inactive_brands(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca original")

    database.execute(
        """
        UPDATE brands
        SET is_active = 0
        WHERE id = ?
        """,
        (brand_id,),
    )

    result = update_brand(
        database,
        brand_id,
        "env-001",
        name="Marca atualizada",
    )

    assert result is not None
    assert result["name"] == "Marca atualizada"
    assert result["is_active"] == 0


def test_update_brand_changes_updated_at(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca original")

    original = get_brand(database, brand_id, "env-001")

    result = update_brand(
        database,
        brand_id,
        "env-001",
        name="Marca atualizada",
    )

    assert result["updated_at"] >= original["updated_at"]
    
    

def test_deactivate_brand_successfully(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    result = deactivate_brand(database, brand_id, "env-001")

    assert result is not None
    assert result["is_active"] == 0
    assert result["deleted_at"] is None


def test_deactivate_brand_rejects_default_brand(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca padrão")

    database.execute(
        """
        UPDATE brands
        SET is_default = 1
        WHERE id = ?
        """,
        (brand_id,),
    )

    with pytest.raises(ValueError, match="marca padrão"):
        deactivate_brand(database, brand_id, "env-001")


def test_deactivate_brand_keeps_inactive_brand_unchanged(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    database.execute(
        """
        UPDATE brands
        SET is_active = 0
        WHERE id = ?
        """,
        (brand_id,),
    )

    original = get_brand(database, brand_id, "env-001")

    result = deactivate_brand(database, brand_id, "env-001")

    assert result == original
    assert result["is_active"] == 0


def test_deactivate_brand_returns_none_for_nonexistent_brand(database):
    create_environment(database)

    result = deactivate_brand(
        database,
        "brand-inexistente",
        "env-001",
    )

    assert result is None


def test_deactivate_brand_respects_environment_isolation(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    brand_id = create_brand(database, "env-001", "Marca")

    result = deactivate_brand(database, brand_id, "env-002")

    assert result is None

    original = get_brand(database, brand_id, "env-001")
    assert original["is_active"] == 1


def test_deactivate_brand_ignores_soft_deleted_brands(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    database.execute(
        """
        UPDATE brands
        SET deleted_at = ?
        WHERE id = ?
        """,
        ("2026-01-01T00:00:00+00:00", brand_id),
    )

    result = deactivate_brand(database, brand_id, "env-001")

    assert result is None
    
def test_reactivate_brand_successfully(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    deactivate_brand(database, brand_id, "env-001")

    result = reactivate_brand(database, brand_id, "env-001")

    assert result is not None
    assert result["is_active"] == 1
    assert result["deleted_at"] is None


def test_reactivate_brand_keeps_active_brand_unchanged(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    original = get_brand(database, brand_id, "env-001")

    result = reactivate_brand(database, brand_id, "env-001")

    assert result == original
    assert result["is_active"] == 1


def test_reactivate_brand_returns_none_for_nonexistent_brand(database):
    create_environment(database)

    result = reactivate_brand(
        database,
        "brand-inexistente",
        "env-001",
    )

    assert result is None


def test_reactivate_brand_respects_environment_isolation(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    brand_id = create_brand(database, "env-001", "Marca")
    deactivate_brand(database, brand_id, "env-001")

    result = reactivate_brand(database, brand_id, "env-002")

    assert result is None

    original = get_brand(database, brand_id, "env-001")
    assert original["is_active"] == 0


def test_reactivate_brand_ignores_soft_deleted_brands(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    deactivate_brand(database, brand_id, "env-001")

    database.execute(
        """
        UPDATE brands
        SET deleted_at = ?
        WHERE id = ?
        """,
        ("2026-01-01T00:00:00+00:00", brand_id),
    )

    result = reactivate_brand(database, brand_id, "env-001")

    assert result is None


def test_reactivate_brand_allows_default_brand(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca padrão")

    database.execute(
        """
        UPDATE brands
        SET is_default = 1, is_active = 0
        WHERE id = ?
        """,
        (brand_id,),
    )

    result = reactivate_brand(database, brand_id, "env-001")

    assert result is not None
    assert result["is_active"] == 1
    assert result["is_default"] == 1
    
    
def test_soft_delete_brand_successfully(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    result = soft_delete_brand(database, brand_id, "env-001")

    assert result is not None
    assert result["id"] == brand_id
    assert result["deleted_at"] is not None
    assert result["updated_at"] == result["deleted_at"]
    assert result["is_active"] == 1

    assert get_brand(database, brand_id, "env-001") is None


def test_soft_delete_brand_rejects_default_brand(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca padrão")

    database.execute(
        """
        UPDATE brands
        SET is_default = 1
        WHERE id = ?
        """,
        (brand_id,),
    )

    with pytest.raises(ValueError, match="marca padrão"):
        soft_delete_brand(database, brand_id, "env-001")


def test_soft_delete_brand_returns_none_for_nonexistent_brand(database):
    create_environment(database)

    result = soft_delete_brand(
        database,
        "brand-inexistente",
        "env-001",
    )

    assert result is None


def test_soft_delete_brand_respects_environment_isolation(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    brand_id = create_brand(database, "env-001", "Marca")

    result = soft_delete_brand(database, brand_id, "env-002")

    assert result is None

    original = get_brand(database, brand_id, "env-001")
    assert original is not None
    assert original["deleted_at"] is None


def test_soft_delete_brand_can_delete_inactive_brand(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    deactivate_brand(database, brand_id, "env-001")

    result = soft_delete_brand(database, brand_id, "env-001")

    assert result is not None
    assert result["id"] == brand_id
    assert result["deleted_at"] is not None
    assert result["is_active"] == 0

    assert get_brand(database, brand_id, "env-001") is None


def test_soft_delete_brand_does_not_physically_delete_record(database):
    create_environment(database)
    brand_id = create_brand(database, "env-001", "Marca")

    soft_delete_brand(database, brand_id, "env-001")

    result = database.execute(
        "SELECT id FROM brands WHERE id = ?",
        (brand_id,),
    ).fetchone()

    assert result is not None
    
    
def test_set_default_brand_successfully(database):
    create_environment(database)

    brand_id = create_brand(database, "env-001", "Marca")

    result = set_default_brand(database, brand_id, "env-001")

    assert result is not None
    assert result["id"] == brand_id
    assert result["is_default"] == 1
    assert result["is_active"] == 1


def test_set_default_brand_replaces_previous_default(database):
    create_environment(database)

    first_id = create_brand(database, "env-001", "Marca 1")
    second_id = create_brand(database, "env-001", "Marca 2")

    set_default_brand(database, first_id, "env-001")

    result = set_default_brand(database, second_id, "env-001")

    first_brand = get_brand(database, first_id, "env-001")

    assert result is not None
    assert result["id"] == second_id
    assert result["is_default"] == 1
    assert first_brand["is_default"] == 0


def test_set_default_brand_keeps_current_default_unchanged(database):
    create_environment(database)

    brand_id = create_brand(database, "env-001", "Marca")

    first_result = set_default_brand(database, brand_id, "env-001")
    second_result = set_default_brand(database, brand_id, "env-001")

    assert second_result["is_default"] == 1
    assert second_result["updated_at"] == first_result["updated_at"]


def test_set_default_brand_rejects_inactive_brand(database):
    create_environment(database)

    brand_id = create_brand(database, "env-001", "Marca")

    deactivate_brand(database, brand_id, "env-001")

    result = set_default_brand(database, brand_id, "env-001")

    assert result is None


def test_set_default_brand_returns_none_for_nonexistent_brand(database):
    create_environment(database)

    result = set_default_brand(
        database,
        "brand-inexistente",
        "env-001",
    )

    assert result is None


def test_set_default_brand_respects_environment_isolation(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    brand_id = create_brand(database, "env-001", "Marca")

    result = set_default_brand(database, brand_id, "env-002")

    assert result is None


def test_set_default_brand_ignores_soft_deleted_brands(database):
    create_environment(database)

    brand_id = create_brand(database, "env-001", "Marca")

    database.execute(
        """
        UPDATE brands
        SET deleted_at = ?
        WHERE id = ?
        """,
        ("2026-01-01T00:00:00+00:00", brand_id),
    )

    result = set_default_brand(database, brand_id, "env-001")

    assert result is None
    
    
def test_set_default_brand_does_not_affect_other_environments(database):
    create_environment(database, "env-001")
    create_environment(database, "env-002")

    first_id = create_brand(database, "env-001", "Marca 1")
    second_id = create_brand(database, "env-002", "Marca 2")

    set_default_brand(database, first_id, "env-001")
    set_default_brand(database, second_id, "env-002")

    new_brand_id = create_brand(database, "env-001", "Marca 3")

    set_default_brand(database, new_brand_id, "env-001")

    first_default = get_brand(database, first_id, "env-001")
    second_default = get_brand(database, second_id, "env-002")
    new_default = get_brand(database, new_brand_id, "env-001")

    assert first_default["is_default"] == 0
    assert second_default["is_default"] == 1
    assert new_default["is_default"] == 1
    

def test_set_default_brand_preserves_previous_default_when_target_is_inactive(database):
    create_environment(database)

    first_id = create_brand(database, "env-001", "Marca padrão")
    second_id = create_brand(database, "env-001", "Marca inativa")

    set_default_brand(database, first_id, "env-001")
    deactivate_brand(database, second_id, "env-001")

    result = set_default_brand(database, second_id, "env-001")

    first_brand = get_brand(database, first_id, "env-001")

    assert result is None
    assert first_brand["is_default"] == 1

def test_create_brand_creates_initial_profile_and_version(database):
    create_environment(database)

    brand_id = create_brand(
        database,
        environment_id="env-001",
        name="Marca de teste",
    )

    profile = database.execute(
        """
        SELECT id, brand_id
        FROM brand_profiles
        WHERE brand_id = ?
        """,
        (brand_id,),
    ).fetchone()

    assert profile is not None
    assert profile[1] == brand_id

    versions = database.execute(
        """
        SELECT
            version_number,
            profile_data_json,
            created_by
        FROM brand_profile_versions
        WHERE brand_id = ?
          AND brand_profile_id = ?
        """,
        (brand_id, profile[0]),
    ).fetchall()

    assert len(versions) == 1
    assert versions[0][0] == 1
    assert json.loads(versions[0][1]) == build_empty_profile_snapshot()
    assert versions[0][2] is None


def test_create_brand_can_be_rolled_back_when_initial_profile_creation_fails(database):
    create_environment(database)

    database.execute(
        """
        CREATE TRIGGER fail_initial_profile_version
        BEFORE INSERT ON brand_profile_versions
        BEGIN
            SELECT RAISE(ABORT, 'Falha simulada na versão inicial');
        END;
        """
    )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="Falha simulada na versão inicial",
    ):
        try:
            create_brand(
                database,
                environment_id="env-001",
                name="Marca de teste",
            )
        except Exception:
            database.rollback()
            raise

    brand_count = database.execute(
        "SELECT COUNT(*) FROM brands WHERE name = ?",
        ("Marca de teste",),
    ).fetchone()[0]

    profile_count = database.execute(
        """
        SELECT COUNT(*)
        FROM brand_profiles
        WHERE brand_id IN (
            SELECT id FROM brands WHERE name = ?
        )
        """,
        ("Marca de teste",),
    ).fetchone()[0]

    assert brand_count == 0
    assert profile_count == 0
