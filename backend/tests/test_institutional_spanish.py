"""Boundary tests for Spanish SQL mapping and institution-owned protocol."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from app.institutional.spanish_bindings import Cursor, layout, principal, translate
from tools import p2_es_migrations as migration


def test_closed_partition_keeps_academics_outside_mapping():
    value = layout()
    assert len(value["tables"]) == 108
    assert len(value["academic_tables"]) == 30
    assert len(value["new_tables"]) == 39
    assert not set(value["academic_tables"]) & set(value["tables"].values())


def test_parameters_and_literal_documents_are_never_translated():
    raw = Mock()
    cursor = Cursor(raw)
    secret = "crm.Contact ' DROP TABLE dbo.Academic"
    document = '{"source":"crm_access.Secret"}'
    cursor.execute(
        "SELECT * FROM [crm].[Contact] WHERE Name=? AND Notes=? AND Name<>'crm.Contact' -- crm.Contact\n",
        secret,
        document,
    )
    raw.execute.assert_called_once_with(
        "SELECT * FROM [dbo].[CRMContacto] WHERE Name=? AND Notes=? AND Name<>'crm.Contact' -- crm.Contact\n",
        secret,
        document,
    )
    assert cursor.execute("SELECT 1") is cursor


def test_object_probes_map_only_known_fixed_objects():
    assert (
        translate("SELECT OBJECT_ID(N'crm.Contact')", layout()["tables"])
        == "SELECT OBJECT_ID(N'dbo.CRMContacto')"
    )
    assert "'crm_channels.Account'" in translate(
        "CHECK (LegacyTable IN('crm_channels.Account'))", layout()["tables"]
    )


@pytest.mark.parametrize(
    "query",
    [
        "SELECT * FROM crm.ContactExtra",
        "SELECT * FROM crm_access.Unknown",
        "SELECT OBJECT_ID('crm.Unknown')",
    ],
)
def test_unknown_logical_references_fail_before_SQL(query):
    raw = Mock()
    with pytest.raises(ValueError):
        Cursor(raw).execute(query)
    raw.execute.assert_not_called()


@pytest.mark.parametrize(
    "database",
    [
        "HORARIOSSIIE",
        "DBSIIE",
        "CBN_P1ES_TRIAL_20261026_12345678",
        "CBN_C13_TRIAL_20261025_1f10a824",
        "CBN_P2ES_TRIAL_20261026_12345678;DROP",
    ],
)
def test_foreign_profile_target_rejected(database):
    with pytest.raises(ValueError):
        principal(database)


def test_caller_transaction_kept_intact():
    connection = Mock(autocommit=True)
    cursor = connection.cursor.return_value
    cursor.execute.return_value = cursor
    cursor.fetchval.return_value = 1
    with pytest.raises(ValueError, match="caller_transaction_not_owned"):
        migration.enter(connection, {})
    cursor.execute.assert_called_once_with("SELECT @@TRANCOUNT")
    connection.close.assert_not_called()


def test_seed_context_is_part_of_attempt_target_binding():
    first = {"institution": str(uuid4()), "bootstrap_sha256": "1" * 64}
    second = {**first, "bootstrap_sha256": "2" * 64}
    assert migration.target_hash({"database": "same"}, first) != migration.target_hash(
        {"database": "same"}, second
    )
    with pytest.raises(ValueError):
        migration.seed_binding({**first, "role": "owner"})


def test_opaque_password_and_document_never_enter_audit_text():
    from app.institutional.db import audit

    cursor = Mock()
    settings = SimpleNamespace(ticket={"context": [[1, str(uuid4()), "version"]]})
    with pytest.raises(ValueError, match="invalid_audit_metadata"):
        audit(cursor, settings, None, "denied", password="private")
    cursor.execute.assert_not_called()


def test_forged_WAL_terminal_cannot_complete_attempt():
    first = {
        "event": "STARTED",
        "unit": migration.UNITS[0],
        "attempt": str(uuid4()),
        "version": migration.VERSION,
        "target": "1" * 64,
        "manifest": "2" * 64,
        "unit_sha256": "3" * 64,
        "before": "4" * 64,
    }
    with pytest.raises(ValueError, match="cross_attempt_binding"):
        migration.wal_state(
            [
                first,
                {**first, "event": "COMMITTED", "before": "5" * 64, "after": "6" * 64},
            ]
        )


def test_WAL_cannot_mix_release_or_database():
    first = {
        "event": "STARTED",
        "unit": migration.UNITS[0],
        "attempt": str(uuid4()),
        "version": migration.VERSION,
        "target": "1" * 64,
        "manifest": "2" * 64,
        "unit_sha256": "3" * 64,
        "before": "4" * 64,
    }
    with pytest.raises(ValueError, match="file_binding"):
        migration.wal_state(
            [first, {**first, "attempt": str(uuid4()), "manifest": "f" * 64}]
        )


@pytest.mark.parametrize(
    "provider", ["gemini", "openai", "anthropic", "hermes", "openrouter", "kimi"]
)
def test_all_reference_vision_choices_and_independent_style(provider):
    from app.institutional.models import AI

    value = AI(
        vision_analysis_provider=provider,
        human_reply_style_enabled=False,
        brief_responses=True,
        model_failover_enabled=False,
        fallback_enabled=True,
    )
    assert value.vision_analysis_provider == provider
    assert not value.human_reply_style_enabled and value.brief_responses
    assert not value.model_failover_enabled and value.fallback_enabled


def test_reference_delay_limits_zero_chunk_and_effective_caps():
    from app.institutional.model_settings import chunks, effective_limits
    from app.institutional.models import AI

    value = AI(
        wait_seconds=3600,
        typing_ms=240000,
        fragment_delay_ms=240000,
        reply_min_chunk_delay_ms=240000,
        chars_per_message=0,
        output_tokens=3000,
        max_tokens=8000,
    ).model_dump(mode="json")
    assert chunks("a long response", value) == ["a long response"]
    assert effective_limits(value)["max_tokens"] == 2000
    assert not effective_limits(value)["split_enabled"]
    assert (
        effective_limits({**value, "human_reply_style_enabled": False})["max_tokens"]
        == 8000
    )


def test_model_selection_is_single_authority_and_supports_reference_ID_length():
    from app.institutional.model_settings import project, validate_projection
    from app.institutional.models import AI
    from fastapi import HTTPException

    models = {
        "selections": [
            {
                "provider": "openrouter",
                "category": "text",
                "selected_model": "a" * 240,
                "display_name": "Selected model",
                "voice_id": "",
            }
        ]
    }
    configured = project(AI(provider="openrouter").model_dump(mode="json"), models)
    assert (
        configured["model"] == configured["provider_models"]["openrouter"] == "a" * 240
    )
    assert validate_projection(configured, models) == configured
    with pytest.raises(HTTPException) as error:
        validate_projection({**configured, "model": "forged-model"}, models)
    assert error.value.status_code == 422


def test_endpoint_identity_is_stable_and_institution_bound():
    from app.institutional.webhooks import endpoint_id

    first = SimpleNamespace(ticket={"context": [[1, str(uuid4()), "contract"]]})
    second = SimpleNamespace(ticket={"context": [[1, str(uuid4()), "contract"]]})
    assert endpoint_id(first, "endpoint-key") == endpoint_id(first, "endpoint-key")
    assert endpoint_id(first, "endpoint-key") != endpoint_id(second, "endpoint-key")


def test_imported_transaction_aliases_delegate_inside_the_original_function():
    from contextlib import nullcontext
    from unittest.mock import patch

    from app.institutional import auth, settings, store

    profile = SimpleNamespace(ticket={"version": "cbn-institutional-spanish-p2-v1"})
    assert auth.transaction is settings.transaction is store.transaction
    with patch(
        "app.institutional.spanish.transaction", return_value=nullcontext("mapped")
    ) as delegated:
        with auth.transaction(profile, True, anonymous=True) as cursor:
            assert cursor == "mapped"
    delegated.assert_called_once_with(
        profile, True, permission=None, anonymous=True, recent=False
    )


def test_UI_contract_covers_typed_settings_and_every_action_without_secrets():
    from app.institutional.policy import ACTIONS
    from app.institutional.ui_contract import contract

    value = contract()
    assert {action["id"] for action in value["actions"]} == set(ACTIONS)
    paths = {field["path"] for field in value["fields"]["ai"]}
    assert {
        "vision_analysis_provider",
        "human_reply_style_enabled",
        "model_failover_enabled",
        "reply_min_chunk_delay_ms",
        "media.voice_id",
    } <= paths
    assert "password" not in str(value) and "ciphertext" not in str(value)
    assert value["model_selection_authority"] == "models"


def test_canonical_media_model_can_preserve_openrouter_identifier():
    from app.institutional.model_settings import project
    from app.institutional.models import AI

    source = AI(vision_analysis_provider="openrouter").model_dump(mode="json")
    value = project(
        source,
        {
            "selections": [
                {
                    "provider": "openrouter",
                    "category": "vision",
                    "selected_model": "provider/model-with-vision",
                    "display_name": "Vision model",
                    "voice_id": "",
                }
            ]
        },
    )
    assert value["media"]["vision_model"] == "provider/model-with-vision"


def test_SQL_UUID_casing_does_not_change_institution_context():
    from app.institutional.spanish_bindings import canonical_context

    identity = str(uuid4())
    assert canonical_context([[1, identity.upper(), "contract"]]) == [
        [1, identity, "contract"]
    ]
    cursor = Mock()
    cursor.execute.return_value = cursor
    cursor.fetchall.return_value = [[1, identity.upper(), "CBN-channels-parity-v1"]]
    migration.validate_data(
        cursor, 1, {"institution": identity, "bootstrap_sha256": "1" * 64}
    )
