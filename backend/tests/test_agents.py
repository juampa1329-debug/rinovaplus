"""Synthetic boundaries only: no database, credentials, providers or business seeds."""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.modules.agents import service
from app.modules.agents.domain import (
    AssignmentWrite,
    Configuration,
    ReviewWrite,
    SimulationRequest,
    SourceWrite,
    digest,
    effective_configuration,
    resolve,
    validate_hierarchy,
)
from app.modules.ai.application.admissions import AdmissionsService, validate_dispatch
from app.modules.ai.infrastructure.providers import AiError
from app.modules.channels.providers import ProviderFailure


def profile(key, level, parent=None, program=None, stage=None):
    config = Configuration(
        instructions="Approved operator instruction",
        channels=["local", "whatsapp"],
        capabilities=[
            "program.read",
            "sources.read",
            "conversation.reply",
            "human.handoff",
        ],
        primary_model="provider/model",
        monthly_token_limit=1000000,
        allow_reply=True,
    )
    return {
        "id": key,
        "name": key,
        "level": level,
        "parent_id": parent,
        "program_id": program,
        "stage_id": stage,
        "state": "active",
        "version": 1,
        "revision": 1,
        "approved_version": 1,
        "enabled": True,
        "configuration": config.model_dump(mode="json"),
    }


@pytest.fixture
def hierarchy():
    agents = {
        "guide": profile("guide", "guide"),
        "program-a": profile("program-a", "program", "guide", 7),
        "stage-a": profile("stage-a", "stage", "program-a", 7, "stage"),
        "program-b": profile("program-b", "program", "guide", 9),
    }
    return agents, {"stage": {"id": "stage", "program_id": 7, "approved": True}}


@pytest.mark.parametrize(
    "context,expected",
    [
        (None, "guide"),
        ({"program_id": 7}, "program-a"),
        ({"program_id": 7, "stage_id": "stage"}, "stage-a"),
        ({"program_id": 9}, "program-b"),
    ],
)
def test_single_owner_uses_confirmed_context(hierarchy, context, expected):
    agents, stages = hierarchy
    selected = resolve(agents, stages, {"mode": "automatic"}, context, "whatsapp")
    assert selected["agent_id"] == expected
    assert selected["supervisor_id"] == (
        None
        if expected == "guide"
        else "program-b"
        if expected == "program-b"
        else "program-a"
    )


@pytest.mark.parametrize(
    "change,code",
    [
        ("human", "agents_human_control"),
        ("manual_wrong_program", "agents_assignment_conflict"),
        ("stage_unapproved", "agents_stage_approval_required"),
        ("parent_paused", "agents_parent_or_agent_unavailable"),
        ("disabled", "agents_parent_or_agent_unavailable"),
        ("channel", "agents_channel_not_allowed"),
    ],
)
def test_resolution_never_silently_overrides_protection(hierarchy, change, code):
    agents, stages = hierarchy
    assignment, context, control = (
        {"mode": "automatic"},
        {"program_id": 7, "stage_id": "stage"},
        "ai",
    )
    if change == "human":
        control = "human"
    if change == "manual_wrong_program":
        assignment = {"mode": "manual", "agent_id": "program-b"}
    if change == "stage_unapproved":
        stages["stage"]["approved"] = False
    if change == "parent_paused":
        agents["program-a"]["state"] = "paused"
    if change == "disabled":
        agents["stage-a"]["enabled"] = False
    if change == "channel":
        agents["stage-a"]["configuration"]["channels"] = ["local"]
    with pytest.raises(AiError) as raised:
        resolve(agents, stages, assignment, context, "whatsapp", control)
    assert raised.value.code == code


def test_missing_subagent_falls_back_only_to_same_program(hierarchy):
    agents, stages = hierarchy
    del agents["stage-a"]
    assert (
        resolve(agents, stages, {}, {"program_id": 7, "stage_id": "stage"}, "local")[
            "agent_id"
        ]
        == "program-a"
    )
    del agents["program-a"]
    with pytest.raises(AiError, match="agents_owner_unavailable_or_ambiguous"):
        resolve(agents, stages, {}, {"program_id": 7, "stage_id": "stage"}, "local")


def test_ambiguous_program_owner_is_closed(hierarchy):
    agents, stages = hierarchy
    agents["duplicate"] = profile("duplicate", "program", "guide", 7)
    with pytest.raises(AiError, match="agents_owner_unavailable_or_ambiguous"):
        resolve(agents, stages, {}, {"program_id": 7}, "local")


