
import sqlite3
import pytest


def create_environment(database, environment_id="env-1"):
    database.execute(
        """
        INSERT INTO environments (
            id, name, created_at, updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            environment_id,
            "Ambiente de teste",
            "2026-01-01T10:00:00",
            "2026-01-01T10:00:00",
        ),
    )
    return environment_id


def create_brand(database, brand_id="brand-1", environment_id="env-1"):
    database.execute(
        """
        INSERT INTO brands (
            id, environment_id, name,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            brand_id,
            environment_id,
            f"Marca {brand_id}",
            "2026-01-01T10:00:00",
            "2026-01-01T10:00:00",
        ),
    )
    return brand_id


def create_tag(
    database,
    tag_id="tag-1",
    brand_id="brand-1",
    name="Tecnologia",
    category="assunto",
    is_custom=0,
):
    database.execute(
        """
        INSERT INTO tags (
            id, brand_id, name, category,
            is_custom, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            tag_id,
            brand_id,
            name,
            category,
            is_custom,
            "2026-01-01T10:00:00",
        ),
    )
    return tag_id


@pytest.fixture
def tag_context(database):
    create_environment(database)
    create_brand(database)

    return {
        "brand_id": "brand-1",
    }


def test_tag_accepts_valid_data(database, tag_context):
    create_tag(database)

    result = database.execute(
        "SELECT id, brand_id, name, category, is_custom FROM tags"
    ).fetchone()

    assert result == (
        "tag-1",
        "brand-1",
        "Tecnologia",
        "assunto",
        0,
    )


@pytest.mark.parametrize("is_custom", [0, 1])
def test_tag_accepts_valid_is_custom_values(
    database, tag_context, is_custom
):
    create_tag(database, is_custom=is_custom)

    result = database.execute(
        "SELECT is_custom FROM tags WHERE id = ?",
        ("tag-1",),
    ).fetchone()

    assert result[0] == is_custom


@pytest.mark.parametrize("is_custom", [-1, 2, 3, 100])
def test_tag_rejects_invalid_is_custom_values(
    database, tag_context, is_custom
):
    with pytest.raises(sqlite3.IntegrityError):
        create_tag(database, is_custom=is_custom)


def test_tag_uses_default_is_custom(database, tag_context):
    database.execute(
        """
        INSERT INTO tags (
            id, brand_id, name, category, created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "tag-1",
            "brand-1",
            "Tecnologia",
            "assunto",
            "2026-01-01T10:00:00",
        ),
    )

    result = database.execute(
        "SELECT is_custom FROM tags WHERE id = ?",
        ("tag-1",),
    ).fetchone()

    assert result[0] == 0


@pytest.mark.parametrize(
    "column",
    ["brand_id", "name", "category", "created_at"],
)
def test_tag_requires_mandatory_fields(
    database, tag_context, column
):
    values = {
        "id": "tag-1",
        "brand_id": "brand-1",
        "name": "Tecnologia",
        "category": "assunto",
        "is_custom": 0,
        "created_at": "2026-01-01T10:00:00",
    }

    values[column] = None

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            INSERT INTO tags (
                id, brand_id, name, category,
                is_custom, created_at
            )
            VALUES (
                :id, :brand_id, :name, :category,
                :is_custom, :created_at
            )
            """,
            values,
        )


def test_tag_rejects_nonexistent_brand(database, tag_context):
    with pytest.raises(sqlite3.IntegrityError):
        create_tag(database, brand_id="brand-inexistente")


def test_tag_rejects_duplicate_id(database, tag_context):
    create_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_tag(
            database,
            tag_id="tag-1",
            name="Outro nome",
        )


def test_tag_rejects_duplicate_name_and_category_for_same_brand(
    database, tag_context
):
    create_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        create_tag(
            database,
            tag_id="tag-2",
            name="Tecnologia",
            category="assunto",
        )


def test_tag_allows_same_name_with_different_category(
    database, tag_context
):
    create_tag(database)

    create_tag(
        database,
        tag_id="tag-2",
        name="Tecnologia",
        category="segmento",
    )

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM tags
        WHERE brand_id = ? AND name = ?
        """,
        ("brand-1", "Tecnologia"),
    ).fetchone()[0]

    assert count == 2


