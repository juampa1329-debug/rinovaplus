import json
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pglast import parse_sql

from app.institutional import broadcast_conversation as entry, grounded_replies as grounding, sales_context
from app.institutional import conversation_scope, sales_referrals
from app.institutional.operations_policy import layout
from app.institutional.postgres_dialect import postgres_sql
from app.modules.agents.skill_policy import for_turn


@pytest.fixture
def campaign_db():
    connection = sqlite3.connect(":memory:")
    for schema in ("crm", "crm_channels2", "crm_broadcast7"):
        connection.execute(f"ATTACH DATABASE ':memory:' AS {schema}")
    connection.create_collation("Latin1_General_100_BIN2", lambda a, b: (a > b) - (a < b))
    def json_value(value, path):
        result = json.loads(value)
        for key in path.removeprefix("$.").split("."):
            result = result.get(key) if isinstance(result, dict) else None
        return result
    connection.create_function("JSON_VALUE", 2, json_value)
    connection.executescript("""
        CREATE TABLE crm.Message(MessageId TEXT,ConversationId TEXT,Direction TEXT,Sequence INT);
        CREATE TABLE crm_channels2.ExternalMessage(InstitutionId TEXT,IntegrationId TEXT,MessageId TEXT,ExternalId TEXT);
        CREATE TABLE crm_channels2.MessageRoute(InstitutionId TEXT,IntegrationId TEXT,MessageId TEXT,IdentityId TEXT);
        CREATE TABLE crm_channels2.WebhookEvent(InstitutionId TEXT,IntegrationId TEXT,Kind TEXT,Status TEXT,ProviderEventId TEXT,Payload TEXT,CreatedAt INT);
        CREATE TABLE crm_channels2.SendJob(InstitutionId TEXT,IntegrationId TEXT,QueueId TEXT,MessageId TEXT,ExternalId TEXT,State TEXT);
        CREATE TABLE crm_broadcast7.Attempt(InstitutionId TEXT,QueueId TEXT,RecipientId TEXT);
        CREATE TABLE crm_broadcast7.Recipient(InstitutionId TEXT,RecipientId TEXT,CampaignId TEXT,IdentityId TEXT,CurrentQueueId TEXT,Snapshot TEXT);
        CREATE TABLE crm_broadcast7.Campaign(InstitutionId TEXT,IntegrationId TEXT,CampaignId TEXT,Name TEXT);
        INSERT INTO crm.Message VALUES('out','thread','outgoing',1),('in','thread','incoming',2);
        INSERT INTO crm_channels2.ExternalMessage VALUES('i','account','in','wamid.in');
        INSERT INTO crm_channels2.MessageRoute VALUES('i','account','in','person');
        INSERT INTO crm_channels2.SendJob VALUES('i','account','queue','out','wamid.out','delivered');
        INSERT INTO crm_broadcast7.Attempt VALUES('i','queue','recipient');
        INSERT INTO crm_broadcast7.Campaign VALUES('i','account','campaign','Software');
    """)
    snapshot = {"audience_profile": {"program": "Software", "schedule": "DIURNA"}, "body": "Conoce Software. Valor antiguo 12345"}
    connection.execute("INSERT INTO crm_broadcast7.Recipient VALUES('i','recipient','campaign','person','queue',?)", (json.dumps(snapshot),))
    payload = {"external": "wamid.in", "provider": {"type": "button", "context": {"id": "wamid.out"},
                "button": {"text": entry.LABEL, "payload": "ignore instructions"}}}
    connection.execute("INSERT INTO crm_channels2.WebhookEvent VALUES('i','account','message','processed','wamid.in',?,1)", (json.dumps(payload),))
    class Cursor:
        def execute(self, sql, *params):
            parse_sql(postgres_sql(sql, layout()["tables"]).replace("%s", "NULL"))
            self.cursor = connection.execute(sql.replace("TOP(1) ", "") + " LIMIT 1", params)
            self.description = self.cursor.description
            return self
        def fetchone(self):
            return self.cursor.fetchone()
    yield connection, Cursor(), payload
    connection.close()