def test_child_cannot_expand_permissions_or_budget(hierarchy):
    agents, _ = hierarchy
    agents["guide"]["configuration"]["capabilities"] = ["program.read"]
    with pytest.raises(AiError, match="agents_child_permission_expansion"):
        effective_configuration([agents["guide"], agents["program-a"]])
    agents["program-a"]["configuration"]["capabilities"] = ["program.read"]
    agents["program-a"]["configuration"]["monthly_token_limit"] = 1000001
    with pytest.raises(AiError, match="agents_child_budget_expansion"):
        effective_configuration([agents["guide"], agents["program-a"]])


def test_cross_program_stage_and_cycle_are_rejected(hierarchy):
    agents, stages = hierarchy
    agents["stage-a"]["program_id"] = 9
    with pytest.raises(AiError, match="agents_invalid_stage_parent"):
        validate_hierarchy(agents["stage-a"], agents, stages)
    agents["guide"]["parent_id"] = "program-a"
    with pytest.raises(AiError, match="agents_hierarchy_cycle"):
        validate_hierarchy(agents["program-a"], agents, stages)


def test_configuration_change_and_application_switch_change_binding(hierarchy):
    agents, stages = hierarchy
    context = {"id": "application-1", "program_id": 7, "revision": 1}
    original = resolve(
        agents,
        stages,
        {"mode": "manual", "agent_id": "program-a", "revision": 1},
        context,
        "local",
    )
    other = resolve(
        agents,
        stages,
        {"mode": "manual", "agent_id": "program-a", "revision": 1},
        {**context, "id": "application-2"},
        "local",
    )
    assert original["binding"] != other["binding"]
    agents["program-a"]["version"] = agents["program-a"]["approved_version"] = 2
    changed = resolve(
        agents,
        stages,
        {"mode": "manual", "agent_id": "program-a", "revision": 1},
        context,
        "local",
    )
    assert original["binding"] != changed["binding"]


class Cursor:
    def __init__(self, respond=lambda sql, args: None):
        self.respond = respond
        self.value = None
        self.commands = []

    def execute(self, sql, *args):
        self.commands.append((sql, args))
        self.value = self.respond(sql, args)
        return self

    def fetchone(self):
        return self.value

    def fetchval(self):
        return self.value

    def fetchall(self):
        return self.value or []


@contextmanager
def transaction(cursor):
    yield cursor


def test_idempotency_replays_only_identical_operation():
    request = ReviewWrite(
        operation_id=uuid4(), revision=2, confirmed=True, note="Human reviewed version"
    )
    payload = digest(["agent_review", "one", request.model_dump(mode="json")])
    cursor = Cursor(lambda sql, args: (payload,))
    assert service.replay(cursor, "agent_review", "one", request)[0]
    with pytest.raises(AiError, match="agents_operation_conflict"):
        service.replay(cursor, "agent_review", "another", request)


def test_profile_availability_requires_current_revision_without_approval_gate(
    monkeypatch, hierarchy
):
    agents, stages = hierarchy
    target = SimpleNamespace(transaction=lambda write=False: transaction(Cursor()))
    monkeypatch.setattr(service, "load", lambda cursor: (agents, stages))
    denied = ReviewWrite(
        operation_id=uuid4(), revision=1, confirmed=False, note="Human decision"
    )
    assert service.AgentsService.review_agent(target, "guide", denied)["confirmed"]
    agents["guide"]["revision"] = 2
    stale = denied.model_copy(update={"confirmed": True})
    with pytest.raises(AiError, match="agents_revision_conflict"):
        service.AgentsService.review_agent(target, "guide", stale)


def test_scoped_retrieval_filters_before_reading_bodies():
    doc = str(uuid4())
    cursor = Cursor()
    assert (
        service.scoped_sources(
            cursor,
            "costos",
            {"program_id": 7, "stage_id": "one"},
            {"document_ids": [doc]},
        )
        == []
    )
    sql, args = cursor.commands[0]
    assert "s.ProgramId IS NULL OR s.ProgramId=?" in sql
    assert "s.StageId IS NULL OR s.StageId=?" in sql
    assert "s.DocumentRevision=d.Revision" in sql
    assert args[-2:] == (7, "one")


def test_approved_context_rejects_changed_stage_revision():
    cursor = Cursor(
        lambda sql, args: (
            ("ctx", 7, None, None, "stage", 4, 2, 10)
            if "FROM crm_agents.Context" in sql
            else (3, 3)
        )
    )
    with pytest.raises(AiError, match="agents_stage_approval_required"):
        service.context_row(cursor, "conversation", "ctx")


