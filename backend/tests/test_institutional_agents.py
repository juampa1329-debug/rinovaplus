"""Institutional agent transport, bounded identifiers and safe inheritance."""

from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.institutional.api import core_permission
from app.institutional import agents_policy
from app.modules.agents.domain import (
    AgentWrite,
    StageWrite,
    Configuration,
    effective_configuration,
    render_instructions,
    resolve,
)
from app.modules.ai.infrastructure.providers import AiError


@pytest.mark.parametrize(
    "path,method,permission,module",
    [
        ("/api/v1/agents", "GET", "agents.manage", "agents"),
        ("/api/v1/agents/simulate", "POST", "agents.manage", "agents"),
        ("/api/v1/agents/selection", "GET", "inbox.read", "inbox"),
        ("/api/v1/agents/conversations/id/draft", "POST", "inbox.write", "inbox"),
        ("/api/v1/agents/sources/id/scope", "PUT", "sources.manage", "agents"),
    ],
)
def test_institutional_authority_is_route_specific(path, method, permission, module):
    assert core_permission(path, method) == (permission, module)


@pytest.mark.parametrize("name", ["😀" * 51, "a" * 101])
def test_UTF16_SQL_name_limits_fail_before_any_write(name):
    with pytest.raises(ValidationError):
        AgentWrite(
            operation_id=uuid4(),
            revision=0,
            name=name,
            level="guide",
            configuration=Configuration(),
        )
    with pytest.raises(ValidationError):
        StageWrite(
            operation_id=uuid4(),
            revision=0,
            name=name,
            program_id=7,
            entry_rule="Ingreso",
            exit_rule="Salida",
            evidence_required="Nota",
        )


def test_profile_templates_are_literal_single_pass_and_keep_original_rules():
    config = Configuration(
        instructions="{saludo} {agent_name}",
        template_variables={"saludo": "{agent_name}"},
        rules=["Regla sin truncar"] * 60,
    ).model_dump(mode="json")
    agent = {"name": "Orientadora", "level": "guide", "configuration": config}
    text = render_instructions(agent, config)
    assert text == "{agent_name} Orientadora"
    assert effective_configuration([agent])["rules"] == config["rules"]


def test_missing_template_variable_fails_without_guessing_an_academic_value():
    cfg = Configuration(instructions="Programa {dato_oficial}").model_dump(mode="json")
    with pytest.raises(AiError, match="agents_template_variable_missing"):
        render_instructions(
            {"name": "Guía", "level": "guide", "configuration": cfg}, cfg
        )


def test_paid_simulation_enforces_ancestors_while_preview_can_inspect_pause():
    config = Configuration(
        instructions="No inventar",
        channels=["local"],
        monthly_token_limit=10000,
        primary_model="model",
    ).model_dump(mode="json")
    root = {
        "id": "root",
        "name": "Guía",
        "level": "guide",
        "program_id": None,
        "stage_id": None,
        "parent_id": None,
        "state": "paused",
        "enabled": False,
        "version": 1,
        "approved_version": None,
        "configuration": config,
    }
    assert (
        resolve({"root": root}, {}, {}, None, "local", simulation_id="root")["agent_id"]
        == "root"
    )
    with pytest.raises(AiError, match="agents_parent_or_agent_unavailable"):
        resolve(
            {"root": root},
            {},
            {},
            None,
            "local",
            simulation_id="root",
            require_active=True,
        )


def test_agents_SQL_rights_do_not_grant_academic_mutation_or_history_rewrite():
    rights = agents_policy.rights({})
    assert rights["crm_agents.History"] == ("SELECT", "INSERT")
    assert rights["crm_ai.KnowledgeDocument"] == ("SELECT",)
    assert all(not key.startswith("dbo.AC") for key in rights)
    assert agents_policy.TARGET.fullmatch("CBN_P5ES_TRIAL_20261027_1234abcd")
    assert not agents_policy.TARGET.fullmatch("HORARIOSSIIE")


def test_descendant_cannot_expand_tools_or_disable_parent_human_approval():
    cfg = Configuration(
        channels=["local"], capabilities=["program.read"], require_human_approval=True
    ).model_dump(mode="json")
    parent = {"name": "Guía", "level": "guide", "configuration": cfg}
    for changed in [
        {"capabilities": ["program.read", "crm.update"]},
        {"require_human_approval": False},
    ]:
        with pytest.raises(AiError, match="agents_child_permission_expansion"):
            effective_configuration(
                [
                    parent,
                    {
                        "name": "Programa",
                        "level": "program",
                        "configuration": {**cfg, **changed},
                    },
                ]
            )