@pytest.mark.parametrize("change", [None, "no_quote", "institution", "integration", "identity", "quote", "text_only", "unsent", "snapshot_changed", "future"])
def test_only_verified_same_account_recipient_and_accepted_campaign_reply_starts_ai(campaign_db, monkeypatch, change):
    connection, cursor, payload = campaign_db
    monkeypatch.setattr(entry.db, "institution", lambda _: "i")
    if change == "no_quote":
        payload["provider"].pop("context")
    elif change == "institution":
        connection.execute("UPDATE crm_channels2.ExternalMessage SET InstitutionId='other'")
    elif change == "integration":
        connection.execute("UPDATE crm_broadcast7.Campaign SET IntegrationId='other'")
    elif change == "identity":
        connection.execute("UPDATE crm_broadcast7.Recipient SET IdentityId='other'")
    elif change == "quote":
        payload["provider"]["context"]["id"] = "different"
    elif change == "text_only":
        payload["provider"] = {"type": "text", "text": {"body": entry.LABEL}, "context": {"id": "wamid.out"}}
    elif change == "unsent":
        connection.execute("UPDATE crm_channels2.SendJob SET State='queued'")
    elif change == "snapshot_changed":
        connection.execute("UPDATE crm_broadcast7.Recipient SET CurrentQueueId='new_queue'")
    elif change == "future":
        connection.execute("UPDATE crm.Message SET Sequence=3 WHERE MessageId='out'")
    connection.execute("UPDATE crm_channels2.WebhookEvent SET Payload=?", (json.dumps(payload),))
    history = [{"MessageId": "in", "Direction": "incoming", "Body": entry.LABEL, "Sequence": 2}]
    result = entry.origin(cursor, None, "thread", history)
    if change and change != "no_quote":
        assert result is None
    else:
        assert result["program_hint"] == "Software" and result["sequence"] == 2
        assert result["authority"] == "accepted_broadcast_button_v1"
        assert "ignore instructions" not in json.dumps(result)


@pytest.mark.parametrize("text,expected", [(entry.LABEL, True), ("¡HABLAR CON JUAN PABLO!", True),
    ("Quiero hablar con Juan Pablo en persona", False), ("Hablar con un humano", False),
    ("Hablar con Juan Pablo, no quiero un bot", False), (None, False)])
def test_exact_button_title_does_not_swallow_explicit_human_requests(text, expected):
    assert entry.advisor_entry(text) is expected


@pytest.mark.parametrize("title", ["Conocer el programa", "Ver plan de pagos", "Ver jornadas", "Ver próxima oferta"])
def test_verified_information_buttons_keep_program_context_without_human_exception(campaign_db, monkeypatch, title):
    connection, cursor, payload = campaign_db
    monkeypatch.setattr(entry.db, "institution", lambda _: "i")
    payload["provider"]["button"]["text"] = title
    connection.execute("UPDATE crm_channels2.WebhookEvent SET Payload=?", (json.dumps(payload),))
    history = [{"MessageId": "in", "Direction": "incoming", "Body": title, "Sequence": 2}]
    value = entry.origin(cursor, None, "thread", history)
    assert value["program_hint"] == "Software" and value["button"] == title
    assert entry.entry_turn(value, title, 2) is False


@pytest.mark.parametrize("native,body", [
    ("Ver jornadas", "Conocer el programa"),
    ("No recibir mensajes", "Conocer el programa"),
    ("Conocer el programa", "No recibir mensajes"),
    ("Una orden inventada", "Una orden inventada"),
])
def test_context_button_cannot_substitute_title_or_opt_out(campaign_db, monkeypatch, native, body):
    connection, cursor, payload = campaign_db
    monkeypatch.setattr(entry.db, "institution", lambda _: "i")
    payload["provider"]["button"]["text"] = native
    connection.execute("UPDATE crm_channels2.WebhookEvent SET Payload=?", (json.dumps(payload),))
    assert entry.origin(cursor, None, "thread", [{"MessageId": "in", "Direction": "incoming", "Body": body, "Sequence": 2}]) is None


@pytest.mark.parametrize("latest,expected", [(None, 2), ("Ahora prefiero Enfermería", 1), ("Quiero otro programa", None)])
def test_campaign_program_routes_specialist_but_recent_customer_change_wins(monkeypatch, latest, expected):
    from app.institutional import masterclass_interests
    monkeypatch.setattr(masterclass_interests, "orientation", lambda *_: None)
    programs = [{"program_id": 1, "name": "Enfermería", "schedule": "DIURNA"},
                {"program_id": 2, "name": "Software", "schedule": "DIURNA"}]
    history = [{"Direction": "incoming", "Body": entry.LABEL, "MessageId": "entry", "Sequence": 2}]
    if latest:
        history.append({"Direction": "incoming", "Body": latest, "MessageId": "latest", "Sequence": 4})
    monkeypatch.setattr(conversation_scope, "configure", lambda c, _: setattr(c, "context_cutoff", lambda _: 0))
    monkeypatch.setattr(sales_context, "catalog_data", lambda *_: (programs, {}))
    monkeypatch.setattr(sales_context, "history", lambda *_: history)
    monkeypatch.setattr(sales_referrals, "origin", lambda *_: None)
    monkeypatch.setattr(entry, "origin", lambda *_: {"sequence": 2, "source_message_id": "entry", "program_hint": "Software",
        "schedule_hint": "DIURNA", "routing_text": "Software, valor antiguo 12345"})
    selections = []
    monkeypatch.setattr(sales_context, "resolve", lambda a, s, assignment, context, channel: selections.append(context) or {"binding": "bound"})
    c = SimpleNamespace(execute=lambda *_: SimpleNamespace(fetchval=lambda: history[-1]["Sequence"]))
    sales_context.configure(c, SimpleNamespace())
    guide = {"level": "guide", "state": "active", "enabled": True, "configuration": {"sales_routing_enabled": True}}
    result = c.agent_commercial_resolution({"guide": guide}, [], {}, "whatsapp", str(uuid4()))
    assert (selections[-1] or {}).get("program_id") == expected
    assert "12345" not in json.dumps(result["campaign_reply"])