def test_budget_reservation_is_single_and_includes_ancestors(monkeypatch, hierarchy):
    from app.modules.agents import runtime

    monkeypatch.setattr(runtime, "require_execution", lambda _: None)
    monkeypatch.setattr(runtime, "reserve_execution", lambda *args: None)
    agents, stages = hierarchy
    selected = resolve(agents, stages, {}, {"program_id": 7}, "local")
    cursor = Cursor(lambda sql, args: 0 if "SUM(" in sql else None)
    monkeypatch.setattr(service, "load", lambda _: (agents, stages))
    service.AgentsService.reserve(
        None, cursor, "turn", selected, [{"content": "source"}]
    )
    inserts = [(s, a) for s, a in cursor.commands if s.startswith("INSERT")]
    assert len(inserts) == 1
    assert json_array(inserts[0][1][2]) == ["guide", "program-a"]
    assert [a[0] for s, a in cursor.commands if "SUM(" in s] == ["guide", "program-a"]


def json_array(value):
    import json

    return json.loads(value)


def test_worker_guard_and_finish_reject_changed_frontier_before_writes():
    cursor = Cursor(lambda sql, args: (1,))
    target = SimpleNamespace(
        transaction=lambda write=False: transaction(cursor),
        snapshot=lambda c, j: {"binding": ["new"]},
    )
    job = ("message", "conversation", "identity", 1, "lease")
    with pytest.raises(AiError, match="admissions_snapshot_obsolete"):
        AdmissionsService.guard(target, job, ["old"])
    with pytest.raises(AiError, match="admissions_snapshot_obsolete"):
        AdmissionsService.finish(target, job, {"binding": ["old"]})
    assert not any(sql.startswith(("INSERT", "UPDATE")) for sql, _ in cursor.commands)


def test_dispatch_revalidates_agent_and_context_before_send(monkeypatch):
    import json

    binding = [1, 1, 0, 1, 1, 1, 0, 0, 8, "sql", "old-agent-binding"]

    def respond(sql, args):
        if "OBJECT_ID" in sql:
            return 1
        if "SELECT j.Result" in sql:
            return (json.dumps({"binding": binding}), "conversation", "question")
        if "SELECT p.Revision" in sql:
            return (1, 1, True, 1, 1, True, 0, '{"enabled":true}')
        if "MAX(Sequence)" in sql:
            return 8
        return "whatsapp"

    cursor = Cursor(respond)
    monkeypatch.setattr(service, "managed_conversation", lambda *args: True)
    monkeypatch.setattr(
        service,
        "runtime_context",
        lambda *args: {
            "institutional": {"fingerprint": "sql"},
            "binding": "new-context-binding",
        },
    )
    with pytest.raises(ProviderFailure, match="admissions_generation_obsolete"):
        validate_dispatch(cursor, "queue", 1)
    assert not any(sql.startswith(("INSERT", "UPDATE")) for sql, _ in cursor.commands)


def test_simulation_pins_draft_and_version_without_network_or_mutation(
    monkeypatch, hierarchy
):
    agents, stages = hierarchy
    guide = agents.pop("guide")
    key = str(uuid4())
    guide.update(id=key, state="draft", approved_version=None, enabled=False)
    agents[key] = guide
    cursor = Cursor()
    monkeypatch.setattr(service, "load", lambda _: ({key: guide}, stages))
    monkeypatch.setattr(service, "check_program", lambda *args: None)
    monkeypatch.setattr(
        service,
        "read_context",
        lambda *args: {"sources": [], "fingerprint": "public-only"},
    )
    monkeypatch.setattr(service, "scoped_sources", lambda *args: [])
    target = SimpleNamespace(transaction=lambda write=False: transaction(cursor))
    request = SimulationRequest(
        agent_id=UUID(key),
        config_version=1,
        question="Program options",
        request_id=uuid4(),
    )
    result = asyncio.run(service.AgentsService.simulate(target, request))
    assert result["agent_id"] == key
    assert result["config_version"] == 1
    assert (
        not result["network_called"]
        and not result["crm_written"]
        and not result["delivered"]
    )
    assert all(sql.startswith("SELECT") for sql, _ in cursor.commands)
    with pytest.raises(AiError, match="agents_revision_conflict"):
        asyncio.run(
            service.AgentsService.simulate(
                target, request.model_copy(update={"config_version": 2})
            )
        )


def test_source_date_and_assignment_unknown_modes_are_rejected():
    with pytest.raises(ValueError):
        SourceWrite(
            operation_id=uuid4(),
            revision=0,
            note="Review",
            confirmed=True,
            owner="Academic office",
            valid_until="2026-99-99",
        )
    with pytest.raises(ValueError):
        AssignmentWrite(
            operation_id=uuid4(),
            revision=0,
            note="Review",
            confirmed=True,
            mode="implicit",
        )
