from datetime import datetime, timezone
from uuid import uuid4

import sqlite3

class _Unset:
    """Representa um campo que não foi informado."""


_UNSET = _Unset()

def create_brand(
    connection: sqlite3.Connection,
    environment_id: str,
    name: str,
    description: str | None = None,
) -> str:
    """
    Cria uma marca em um ambiente ativo.

    Retorna o ID da marca criada.
    """

    if not name or not name.strip():
        raise ValueError("O nome da marca é obrigatório.")

    environment = connection.execute(
        """
        SELECT status
        FROM environments
        WHERE id = ?
        """,
        (environment_id,),
    ).fetchone()

    if environment is None:
        raise LookupError("Ambiente não encontrado.")

    if environment[0] != "active":
        raise ValueError("Não é possível criar marcas em um ambiente inativo.")

    brand_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        INSERT INTO brands (
            id,
            environment_id,
            name,
            description,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            brand_id,
            environment_id,
            name.strip(),
            description,
            now,
            now,
        ),
    )

    return brand_id

def get_brand(
    connection: sqlite3.Connection,
    brand_id: str,
    environment_id: str,
) -> dict | None:
    """
    Busca uma marca pelo ID dentro de seu ambiente.

    Marcas excluídas logicamente não são retornadas.
    """

    columns = (
        "id",
        "environment_id",
        "name",
        "description",
        "is_default",
        "is_active",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    result = connection.execute(
        """
        SELECT
            id,
            environment_id,
            name,
            description,
            is_default,
            is_active,
            created_at,
            updated_at,
            deleted_at
        FROM brands
        WHERE id = ?
          AND environment_id = ?
          AND deleted_at IS NULL
        """,
        (brand_id, environment_id),
    ).fetchone()

    if result is None:
        return None

    return dict(zip(columns, result))


def list_brands(
    connection: sqlite3.Connection,
    environment_id: str,
) -> list[dict]:
    """
    Lista as marcas não excluídas logicamente de um ambiente.

    Inclui marcas ativas e inativas.
    Ordena os resultados pelo nome.
    """

    columns = (
        "id",
        "environment_id",
        "name",
        "description",
        "is_default",
        "is_active",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    results = connection.execute(
        """
        SELECT
            id,
            environment_id,
            name,
            description,
            is_default,
            is_active,
            created_at,
            updated_at,
            deleted_at
        FROM brands
        WHERE environment_id = ?
          AND deleted_at IS NULL
        ORDER BY name COLLATE NOCASE ASC
        """,
        (environment_id,),
    ).fetchall()

    return [
        dict(zip(columns, result))
        for result in results
    ]
    
    
    
def update_brand(
    connection: sqlite3.Connection,
    brand_id: str,
    environment_id: str,
    name: str | None = None,
    description: str | None | _Unset = _UNSET,
) -> dict | None:
    """
    Atualiza os dados de uma marca não excluída.

    Retorna os dados atualizados ou None se a marca não existir
    no ambiente informado.
    """

    if name is None and isinstance(description, _Unset):
        raise ValueError("Informe pelo menos um campo para atualizar.")

    if name is not None:
        if not name or not name.strip():
            raise ValueError("O nome da marca é obrigatório.")

        name = name.strip()

    brand = get_brand(connection, brand_id, environment_id)

    if brand is None:
        return None

    updated_name = (
        name if name is not None else brand["name"]
    )

    updated_description = (
        brand["description"]
        if isinstance(description, _Unset)
        else description
    )

    now = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        UPDATE brands
        SET
            name = ?,
            description = ?,
            updated_at = ?
        WHERE id = ?
          AND environment_id = ?
          AND deleted_at IS NULL
        """,
        (
            updated_name,
            updated_description,
            now,
            brand_id,
            environment_id,
        ),
    )

    return get_brand(connection, brand_id, environment_id)


def deactivate_brand(
    connection: sqlite3.Connection,
    brand_id: str,
    environment_id: str,
) -> dict | None:
    """
    Desativa uma marca não excluída.

    Marcas padrão não podem ser desativadas.
    Retorna os dados atualizados ou None se não encontrada.
    """

    brand = get_brand(connection, brand_id, environment_id)

    if brand is None:
        return None

    if brand["is_default"] == 1:
        raise ValueError(
            "Não é possível desativar a marca padrão."
        )

    if brand["is_active"] == 0:
        return brand

    now = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        UPDATE brands
        SET
            is_active = 0,
            updated_at = ?
        WHERE id = ?
          AND environment_id = ?
          AND deleted_at IS NULL
        """,
        (now, brand_id, environment_id),
    )

    return get_brand(connection, brand_id, environment_id)


def reactivate_brand(
    connection: sqlite3.Connection,
    brand_id: str,
    environment_id: str,
) -> dict | None:
    """
    Reativa uma marca não excluída logicamente.

    Retorna os dados atualizados ou None se não encontrada.
    """

    brand = get_brand(connection, brand_id, environment_id)

    if brand is None:
        return None

    if brand["is_active"] == 1:
        return brand

    now = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        UPDATE brands
        SET
            is_active = 1,
            updated_at = ?
        WHERE id = ?
          AND environment_id = ?
          AND deleted_at IS NULL
        """,
        (now, brand_id, environment_id),
    )

    return get_brand(connection, brand_id, environment_id)


def soft_delete_brand(
    connection: sqlite3.Connection,
    brand_id: str,
    environment_id: str,
) -> dict | None:
    """
    Exclui logicamente uma marca não excluída.

    Marcas padrão não podem ser excluídas.
    Retorna os dados da marca excluída ou None se não encontrada.
    """

    brand = get_brand(connection, brand_id, environment_id)

    if brand is None:
        return None

    if brand["is_default"] == 1:
        raise ValueError(
            "Não é possível excluir a marca padrão."
        )

    now = datetime.now(timezone.utc).isoformat()

    connection.execute(
        """
        UPDATE brands
        SET
            deleted_at = ?,
            updated_at = ?
        WHERE id = ?
          AND environment_id = ?
          AND deleted_at IS NULL
        """,
        (now, now, brand_id, environment_id),
    )

    result = connection.execute(
        """
        SELECT
            id,
            environment_id,
            name,
            description,
            is_default,
            is_active,
            created_at,
            updated_at,
            deleted_at
        FROM brands
        WHERE id = ?
          AND environment_id = ?
        """,
        (brand_id, environment_id),
    ).fetchone()

    columns = (
        "id",
        "environment_id",
        "name",
        "description",
        "is_default",
        "is_active",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    return dict(zip(columns, result)) if result else None



def set_default_brand(
    connection: sqlite3.Connection,
    brand_id: str,
    environment_id: str,
) -> dict | None:
    """
    Define uma marca ativa como padrão do ambiente.

    A marca deve existir, estar ativa e não estar excluída.
    Retorna os dados atualizados ou None se não atender
    aos requisitos.
    """

    brand = get_brand(connection, brand_id, environment_id)

    if brand is None:
        return None

    if brand["is_active"] == 0:
        return None

    if brand["is_default"] == 1:
        return brand

    now = datetime.now(timezone.utc).isoformat()

    result = connection.execute(
        """
        UPDATE brands
        SET
            is_default = CASE
                WHEN id = ? THEN 1
                ELSE 0
            END,
            updated_at = ?
        WHERE environment_id = ?
          AND deleted_at IS NULL
          AND (
              is_default = 1
              OR (
                  id = ?
                  AND is_active = 1
              )
          )
        RETURNING
            id,
            environment_id,
            name,
            description,
            is_default,
            is_active,
            created_at,
            updated_at,
            deleted_at
        """,
        (
            brand_id,
            now,
            environment_id,
            brand_id,
        ),
    ).fetchall()

    columns = (
        "id",
        "environment_id",
        "name",
        "description",
        "is_default",
        "is_active",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    for row in result:
        if row[0] == brand_id:
            return dict(zip(columns, row))

    return None