def test_tag_allows_different_names_with_same_category(
    database, tag_context
):
    create_tag(database)

    create_tag(
        database,
        tag_id="tag-2",
        name="Inovação",
        category="assunto",
    )

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM tags
        WHERE brand_id = ? AND category = ?
        """,
        ("brand-1", "assunto"),
    ).fetchone()[0]

    assert count == 2


def test_tag_allows_same_name_and_category_for_different_brands(
    database, tag_context
):
    create_environment(database, "env-2")
    create_brand(database, "brand-2", "env-2")

    create_tag(database)

    create_tag(
        database,
        tag_id="tag-2",
        brand_id="brand-2",
        name="Tecnologia",
        category="assunto",
    )

    count = database.execute(
        """
        SELECT COUNT(*)
        FROM tags
        WHERE name = ? AND category = ?
        """,
        ("Tecnologia", "assunto"),
    ).fetchone()[0]

    assert count == 2


def test_tag_allows_multiple_tags_for_same_brand(
    database, tag_context
):
    create_tag(database)

    create_tag(
        database,
        tag_id="tag-2",
        name="Inovação",
    )

    count = database.execute(
        "SELECT COUNT(*) FROM tags WHERE brand_id = ?",
        ("brand-1",),
    ).fetchone()[0]

    assert count == 2


def test_tag_allows_same_name_in_different_categories(
    database, tag_context
):
    create_tag(database)

    create_tag(
        database,
        tag_id="tag-2",
        name="Tecnologia",
        category="formato",
    )

    count = database.execute(
        "SELECT COUNT(*) FROM tags WHERE brand_id = ?",
        ("brand-1",),
    ).fetchone()[0]

    assert count == 2


def test_tag_preserves_brand_relationship(database, tag_context):
    create_tag(database)

    result = database.execute(
        """
        SELECT b.id
        FROM tags t
        JOIN brands b ON b.id = t.brand_id
        WHERE t.id = ?
        """,
        ("tag-1",),
    ).fetchone()

    assert result[0] == "brand-1"


def test_tag_prevents_deleting_referenced_brand(
    database, tag_context
):
    create_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "DELETE FROM brands WHERE id = ?",
            ("brand-1",),
        )


def test_tag_allows_updating_name(database, tag_context):
    create_tag(database)

    database.execute(
        "UPDATE tags SET name = ? WHERE id = ?",
        ("Inovação", "tag-1"),
    )

    result = database.execute(
        "SELECT name FROM tags WHERE id = ?",
        ("tag-1",),
    ).fetchone()

    assert result[0] == "Inovação"


def test_tag_allows_updating_category(database, tag_context):
    create_tag(database)

    database.execute(
        "UPDATE tags SET category = ? WHERE id = ?",
        ("formato", "tag-1"),
    )

    result = database.execute(
        "SELECT category FROM tags WHERE id = ?",
        ("tag-1",),
    ).fetchone()

    assert result[0] == "formato"


@pytest.mark.parametrize("is_custom", [-1, 2])
def test_tag_rejects_invalid_is_custom_on_update(
    database, tag_context, is_custom
):
    create_tag(database)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "UPDATE tags SET is_custom = ? WHERE id = ?",
            (is_custom, "tag-1"),
        )


def test_tag_rejects_update_creating_duplicate_combination(
    database, tag_context
):
    create_tag(database)

    create_tag(
        database,
        tag_id="tag-2",
        name="Inovação",
        category="assunto",
    )

    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            """
            UPDATE tags
            SET name = ?, category = ?
            WHERE id = ?
            """,
            ("Tecnologia", "assunto", "tag-2"),
        )


def test_tag_allows_updating_is_custom(database, tag_context):
    create_tag(database)

    database.execute(
        "UPDATE tags SET is_custom = 1 WHERE id = ?",
        ("tag-1",),
    )

    result = database.execute(
        "SELECT is_custom FROM tags WHERE id = ?",
        ("tag-1",),
    ).fetchone()

    assert result[0] == 1
