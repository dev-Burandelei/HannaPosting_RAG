
import json
import pytest

from app.services.brand_profiles import (
    build_empty_profile_snapshot,
    create_initial_brand_profile,
    get_brand_profile,
    _build_profile_snapshot,
    _create_profile_version,
    update_general_profile,
    update_platform_profile,
    get_brand_profile_version,
    restore_brand_profile_version,
)




def create_environment(database, environment_id="env-001"):
    database.execute(
        """
        INSERT INTO environments (
            id,
            name,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            environment_id,
            "Ambiente de teste",
            "active",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )


def create_brand(database, brand_id="brand-001"):
    database.execute(
        """
        INSERT INTO brands (
            id,
            environment_id,
            name,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            brand_id,
            "env-001",
            "Marca de teste",
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )


def test_build_empty_profile_snapshot():
    snapshot = build_empty_profile_snapshot()

    assert snapshot == {
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


def test_create_initial_brand_profile(database):
    create_environment(database)
    create_brand(database)

    profile_id = create_initial_brand_profile(
        database,
        "brand-001",
    )

    profile = database.execute(
        """
        SELECT id, brand_id
        FROM brand_profiles
        WHERE id = ?
        """,
        (profile_id,),
    ).fetchone()

    assert profile == (profile_id, "brand-001")


def test_create_initial_brand_profile_creates_version_one(database):
    create_environment(database)
    create_brand(database)

    profile_id = create_initial_brand_profile(
        database,
        "brand-001",
    )

    version = database.execute(
        """
        SELECT
            brand_id,
            brand_profile_id,
            version_number,
            profile_data_json,
            created_by
        FROM brand_profile_versions
        WHERE brand_profile_id = ?
        """,
        (profile_id,),
    ).fetchone()

    assert version is not None
    assert version[0] == "brand-001"
    assert version[1] == profile_id
    assert version[2] == 1
    assert json.loads(version[3]) == build_empty_profile_snapshot()
    assert version[4] is None


def test_create_initial_brand_profile_generates_unique_ids(database):
    create_environment(database)
    create_brand(database, "brand-001")
    create_brand(database, "brand-002")

    first_profile = create_initial_brand_profile(
        database,
        "brand-001",
    )

    second_profile = create_initial_brand_profile(
        database,
        "brand-002",
    )

    assert first_profile != second_profile



def test_get_brand_profile_returns_empty_profile(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    from app.services.brand_profiles import get_brand_profile

    result = get_brand_profile(database, "brand-001")

    assert result is not None
    assert result["brand_id"] == "brand-001"

    assert all(
        value is None
        for value in result["general"].values()
    )

    assert result["platforms"] == {
        "instagram": None,
        "linkedin": None,
    }

    assert result["current_version"]["version_number"] == 1
    assert result["current_version"]["profile_data"] == (
        build_empty_profile_snapshot()
    )


def test_get_brand_profile_returns_none_when_profile_does_not_exist(database):
    result = get_brand_profile(database, "brand-inexistente")

    assert result is None


def test_get_brand_profile_decodes_general_json_fields(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    database.execute(
        """
        UPDATE brand_profiles
        SET
            emoji_policy = ?,
            hashtag_policy = ?,
            required_expressions = ?,
            forbidden_expressions = ?
        WHERE brand_id = ?
        """,
        (
            '{"allowed":true,"maximum":3}',
            '{"maximum":5,"position":"end"}',
            '["inovação","tecnologia"]',
            '["garantido","milagre"]',
            "brand-001",
        ),
    )

    result = get_brand_profile(database, "brand-001")

    assert result["general"]["emoji_policy"] == {
        "allowed": True,
        "maximum": 3,
    }

    assert result["general"]["hashtag_policy"] == {
        "maximum": 5,
        "position": "end",
    }

    assert result["general"]["required_expressions"] == [
        "inovação",
        "tecnologia",
    ]

    assert result["general"]["forbidden_expressions"] == [
        "garantido",
        "milagre",
    ]


def test_get_brand_profile_returns_latest_version(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    profile_id = database.execute(
        """
        SELECT id
        FROM brand_profiles
        WHERE brand_id = ?
        """,
        ("brand-001",),
    ).fetchone()[0]

    snapshot = build_empty_profile_snapshot()
    snapshot["general"]["voice_tone"] = "Profissional e próximo"

    database.execute(
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
            "version-002",
            "brand-001",
            profile_id,
            2,
            json.dumps(snapshot, ensure_ascii=False),
            "2026-11-25T12:00:00+00:00",
            None,
        ),
    )

    result = get_brand_profile(database, "brand-001")

    assert result["current_version"]["id"] == "version-002"
    assert result["current_version"]["version_number"] == 2
    assert result["current_version"]["profile_data"] == snapshot



def test_get_brand_profile_returns_instagram_configuration(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    database.execute(
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
            "platform-001",
            "brand-001",
            "instagram",
            "Linguagem descontraída e visual",
            '["carrossel","reels"]',
            "2026-11-25T12:00:00+00:00",
            "2026-11-25T12:00:00+00:00",
        ),
    )

    result = get_brand_profile(database, "brand-001")

    instagram = result["platforms"]["instagram"]

    assert instagram is not None
    assert instagram["id"] == "platform-001"
    assert instagram["platform_guidelines"] == (
        "Linguagem descontraída e visual"
    )
    assert instagram["preferred_formats"] == ["carrossel", "reels"]

    assert result["platforms"]["linkedin"] is None


def test_get_brand_profile_returns_both_platforms(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    for platform, profile_id, guidelines in [
        ("instagram", "platform-001", "Linguagem descontraída"),
        ("linkedin", "platform-002", "Linguagem profissional"),
    ]:
        database.execute(
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
                profile_id,
                "brand-001",
                platform,
                guidelines,
                '["texto"]',
                "2026-11-25T12:00:00+00:00",
                "2026-11-25T12:00:00+00:00",
            ),
        )

    result = get_brand_profile(database, "brand-001")

    assert result["platforms"]["instagram"]["platform_guidelines"] == (
        "Linguagem descontraída"
    )

    assert result["platforms"]["linkedin"]["platform_guidelines"] == (
        "Linguagem profissional"
    )

    assert result["platforms"]["instagram"]["preferred_formats"] == ["texto"]
    assert result["platforms"]["linkedin"]["preferred_formats"] == ["texto"]



def test_build_profile_snapshot_excludes_record_metadata(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    profile = get_brand_profile(database, "brand-001")

    snapshot = _build_profile_snapshot(profile)

    assert snapshot == build_empty_profile_snapshot()


def test_build_profile_snapshot_includes_platform_configurations(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    database.execute(
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
            "platform-001",
            "brand-001",
            "instagram",
            "Comunicação descontraída",
            '["carrossel","reels"]',
            "2026-11-25T12:00:00+00:00",
            "2026-11-25T12:00:00+00:00",
        ),
    )

    profile = get_brand_profile(database, "brand-001")
    snapshot = _build_profile_snapshot(profile)

    assert snapshot["platforms"]["instagram"] == {
        "platform_guidelines": "Comunicação descontraída",
        "preferred_formats": ["carrossel", "reels"],
    }

    assert snapshot["platforms"]["linkedin"] is None


def test_create_profile_version_increments_version_number(database):
    create_environment(database)
    create_brand(database)
    profile_id = create_initial_brand_profile(database, "brand-001")

    snapshot = build_empty_profile_snapshot()
    snapshot["general"]["voice_tone"] = "Profissional"

    version = _create_profile_version(
        database,
        "brand-001",
        profile_id,
        snapshot,
    )

    assert version["version_number"] == 2
    assert version["profile_data"] == snapshot

    stored_versions = database.execute(
        """
        SELECT version_number
        FROM brand_profile_versions
        WHERE brand_profile_id = ?
        ORDER BY version_number
        """,
        (profile_id,),
    ).fetchall()

    assert stored_versions == [(1,), (2,)]



def test_update_general_profile_changes_one_field(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    result = update_general_profile(
        database,
        "brand-001",
        voice_tone="Profissional e acessível",
    )

    assert result["general"]["voice_tone"] == "Profissional e acessível"
    assert result["general"]["target_audience"] is None
    assert result["current_version"]["version_number"] == 2


def test_update_general_profile_preserves_omitted_fields(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_general_profile(
        database,
        "brand-001",
        voice_tone="Profissional",
        target_audience="Pequenas empresas",
    )

    result = update_general_profile(
        database,
        "brand-001",
        voice_tone="Descontraído",
    )

    assert result["general"]["voice_tone"] == "Descontraído"
    assert result["general"]["target_audience"] == "Pequenas empresas"


def test_update_general_profile_clears_field_with_none(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_general_profile(
        database,
        "brand-001",
        voice_tone="Profissional",
    )

    result = update_general_profile(
        database,
        "brand-001",
        voice_tone=None,
    )

    assert result["general"]["voice_tone"] is None
    assert result["current_version"]["version_number"] == 3


def test_update_general_profile_does_not_create_version_without_changes(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_general_profile(
        database,
        "brand-001",
        voice_tone="Profissional",
    )

    result = update_general_profile(
        database,
        "brand-001",
        voice_tone="Profissional",
    )

    assert result["current_version"]["version_number"] == 2

    versions = database.execute(
        """
        SELECT version_number
        FROM brand_profile_versions
        WHERE brand_id = ?
        ORDER BY version_number
        """,
        ("brand-001",),
    ).fetchall()

    assert [row[0] for row in versions] == [1, 2]


def test_update_general_profile_updates_json_fields(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    result = update_general_profile(
        database,
        "brand-001",
        emoji_policy={
            "allowed": True,
            "maximum": 3,
        },
        required_expressions=["Inovação", "Tecnologia"],
    )

    assert result["general"]["emoji_policy"] == {
        "allowed": True,
        "maximum": 3,
    }
    assert result["general"]["required_expressions"] == [
        "Inovação",
        "Tecnologia",
    ]


def test_update_general_profile_rejects_invalid_json_field(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    with pytest.raises(ValueError):
        update_general_profile(
            database,
            "brand-001",
            emoji_policy="permitidos",
        )


def test_update_general_profile_returns_none_for_missing_profile(database):
    create_environment(database)
    create_brand(database)

    result = update_general_profile(
        database,
        "brand-001",
        voice_tone="Profissional",
    )

    assert result is None


def test_update_platform_profile_creates_instagram_configuration(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    result = update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Priorizar conteúdos visuais.",
        preferred_formats=["reels", "carrossel"],
    )

    assert result["platforms"]["instagram"]["platform_guidelines"] == (
        "Priorizar conteúdos visuais."
    )
    assert result["platforms"]["instagram"]["preferred_formats"] == [
        "reels",
        "carrossel",
    ]
    assert result["platforms"]["linkedin"] is None
    assert result["current_version"]["version_number"] == 2


def test_update_platform_profile_creates_linkedin_configuration(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    result = update_platform_profile(
        database,
        "brand-001",
        "linkedin",
        platform_guidelines="Priorizar conteúdo profissional.",
    )

    assert result["platforms"]["linkedin"]["platform_guidelines"] == (
        "Priorizar conteúdo profissional."
    )
    assert result["platforms"]["instagram"] is None
    assert result["current_version"]["version_number"] == 2


def test_update_platform_profile_preserves_omitted_fields(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Instruções iniciais.",
        preferred_formats=["reels", "stories"],
    )

    result = update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Novas instruções.",
    )

    assert result["platforms"]["instagram"]["platform_guidelines"] == (
        "Novas instruções."
    )
    assert result["platforms"]["instagram"]["preferred_formats"] == [
        "reels",
        "stories",
    ]
    assert result["current_version"]["version_number"] == 3


def test_update_platform_profile_clears_field_with_none(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Instruções iniciais.",
    )

    result = update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines=None,
    )

    assert result["platforms"]["instagram"]["platform_guidelines"] is None
    assert result["current_version"]["version_number"] == 3


def test_update_platform_profile_does_not_create_duplicate_version(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Instruções iniciais.",
    )

    result = update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Instruções iniciais.",
    )

    assert result["current_version"]["version_number"] == 2


def test_update_platform_profile_versions_are_unified(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_general_profile(
        database,
        "brand-001",
        voice_tone="Profissional",
    )

    update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Conteúdo visual.",
    )

    result = update_platform_profile(
        database,
        "brand-001",
        "linkedin",
        platform_guidelines="Conteúdo profissional.",
    )

    assert result["current_version"]["version_number"] == 4

    snapshot = result["current_version"]["profile_data"]

    assert snapshot["general"]["voice_tone"] == "Profissional"
    assert snapshot["platforms"]["instagram"]["platform_guidelines"] == (
        "Conteúdo visual."
    )
    assert snapshot["platforms"]["linkedin"]["platform_guidelines"] == (
        "Conteúdo profissional."
    )


def test_update_platform_profile_rejects_invalid_platform(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    with pytest.raises(ValueError):
        update_platform_profile(
            database,
            "brand-001",
            "facebook",
            platform_guidelines="Instruções.",
        )


def test_update_platform_profile_rejects_invalid_preferred_formats(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    with pytest.raises(ValueError):
        update_platform_profile(
            database,
            "brand-001",
            "instagram",
            preferred_formats="reels",
        )


def test_update_platform_profile_returns_none_for_missing_profile(database):
    create_environment(database)
    create_brand(database)

    result = update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Instruções.",
    )

    assert result is None


def test_get_brand_profile_version_by_number(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    profile = get_brand_profile(database, "brand-001")

    version = get_brand_profile_version(
        database,
        "brand-001",
        version_number=1,
    )

    assert version is not None
    assert version["id"] == profile["current_version"]["id"]
    assert version["brand_id"] == "brand-001"
    assert version["version_number"] == 1
    assert version["profile_data"] == build_empty_profile_snapshot()


def test_get_brand_profile_version_by_id(database):
    create_environment(database)
    create_brand(database)

    create_initial_brand_profile(database, "brand-001")

    current = get_brand_profile(database, "brand-001")["current_version"]

    version = get_brand_profile_version(
        database,
        "brand-001",
        version_id=current["id"],
    )

    assert version is not None
    assert version["id"] == current["id"]
    assert version["version_number"] == 1


def test_get_brand_profile_version_returns_none_for_missing_version(database):
    create_environment(database)
    create_brand(database)

    version = get_brand_profile_version(
        database,
        "brand-001",
        version_number=99,
    )

    assert version is None


def test_get_brand_profile_version_does_not_return_another_brands_version(
    database,
):
    create_environment(database)
    create_brand(database, "brand-001")
    create_brand(database, "brand-002")

    create_initial_brand_profile(database, "brand-001")
    create_initial_brand_profile(database, "brand-002")

    version_id = get_brand_profile(
        database,
        "brand-001",
    )["current_version"]["id"]

    version = get_brand_profile_version(
        database,
        "brand-002",
        version_id=version_id,
    )

    assert version is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"version_number": 1, "version_id": "some-id"},
    ],
)
def test_get_brand_profile_version_requires_exactly_one_selector(
    database,
    kwargs,
):
    with pytest.raises(ValueError):
        get_brand_profile_version(
            database,
            "brand-001",
            **kwargs,
        )


def test_get_brand_profile_version_rejects_non_positive_number(database):
    with pytest.raises(ValueError):
        get_brand_profile_version(
            database,
            "brand-001",
            version_number=0,
        )


def test_restore_brand_profile_version_by_number(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_general_profile(
        database,
        "brand-001",
        voice_tone="Profissional",
    )

    update_general_profile(
        database,
        "brand-001",
        voice_tone="Descontraído",
    )

    result = restore_brand_profile_version(
        database,
        "brand-001",
        version_number=2,
    )

    assert result["general"]["voice_tone"] == "Profissional"
    assert result["current_version"]["version_number"] == 4
    assert result["current_version"]["profile_data"]["general"][
        "voice_tone"
    ] == "Profissional"


def test_restore_brand_profile_version_by_id(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_general_profile(
        database,
        "brand-001",
        voice_tone="Formal",
    )

    historical = get_brand_profile_version(
        database,
        "brand-001",
        version_number=2,
    )

    result = restore_brand_profile_version(
        database,
        "brand-001",
        version_id=historical["id"],
    )

    assert result["general"]["voice_tone"] == "Formal"
    assert result["current_version"]["version_number"] == 3


def test_restore_brand_profile_version_preserves_history(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_general_profile(
        database,
        "brand-001",
        voice_tone="Formal",
    )

    historical_before = get_brand_profile_version(
        database,
        "brand-001",
        version_number=2,
    )

    restore_brand_profile_version(
        database,
        "brand-001",
        version_number=1,
    )

    historical_after = get_brand_profile_version(
        database,
        "brand-001",
        version_number=2,
    )

    assert historical_after == historical_before

    current = get_brand_profile(database, "brand-001")

    assert current["current_version"]["version_number"] == 3
    assert current["general"]["voice_tone"] is None


def test_restore_brand_profile_version_restores_platforms(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Conteúdo visual.",
    )

    update_platform_profile(
        database,
        "brand-001",
        "linkedin",
        platform_guidelines="Conteúdo profissional.",
    )

    result = restore_brand_profile_version(
        database,
        "brand-001",
        version_number=2,
    )

    assert result["platforms"]["instagram"] is not None
    assert result["platforms"]["instagram"]["platform_guidelines"] == (
        "Conteúdo visual."
    )
    assert result["platforms"]["linkedin"] is None
    assert result["current_version"]["version_number"] == 4


def test_restore_brand_profile_version_creates_missing_platform(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Conteúdo visual.",
    )

    restore_brand_profile_version(
        database,
        "brand-001",
        version_number=1,
    )

    restored = restore_brand_profile_version(
        database,
        "brand-001",
        version_number=2,
    )

    assert restored["platforms"]["instagram"] is not None
    assert restored["platforms"]["instagram"]["platform_guidelines"] == (
        "Conteúdo visual."
    )
    assert restored["current_version"]["version_number"] == 4


def test_restore_brand_profile_version_returns_none_for_missing_version(
    database,
):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    result = restore_brand_profile_version(
        database,
        "brand-001",
        version_number=99,
    )

    assert result is None



@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"version_number": 1, "version_id": "some-id"},
    ],
)
def test_restore_brand_profile_version_requires_exactly_one_selector(
    database,
    kwargs,
):
    with pytest.raises(ValueError):
        restore_brand_profile_version(
            database,
            "brand-001",
            **kwargs,
        )


def test_restore_brand_profile_version_rejects_non_positive_number(
    database,
):
    with pytest.raises(ValueError):
        restore_brand_profile_version(
            database,
            "brand-001",
            version_number=0,
        )



def test_restore_brand_profile_version_updates_existing_platform(database):
    create_environment(database)
    create_brand(database)
    create_initial_brand_profile(database, "brand-001")

    update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Instruções A.",
    )

    update_platform_profile(
        database,
        "brand-001",
        "instagram",
        platform_guidelines="Instruções B.",
    )

    result = restore_brand_profile_version(
        database,
        "brand-001",
        version_number=2,
    )

    assert result["platforms"]["instagram"]["platform_guidelines"] == (
        "Instruções A."
    )
    assert result["current_version"]["version_number"] == 4
