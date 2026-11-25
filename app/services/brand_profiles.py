
import json
import sqlite3

from datetime import datetime, timezone
from uuid import uuid4

class _Unset:
    """Representa um campo que não foi informado."""


_UNSET = _Unset()

def build_empty_profile_snapshot() -> dict:
    """
    Constrói o snapshot inicial de um perfil de marca.

    Representa o perfil geral vazio e a ausência
    de configurações específicas por plataforma.
    """

    return {
        "general": {
            "target_audience": None,
            "voice_tone": None,
            "formality": None,
            "preferred_length": None,
            "emoji_policy": None,
            "hashtag_policy": None,
            "cta_guidelines": None,
            "required_expressions": None,
            "forbidden_expressions": None,
            "general_guidelines": None,
        },
        "platforms": {
            "instagram": None,
            "linkedin": None,
        },
    }


def create_initial_brand_profile(
    connection: sqlite3.Connection,
    brand_id: str,
) -> str:
    """
    Cria o perfil geral vazio de uma marca e sua versão inicial.

    A versão inicial recebe o número 1 e contém o snapshot
    completo do perfil, incluindo as plataformas.

    Retorna o ID do perfil criado.

    Não executa commit, rollback ou close.
    """

    profile_id = str(uuid4())
    version_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    snapshot = build_empty_profile_snapshot()

    snapshot_json = json.dumps(
        snapshot,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    connection.execute(
        """
        INSERT INTO brand_profiles (
            id,
            brand_id,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            profile_id,
            brand_id,
            now,
            now,
        ),
    )

    connection.execute(
        """
        INSERT INTO brand_profile_versions (
            id,
            brand_id,
            brand_profile_id,
            version_number,
            profile_data_json,
            created_at,
            created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            brand_id,
            profile_id,
            1,
            snapshot_json,
            now,
            None,
        ),
    )

    return profile_id



def _decode_json_field(value):
    """Converte um campo JSON armazenado no banco para Python."""

    if value is None:
        return None

    return json.loads(value)


def get_brand_profile(
    connection: sqlite3.Connection,
    brand_id: str,
) -> dict | None:
    """
    Consulta o perfil atual de uma marca e sua versão mais recente.

    Retorna None se a marca não possuir perfil geral.

    Não altera o banco nem controla transações.
    """

    profile_row = connection.execute(
        """
        SELECT
            id,
            brand_id,
            target_audience,
            voice_tone,
            formality,
            preferred_length,
            emoji_policy,
            hashtag_policy,
            cta_guidelines,
            required_expressions,
            forbidden_expressions,
            general_guidelines,
            created_at,
            updated_at
        FROM brand_profiles
        WHERE brand_id = ?
        """,
        (brand_id,),
    ).fetchone()

    if profile_row is None:
        return None

    general = {
        "target_audience": profile_row[2],
        "voice_tone": profile_row[3],
        "formality": profile_row[4],
        "preferred_length": profile_row[5],
        "emoji_policy": _decode_json_field(profile_row[6]),
        "hashtag_policy": _decode_json_field(profile_row[7]),
        "cta_guidelines": profile_row[8],
        "required_expressions": _decode_json_field(profile_row[9]),
        "forbidden_expressions": _decode_json_field(profile_row[10]),
        "general_guidelines": profile_row[11],
    }

    platform_rows = connection.execute(
        """
        SELECT
            id,
            platform,
            platform_guidelines,
            preferred_formats,
            created_at,
            updated_at
        FROM brand_platform_profiles
        WHERE brand_id = ?
        """,
        (brand_id,),
    ).fetchall()

    platforms = {
        "instagram": None,
        "linkedin": None,
    }

    for row in platform_rows:
        platforms[row[1]] = {
            "id": row[0],
            "platform_guidelines": row[2],
            "preferred_formats": _decode_json_field(row[3]),
            "created_at": row[4],
            "updated_at": row[5],
        }

    version_row = connection.execute(
        """
        SELECT
            id,
            version_number,
            profile_data_json,
            created_at,
            created_by
        FROM brand_profile_versions
        WHERE brand_id = ?
          AND brand_profile_id = ?
        ORDER BY version_number DESC
        LIMIT 1
        """,
        (brand_id, profile_row[0]),
    ).fetchone()

    current_version = None

    if version_row is not None:
        current_version = {
            "id": version_row[0],
            "version_number": version_row[1],
            "profile_data": json.loads(version_row[2]),
            "created_at": version_row[3],
            "created_by": version_row[4],
        }

    return {
        "brand_id": brand_id,
        "general": general,
        "platforms": platforms,
        "current_version": current_version,
    }
def _build_profile_snapshot(profile: dict) -> dict:
    """
    Constrói um snapshot completo usando os dados atuais do perfil.

    Exclui identificadores e timestamps específicos dos registros.
    """

    platforms = {}

    for platform in ("instagram", "linkedin"):
        platform_data = profile["platforms"][platform]

        if platform_data is None:
            platforms[platform] = None
        else:
            platforms[platform] = {
                "platform_guidelines": platform_data[
                    "platform_guidelines"
                ],
                "preferred_formats": platform_data[
                    "preferred_formats"
                ],
            }

    return {
        "general": profile["general"].copy(),
        "platforms": platforms,
    }

def _create_profile_version(
    connection: sqlite3.Connection,
    brand_id: str,
    brand_profile_id: str,
    snapshot: dict,
    created_by: str | None = None,
) -> dict:
    """
    Registra uma nova versão completa do perfil.

    O número é calculado com base na maior versão existente.

    Não executa commit, rollback ou close.
    """

    version_number = connection.execute(
        """
        SELECT COALESCE(MAX(version_number), 0) + 1
        FROM brand_profile_versions
        WHERE brand_profile_id = ?
        """,
        (brand_profile_id,),
    ).fetchone()[0]

    version_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    snapshot_json = json.dumps(
        snapshot,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    connection.execute(
        """
        INSERT INTO brand_profile_versions (
            id,
            brand_id,
            brand_profile_id,
            version_number,
            profile_data_json,
            created_at,
            created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            version_id,
            brand_id,
            brand_profile_id,
            version_number,
            snapshot_json,
            now,
            created_by,
        ),
    )

    return {
        "id": version_id,
        "version_number": version_number,
        "profile_data": snapshot,
        "created_at": now,
        "created_by": created_by,
    }


def update_general_profile(
    connection: sqlite3.Connection,
    brand_id: str,
    target_audience=_UNSET,
    voice_tone=_UNSET,
    formality=_UNSET,
    preferred_length=_UNSET,
    emoji_policy=_UNSET,
    hashtag_policy=_UNSET,
    cta_guidelines=_UNSET,
    required_expressions=_UNSET,
    forbidden_expressions=_UNSET,
    general_guidelines=_UNSET,
    created_by: str | None = None,
) -> dict | None:
    """
    Atualiza parcialmente o perfil geral de uma marca.

    Campos omitidos são preservados.
    Campos enviados como None são limpos.
    Uma nova versão é criada somente quando há mudança efetiva.

    Não executa commit, rollback ou close.
    """

    profile = get_brand_profile(connection, brand_id)

    if profile is None:
        return None

    brand_profile_id = connection.execute(
        """
        SELECT id
        FROM brand_profiles
        WHERE brand_id = ?
        """,
        (brand_id,),
    ).fetchone()[0]

    updates = {
        "target_audience": target_audience,
        "voice_tone": voice_tone,
        "formality": formality,
        "preferred_length": preferred_length,
        "emoji_policy": emoji_policy,
        "hashtag_policy": hashtag_policy,
        "cta_guidelines": cta_guidelines,
        "required_expressions": required_expressions,
        "forbidden_expressions": forbidden_expressions,
        "general_guidelines": general_guidelines,
    }

    json_fields = {
        "emoji_policy",
        "hashtag_policy",
        "required_expressions",
        "forbidden_expressions",
    }

    changed_fields = {}

    for field, new_value in updates.items():
        if new_value is _UNSET:
            continue

        if field in json_fields:
            if new_value is not None:
                if not isinstance(new_value, (dict, list)):
                    raise ValueError(
                        f"O campo '{field}' deve receber um dicionário, "
                        "uma lista ou None."
                    )

        current_value = profile["general"][field]

        if current_value != new_value:
            changed_fields[field] = new_value

    if not changed_fields:
        return profile

    sql_values = {}

    for field, value in changed_fields.items():
        if field in json_fields and value is not None:
            value = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        sql_values[field] = value

    now = datetime.now(timezone.utc).isoformat()

    assignments = ", ".join(
        f"{field} = ?" for field in sql_values
    )

    parameters = list(sql_values.values())
    parameters.extend([now, brand_id])

    connection.execute(
        f"""
        UPDATE brand_profiles
        SET {assignments},
            updated_at = ?
        WHERE brand_id = ?
        """,
        parameters,
    )

    updated_profile = get_brand_profile(connection, brand_id)

    snapshot = _build_profile_snapshot(updated_profile)

    _create_profile_version(
        connection=connection,
        brand_id=brand_id,
        brand_profile_id=brand_profile_id,
        snapshot=snapshot,
        created_by=created_by,
    )

    return get_brand_profile(connection, brand_id)



def update_platform_profile(
    connection: sqlite3.Connection,
    brand_id: str,
    platform: str,
    platform_guidelines=_UNSET,
    preferred_formats=_UNSET,
    created_by: str | None = None,
) -> dict | None:
    """
    Atualiza parcialmente as configurações de uma plataforma.

    Cria o registro da plataforma quando ele ainda não existe.
    Campos omitidos são preservados.
    Campos enviados como None são limpos.

    Uma nova versão completa é criada somente quando há
    mudança efetiva no perfil.

    Não executa commit, rollback ou close.
    """

    if platform not in ("instagram", "linkedin"):
        raise ValueError("Plataforma inválida.")

    profile = get_brand_profile(connection, brand_id)

    if profile is None:
        return None

    platform_data = profile["platforms"][platform]

    if (
        platform_guidelines is _UNSET
        and preferred_formats is _UNSET
    ):
        return profile

    if preferred_formats is not _UNSET:
        if preferred_formats is not None and not isinstance(
            preferred_formats, list
        ):
            raise ValueError(
                "preferred_formats deve ser uma lista ou None."
            )

    updates = {
        "platform_guidelines": platform_guidelines,
        "preferred_formats": preferred_formats,
    }

    changed_fields = {}

    for field, new_value in updates.items():
        if new_value is _UNSET:
            continue

        current_value = (
            None if platform_data is None
            else platform_data[field]
        )

        if current_value != new_value:
            changed_fields[field] = new_value

    if platform_data is not None and not changed_fields:
        return profile

    now = datetime.now(timezone.utc).isoformat()

    brand_profile_id = connection.execute(
        """
        SELECT id
        FROM brand_profiles
        WHERE brand_id = ?
        """,
        (brand_id,),
    ).fetchone()[0]

    if platform_data is None:
        values = {
            "platform_guidelines": None,
            "preferred_formats": None,
        }
        values.update(changed_fields)

        preferred_formats_json = values["preferred_formats"]

        if preferred_formats_json is not None:
            preferred_formats_json = json.dumps(
                preferred_formats_json,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        connection.execute(
            """
            INSERT INTO brand_platform_profiles (
                id,
                brand_id,
                platform,
                platform_guidelines,
                preferred_formats,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                brand_id,
                platform,
                values["platform_guidelines"],
                preferred_formats_json,
                now,
                now,
            ),
        )

    else:
        sql_values = {}

        for field, value in changed_fields.items():
            if field == "preferred_formats" and value is not None:
                value = json.dumps(
                    value,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

            sql_values[field] = value

        assignments = ", ".join(
            f"{field} = ?" for field in sql_values
        )

        parameters = list(sql_values.values())
        parameters.extend([now, brand_id, platform])

        connection.execute(
            f"""
            UPDATE brand_platform_profiles
            SET {assignments},
                updated_at = ?
            WHERE brand_id = ?
              AND platform = ?
            """,
            parameters,
        )

    updated_profile = get_brand_profile(connection, brand_id)

    snapshot = _build_profile_snapshot(updated_profile)

    _create_profile_version(
        connection=connection,
        brand_id=brand_id,
        brand_profile_id=brand_profile_id,
        snapshot=snapshot,
        created_by=created_by,
    )

    return get_brand_profile(connection, brand_id)


def get_brand_profile_version(
    connection: sqlite3.Connection,
    brand_id: str,
    version_number: int | None = None,
    version_id: str | None = None,
) -> dict | None:
    """Retorna uma versão específica do perfil de uma marca."""

    if (version_number is None) == (version_id is None):
        raise ValueError(
            "Informe exatamente um dos parâmetros: "
            "version_number ou version_id."
        )

    if version_number is not None:
        if version_number <= 0:
            raise ValueError("version_number deve ser maior que zero.")

        row = connection.execute(
            """
            SELECT
                bpv.id,
                bpv.brand_id,
                bpv.brand_profile_id,
                bpv.version_number,
                bpv.profile_data_json,
                bpv.created_at,
                bpv.created_by
            FROM brand_profile_versions AS bpv
            INNER JOIN brand_profiles AS bp
                ON bp.id = bpv.brand_profile_id
            WHERE bpv.brand_id = ?
              AND bpv.version_number = ?
            """,
            (brand_id, version_number),
        ).fetchone()

    else:
        row = connection.execute(
            """
            SELECT
                bpv.id,
                bpv.brand_id,
                bpv.brand_profile_id,
                bpv.version_number,
                bpv.profile_data_json,
                bpv.created_at,
                bpv.created_by
            FROM brand_profile_versions AS bpv
            INNER JOIN brand_profiles AS bp
                ON bp.id = bpv.brand_profile_id
            WHERE bpv.brand_id = ?
              AND bpv.id = ?
            """,
            (brand_id, version_id),
        ).fetchone()

    if row is None:
        return None

    return {
    "id": row[0],
    "brand_id": row[1],
    "brand_profile_id": row[2],
    "version_number": row[3],
    "profile_data": json.loads(row[4]),
    "created_at": row[5],
    "created_by": row[6],
}


def restore_brand_profile_version(
    connection: sqlite3.Connection,
    brand_id: str,
    version_number: int | None = None,
    version_id: str | None = None,
    created_by: str | None = None,
) -> dict | None:
    """
    Recupera uma versão anterior do perfil de uma marca.

    A versão recuperada não é modificada. A recuperação gera
    uma nova versão com o snapshot restaurado.

    Não executa commit, rollback ou close.
    """

    if (version_number is None) == (version_id is None):
        raise ValueError(
            "Informe exatamente um dos parâmetros: "
            "version_number ou version_id."
        )

    if version_number is not None and version_number <= 0:
        raise ValueError("version_number deve ser maior que zero.")

    profile = get_brand_profile(connection, brand_id)


    if profile is None:
        return None

    historical_version = get_brand_profile_version(
        connection=connection,
        brand_id=brand_id,
        version_number=version_number,
        version_id=version_id,
    )

    if historical_version is None:
        return None

    snapshot = historical_version["profile_data"]
    general = snapshot["general"]
    platforms = snapshot["platforms"]

    now = datetime.now(timezone.utc).isoformat()

    brand_profile_id = connection.execute(
        """
        SELECT id
        FROM brand_profiles
        WHERE brand_id = ?
        """,
        (brand_id,),
    ).fetchone()[0]

    json_fields = {
        "emoji_policy",
        "hashtag_policy",
        "required_expressions",
        "forbidden_expressions",
    }

    general_fields = (
        "target_audience",
        "voice_tone",
        "formality",
        "preferred_length",
        "emoji_policy",
        "hashtag_policy",
        "cta_guidelines",
        "required_expressions",
        "forbidden_expressions",
        "general_guidelines",
    )

    general_values = []

    for field in general_fields:
        value = general[field]

        if field in json_fields and value is not None:
            value = json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        general_values.append(value)

    general_values.extend([now, brand_id])

    connection.execute(
        """
        UPDATE brand_profiles
        SET
            target_audience = ?,
            voice_tone = ?,
            formality = ?,
            preferred_length = ?,
            emoji_policy = ?,
            hashtag_policy = ?,
            cta_guidelines = ?,
            required_expressions = ?,
            forbidden_expressions = ?,
            general_guidelines = ?,
            updated_at = ?
        WHERE brand_id = ?
        """,
        general_values,
    )

    for platform in ("instagram", "linkedin"):
        platform_data = platforms[platform]

        existing = connection.execute(
            """
            SELECT id
            FROM brand_platform_profiles
            WHERE brand_id = ?
              AND platform = ?
            """,
            (brand_id, platform),
        ).fetchone()

        if platform_data is None:
            connection.execute(
                """
                DELETE FROM brand_platform_profiles
                WHERE brand_id = ?
                  AND platform = ?
                """,
                (brand_id, platform),
            )
            continue

        preferred_formats = platform_data["preferred_formats"]

        if preferred_formats is not None:
            preferred_formats = json.dumps(
                preferred_formats,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        if existing is None:
            connection.execute(
                """
                INSERT INTO brand_platform_profiles (
                    id,
                    brand_id,
                    platform,
                    platform_guidelines,
                    preferred_formats,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    brand_id,
                    platform,
                    platform_data["platform_guidelines"],
                    preferred_formats,
                    now,
                    now,
                ),
            )

        else:
            connection.execute(
                """
                UPDATE brand_platform_profiles
                SET
                    platform_guidelines = ?,
                    preferred_formats = ?,
                    updated_at = ?
                WHERE brand_id = ?
                  AND platform = ?
                """,
                (
                    platform_data["platform_guidelines"],
                    preferred_formats,
                    now,
                    brand_id,
                    platform,
                ),
            )

    restored_profile = get_brand_profile(connection, brand_id)

    restored_snapshot = _build_profile_snapshot(restored_profile)

    _create_profile_version(
        connection=connection,
        brand_id=brand_id,
        brand_profile_id=brand_profile_id,
        snapshot=restored_snapshot,
        created_by=created_by,
    )

    return get_brand_profile(connection, brand_id)