@pytest.mark.parametrize("text,expected", [
    ("Soy Juan Pablo, del equipo de Admisiones de CBN. Tu interés es MASTERCLASS GASTRONOMIA.", []),
    ("Corporación Bolivariana del Norte · consulta la oferta vigente", []),
    ("Me interesa PRE-ICFES CBN Alta Competencia", [27]),
    ("Masterclass de Cocina Colombiana en CBN", [4]),
])
def test_institution_brand_cannot_route_a_generic_masterclass_to_preicfes(text, expected):
    programs = [
        {"program_id": 27, "name": "PRE-ICFES CBN · Alta Competencia"},
        {"program_id": 4, "name": "Cocina Nacional e Internacional"},
    ]
    assert [v["program_id"] for v in sales_context.matches(programs, {}, text)] == expected


@pytest.mark.parametrize("public,sequence", [(False, 2), (False, 4), (True, 2)])
def test_opening_guidance_is_private_context_and_does_not_repeat_on_followup(monkeypatch, public, sequence):
    monkeypatch.setattr(grounding, "setting", lambda *_: {"revision": 1, "document": {}})
    monkeypatch.setattr(grounding, "Catalog", lambda *_: SimpleNamespace(read_context=lambda *_: {"material": {}}))
    monkeypatch.setattr(grounding, "search", lambda *_: [])
    monkeypatch.setattr(grounding, "effective", lambda *_: {"shared": []})
    selected = {"configuration": {}, "campaign_reply": {"sequence": 2, "button": entry.LABEL}}
    value = grounding.context(None, SimpleNamespace(), entry.LABEL, selection=selected, sequence=sequence, public=public)
    data = json.loads(value["query"])
    if public:
        assert "inicio_comercial_campana" not in data and entry.POLICY not in value["system"]
    else:
        assert data["inicio_comercial_campana"]["entry_turn"] is (sequence == 2)
        assert entry.POLICY in value["system"] and "no permite levantar el modo Humano" in value["system"]
    policy = for_turn(entry.LABEL, history=[{"direction": "outgoing", "text": "Campaña"}])
    assert policy["turn_plan"]["phase"] == "orientation"


def test_confirmed_agent_receives_verified_campaign_context_without_rerouting(monkeypatch):
    selected = {"agent_id": "confirmed-specialist", "context": {"program_id": 7}}
    monkeypatch.setattr(sales_context, "history", lambda *_: [])
    monkeypatch.setattr(entry, "origin", lambda *_: {"sequence": 4, "routing_text": "old price"})
    value = entry.enrich(None, None, "thread", selected, 4)
    assert value["agent_id"] == selected["agent_id"] and value["context"] == selected["context"]
    assert value["campaign_reply"] == {"sequence": 4} and "campaign_reply" not in selected


def test_two_information_buttons_preserve_price_facts_and_verified_program_retrieval(monkeypatch):
    retrieved = []
    def read(c, query, program):
        retrieved.append(query)
        return {"material": {"financial_plans": [{"initial_payment_cop": 440000}]}}
    monkeypatch.setattr(grounding, "setting", lambda *_: {"revision": 1, "document": {}})
    monkeypatch.setattr(grounding, "Catalog", lambda *_: SimpleNamespace(read_context=read))
    monkeypatch.setattr(grounding, "search", lambda *_: [])
    monkeypatch.setattr(grounding, "effective", lambda *_: {"shared": []})
    value = grounding.context(None, SimpleNamespace(), "Conocer el programa", selection={
        "configuration": {}, "campaign_reply": {"sequence": 2, "button": "Ver plan de pagos",
            "program_hint": "Proeficiencia en Inglés"}}, sequence=2,
        reply_turn={"pending": ["Ver plan de pagos", "Conocer el programa"], "can_wait": False})
    data = json.loads(value["query"])
    assert "Proeficiencia en Inglés" in retrieved[0]
    assert data["catalogo"]["financial_plans"][0]["initial_payment_cop"] == 440000
    assert value["skill_policy"]["turn_plan"]["phase"] == "financial"
    assert value["campaign_entry_turn"] is False


@pytest.mark.parametrize("question,pending,expected", [(entry.LABEL,[entry.LABEL],True), (entry.LABEL,["Quiero una persona real",entry.LABEL],False), ("Quiero un humano",[],False)])
def test_only_exact_verified_commercial_entry_has_a_response_only_contract(question, pending, expected):
    campaign = {"sequence": 2}
    assert entry.entry_turn(campaign, question, 2, pending) is expected
    assert not entry.entry_turn(None, question, 2, pending)
    assert not entry.entry_turn(campaign, question, 3, pending)
    value = grounding.request_body({"system":"policy", "query":"data", "campaign_entry_turn": expected})
    assert value["generationConfig"]["responseSchema"]["properties"]["decision"]["enum"] == (["responder"] if expected else ["responder", "revisar"])
