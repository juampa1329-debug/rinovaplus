"P3 SQL workspace: bounded reads, current authority, reversible identity groups."

import json
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, Query
from pydantic import Field, field_validator, model_validator

from app.institutional import db
from app.institutional.auth import authorize
from app.institutional.models import Strict
from app.institutional.policy import request_authority
from app.institutional.store import transaction
from app.modules.crm_configuration.application.service import validate_contact
from app.modules.inbox.application.service import pattern
from app.modules.inbox.application.service import rows as legacy_rows
from app.modules.inbox.application.state import (
    change_control,
    mark_read,
    save_assessment,
)
from app.sql_workspace import CONTACT_COLUMNS, CONTACT_KEYS, Contact, Identifier

PAGE = 25


def rows(cursor):
    result = legacy_rows(cursor)
    identifiers = {
        "id",
        "conversationId",
        "contactId",
        "userId",
        "sourceContactId",
        "targetContactId",
    }
    for row in result:
        for key in identifiers & row.keys():
            if isinstance(row[key], str):
                row[key] = db.uid(row[key])
    return result


class Command(Strict):
    operationId: Identifier
    revision: Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$")]


class ContactWrite(Command):
    client: Contact

    @model_validator(mode="after")
    def sql_lengths(self):
        for key, limit in {
            "name": 100,
            "phone": 40,
            "city": 100,
            "program": 200,
            "schedule": 100,
            "stage": 60,
            "tags": 1000,
            "notes": 1000,
            "type": 100,
            "interests": 300,
        }.items():
            if len(getattr(self.client, key).encode("utf-16-le")) // 2 > limit:
                raise ValueError("SQL_text_limit")
        return self


class ConversationWrite(Command):
    state: Literal["open", "waiting", "closed"]
    priority: Literal["low", "normal", "high", "urgent"]
    mode: Literal["human", "ai"]
    userId: Identifier | None = None
    unread: bool
    readThrough: Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$")] | None = None

    @model_validator(mode="after")
    def observed_read(self):
        if not self.unread and self.readThrough is None:
            raise ValueError("observed_read_sequence_required")
        return self


class ControlWrite(Strict):
    operationId: Identifier
    expectedEpoch: Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$")]
    mode: Literal["human", "ai"]


class ConversationRead(Strict):
    operationId: Identifier
    readThrough: Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$")]


class MessageWrite(Command):
    body: Annotated[str, Field(min_length=1, max_length=4000)]
    mediaId: Identifier | None = None

    @field_validator("body")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("blank_message")
        if len(value.encode("utf-16-le")) // 2 > 4000:
            raise ValueError("SQL_text_limit")
        return value.strip()


class NoteWrite(Command):
    body: Annotated[str, Field(min_length=1, max_length=2000)]

    @field_validator("body")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("blank_note")
        if len(value.encode("utf-16-le")) // 2 > 2000:
            raise ValueError("SQL_text_limit")
        return value.strip()


class TaskWrite(Command):
    conversationId: Identifier
    title: Annotated[str, Field(min_length=1, max_length=120)]
    status: Literal["pending", "completed", "cancelled"] = "pending"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    userId: Identifier | None = None
    dueAt: str | None = None

    @model_validator(mode="after")
    def validate_values(self):
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("blank_task")
        if len(self.title.encode("utf-16-le")) // 2 > 120:
            raise ValueError("SQL_text_limit")
        if self.dueAt is not None:
            parsed = datetime.fromisoformat(self.dueAt.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timezone_required")
            self.dueAt = parsed.astimezone(timezone.utc).isoformat()
        return self


class MergeWrite(Command):
    sourceContactId: Identifier
    targetContactId: Identifier
    confirmedSamePerson: Literal[True]

    @field_validator("confirmedSamePerson", mode="before")
    @classmethod
    def explicit(cls, value):
        if value is not True:
            raise ValueError("human_confirmation_required")
        return value


class ManualWrite(Command):
    score: Annotated[int, Field(strict=True, ge=0, le=100)] | None
    temperature: Literal["cold", "warm", "hot"] | None


class PolicyWrite(Command):
    enabled: bool
    thresholdMinutes: Annotated[int, Field(strict=True, ge=1, le=525600)]


def primary(c, contact):
    row = c.execute(
        (
            "SELECT TargetContactId FROM crm_workspac"
            "e.Merge WHERE SourceContactId=? AND Acti"
            "ve=1"
        ),
        contact,
    ).fetchone()
    return db.uid(str(row[0])) if row else db.uid(contact)


def members(c, contact):
    contact = primary(c, contact)
    return [contact] + [
        db.uid(str(r[0]))
        for r in c.execute(
            (
                "SELECT SourceContactId FROM crm_workspac"
                "e.Merge WHERE TargetContactId=? AND Acti"
                "ve=1 ORDER BY SourceContactId"
            ),
            contact,
        ).fetchall()
    ]


def read_contact(c, contact):
    row = c.execute(
        "SELECT " + CONTACT_COLUMNS + " FROM crm.Contact WHERE ContactId=?", contact
    ).fetchone()
    if row is None:
        raise HTTPException(404, "client_not_found")
    result = dict(zip(CONTACT_KEYS, row, strict=True))
    result["id"] = db.uid(str(result["id"]))
    result["customValues"] = json.loads(result["customValues"])
    from app.modules.contacts.api.router import PROFILE_COLUMNS, PROFILE_KEYS

    profile = c.execute(
        "SELECT " + PROFILE_COLUMNS + " FROM crm_identity.Profile WHERE ContactId=?",
        contact,
    ).fetchone()
    if profile:
        result["institutionalProfile"] = dict(zip(PROFILE_KEYS, profile, strict=True))
    return result


def revision(c):
    state = c.execute(
        ("SELECT Revision FROM crm_workspace.State WHERE StateId=1")
    ).fetchval()
    configuration = c.execute(
        ("SELECT Revision FROM crm_config.Configuration WHERE ConfigurationId=1")
    ).fetchval()
    return str(state + configuration)


def active_user(c, settings, value):
    if (
        value
        and not c.execute(
            (
                "SELECT 1 FROM crm_access.AccessUser u JO"
                "IN crm_access.Role r ON r.InstitutionId="
                "u.InstitutionId AND r.RoleKey=u.RoleKey "
                "WHERE u.InstitutionId=? AND u.UserId=? A"
                "ND u.Active=1 AND r.Active=1 AND EXISTS("
                "SELECT 1 FROM OPENJSON(r.Actions) WHERE "
                "value='inbox.write')"
            ),
            db.institution(settings),
            value,
        ).fetchone()
    ):
        raise HTTPException(422, "active_workspace_user_required")


def risk_projection(row, *, sequence, stage, state, now):
    "A recorded rule result is usable only for the same current inputs and day."
    result = {
        "status": "unknown",
        "level": "unknown",
        "score": None,
        "source": "not_evaluated",
        "asOf": None,
        "fresh": False,
        "reasons": ["Sin evidencia suficiente para evaluar."],
        "nextAction": ("Revisar la conversación y confirmar el siguiente paso."),
        "probability": None,
    }
    if state == "closed":
        return dict(
            result,
            status="not_applicable",
            level="not_applicable",
            reasons=["La conversación está cerrada."],
            nextAction=("Sin acción de seguimiento mientras permanezca cerrada."),
        )
    if row is None:
        return result
    result["asOf"] = db.utc(row["AsOfUtc"])
    try:
        evidence = json.loads(row["EvidenceJson"])
        reasons = json.loads(row["ReasonsJson"])
        at = row["AsOfUtc"].replace(tzinfo=timezone.utc)
        if (
            row["Status"] != "known"
            or evidence.get("formula_version") != "churn-rubric-v1"
            or row["InputSequence"] != sequence
            or row["StageSnapshot"] != stage
            or not 0 <= (now - at).total_seconds() <= 86400
            or evidence.get("input_sequence") != sequence
            or evidence.get("status") != "known"
            or row["FormulaVersion"] != "churn-rubric-v1"
            or evidence.get("score") != row["RiskScore"]
            or evidence.get("level") != row["RiskLevel"]
            or not evidence.get("evidence_message_ids")
            or row["RiskLevel"] not in {"low", "medium", "high"}
            or type(row["RiskScore"]) is not int
            or not 0 <= row["RiskScore"] <= 100
        ):
            return dict(
                result,
                reasons=[
                    ("La evaluación registrada requiere actualizar su evidencia.")
                ],
            )
        labels = {
            "waiting_for_client": (
                "Sin nueva respuesta del contacto tras la respuesta confirmada."
            ),
            "configured_stage_weight": (
                "La etapa actual aporta a la rúbrica configurada."
            ),
            "confirmed_unanswered_responses": (
                "Hay respuestas confirmadas pendientes de contestación."
            ),
            "cost_answer_without_new_incoming_72h": (
                "Pasaron al menos 72 horas sin nueva respuesta tras informar el valor."
            ),
            "waiting_over_48h": ("Espera prolongada desde la respuesta confirmada."),
            "waiting_over_24h": "Seguimiento pendiente.",
            "slow_response": "La respuesta tardó en confirmarse.",
            "stage_weight": "Etapa del seguimiento.",
        }
        clean = [
            labels.get(x, "Señal de seguimiento registrada.")
            for x in reasons
            if isinstance(x, str)
        ]
        return dict(
            result,
            status="known",
            level=row["RiskLevel"],
            score=row["RiskScore"],
            source="rule",
            fresh=True,
            reasons=clean or [("Rúbrica de seguimiento con evidencia confirmada.")],
            nextAction=("Priorizar contacto humano y acordar el siguiente paso.")
            if row["RiskLevel"] == "high"
            else ("Revisar compromisos y mantener el seguimiento acordado."),
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        return result


def risk(c, contact, conversation=None):
    ids = members(c, contact)
    canonical_stage = read_contact(c, ids[0])["stage"]
    slots = ",".join("?" for _ in ids)
    found = db.rows(
        c,
        (
            "SELECT v.ConversationId,v.State,p.Stage,"
            "(SELECT COALESCE(MAX(Sequence),0) FROM c"
            "rm.Message WHERE ConversationId=v.Conver"
            "sationId) AS InputSequence FROM crm.Conv"
            "ersation v JOIN crm.Contact p ON p.Conta"
            "ctId=v.ContactId WHERE v.ContactId IN ("
        )
        + slots
        + ")"
        + (" AND v.ConversationId=?" if conversation else ""),
        *ids,
        *([conversation] if conversation else []),
    )
    now = c.execute("SELECT SYSUTCDATETIME()").fetchval().replace(tzinfo=timezone.utc)
    assessments = []
    for item in found:
        stored = db.one(
            c,
            (
                "SELECT TOP(1) * FROM crm_marketing.Churn"
                "Assessment WHERE ConversationId=? ORDER "
                "BY AsOfUtc DESC,CreatedAtUtc DESC,Assess"
                "mentId"
            ),
            item["ConversationId"],
        )
        view = risk_projection(
            stored,
            sequence=item["InputSequence"],
            stage=canonical_stage,
            state=item["State"],
            now=now,
        )
        if view["status"] == "known":
            try:
                evidence_ids = list(
                    dict.fromkeys(
                        db.uid(value)
                        for value in json.loads(stored["EvidenceJson"])[
                            "evidence_message_ids"
                        ]
                    )
                )
                if not 1 <= len(evidence_ids) <= 100:
                    raise ValueError("evidence_limit")
                context = c.execute(
                    (
                        "SELECT 1 FROM crm_channels.ExternalIdent"
                        "ity i JOIN crm_marketing.EvaluationRun r"
                        " ON r.RunId=? AND r.State='completed' WH"
                        "ERE i.IdentityId=? AND i.ConversationId="
                        "?"
                    ),
                    stored["RunId"],
                    stored["IdentityId"],
                    item["ConversationId"],
                ).fetchone()
                matched = c.execute(
                    (
                        "SELECT COUNT(DISTINCT m.MessageId) FROM "
                        "crm.Message m JOIN crm_channels.MessageR"
                        "oute route ON route.MessageId=m.MessageI"
                        "d AND route.IdentityId=? WHERE m.Convers"
                        "ationId=? AND m.MessageId IN ("
                    )
                    + ",".join("?" for _ in evidence_ids)
                    + ")",
                    stored["IdentityId"],
                    item["ConversationId"],
                    *evidence_ids,
                ).fetchval()
                if not context or matched != len(evidence_ids):
                    raise ValueError("evidence_scope_changed")
            except (ValueError, TypeError, KeyError, HTTPException):
                view = risk_projection(
                    None,
                    sequence=item["InputSequence"],
                    stage=canonical_stage,
                    state=item["State"],
                    now=now,
                )
                view["reasons"] = [
                    (
                        "La evidencia registrada requiere validar"
                        " su conversación y su ejecución."
                    )
                ]
        view["conversationId"] = db.uid(str(item["ConversationId"]))
        assessments.append(view)
    known = [a for a in assessments if a["status"] == "known"]
    unknown = [a for a in assessments if a["status"] == "unknown"]
    selected = (
        max(known, key=lambda a: a["score"])
        if known
        else (
            (unknown or assessments)[0]
            if assessments
            else risk_projection(None, sequence=0, stage="", state="open", now=now)
        )
    )
    return dict(
        selected,
        scope="contact_group",
        conversationCount=len(found),
        trainedPrediction=False,
    )


BASE = (
    " FROM crm.Conversation v JOIN crm.Contac"
    "t p ON p.ContactId=v.ContactId LEFT JOIN"
    " crm_workspace.Assignment a ON a.Convers"
    "ationId=v.ConversationId LEFT JOIN crm_a"
    "ccess.AccessUser u ON u.UserId=a.UserId "
    "AND u.InstitutionId=a.InstitutionId "
)
SLA_DEADLINE = "DATEADD(minute,sp.ThresholdMinutes,pending.startedAt)"
SLA_STATUS = (
    "CASE WHEN sp.PolicyId IS NULL THEN 'not_configured' "
    "WHEN sp.Enabled=0 THEN 'disabled' WHEN v.State='closed' THEN 'closed' "
    "WHEN pending.startedAt IS NULL THEN 'no_incoming' "
    f"WHEN {SLA_DEADLINE}<=SYSUTCDATETIME() THEN 'overdue' ELSE 'on_time' END"
)


def sla_join(operational):
    local = "NOT EXISTS(SELECT 1 FROM crm_channels.ExternalIdentity WHERE ConversationId=v.ConversationId)"
    confirmed = (
        "EXISTS(SELECT 1 FROM crm_channels.outbound_queue q "
        "WHERE q.MessageId=m.MessageId AND q.State IN('sent','delivered','read'))"
    )
    if operational:
        local += " AND NOT EXISTS(SELECT 1 FROM crm_channels2.ExternalIdentity WHERE ConversationId=v.ConversationId)"
        confirmed += (
            " OR EXISTS(SELECT 1 FROM crm_channels2.MessageRoute route "
            "JOIN crm_channels2.SendJob job ON job.InstitutionId=route.InstitutionId "
            "AND job.IntegrationId=route.IntegrationId AND job.QueueId=route.QueueId "
            "AND job.MessageId=route.MessageId AND job.IdentityId=route.IdentityId "
            "WHERE route.MessageId=m.MessageId AND job.ExternalId IS NOT NULL "
            "AND job.State IN('sent','delivered','read'))"
        )
    return (
        " LEFT JOIN crm_inbox.SlaPolicy sp ON sp.PolicyId=1 "
        "OUTER APPLY(SELECT MAX(m.Sequence) AS seq FROM crm.Message m "
        "WHERE sp.Enabled=1 AND m.ConversationId=v.ConversationId AND m.Direction='outgoing' "
        f"AND (({local}) OR {confirmed})) replied "
        "OUTER APPLY(SELECT MIN(m.CreatedAt) AS startedAt FROM crm.Message m "
        "WHERE sp.Enabled=1 AND m.ConversationId=v.ConversationId AND m.Direction='incoming' "
        "AND m.Sequence>COALESCE(replied.seq,0)) pending "
    )


ALIASES = (
    "NOT EXISTS(SELECT 1 FROM crm_workspace.M"
    "erge hidden WHERE hidden.SourceContactId"
    "=p.ContactId AND hidden.Active=1)"
)


class Workspace:
    foundation = True
    operational_channels = False

    def conversation_risk(self, c, contact, conversation):
        return risk(c, contact, conversation)

    def populate_inbox_risk(self, c, items):
        for row in items:
            row["risk"] = risk(c, row["id"], row["conversationId"])

    def inbox_channel_expression(self):
        legacy = (
            "(SELECT TOP(1) Channel FROM crm_channels.ExternalIdentity "
            "WHERE ConversationId=v.ConversationId ORDER BY IdentityId)"
        )
        if not self.operational_channels:
            return f"COALESCE({legacy},'local')"
        connected = (
            "(SELECT TOP(1) ca.Channel FROM crm_channels2.ExternalIdentity ci "
            "JOIN crm_channels2.Integration ca ON ca.InstitutionId=ci.InstitutionId "
            "AND ca.IntegrationId=ci.IntegrationId WHERE ci.ConversationId=v.ConversationId "
            "ORDER BY ci.IdentityId)"
        )
        return f"COALESCE({connected},{legacy},'local')"

    def inbox_account_columns(self):
        if not self.operational_channels:
            return ""
        account = (
            " FROM crm_channels2.ExternalIdentity ci "
            "JOIN crm_channels2.Integration ca ON ca.InstitutionId=ci.InstitutionId "
            "AND ca.IntegrationId=ci.IntegrationId "
            "WHERE ci.ConversationId=v.ConversationId ORDER BY ci.IdentityId)"
        )
        return (
            ",(SELECT TOP(1) ca.DisplayName" + account + " AS accountName"
            ",(SELECT TOP(1) (SELECT TOP(1) "
            "JSON_VALUE(op.ResultMetadata,'$.asset.display_phone_number') "
            "FROM crm_channels2.ProviderOperation op "
            "WHERE op.InstitutionId=ca.InstitutionId AND op.IntegrationId=ca.IntegrationId "
            "AND op.ApplicationId=ca.ApplicationId AND op.Action='verify' "
            "AND op.Status='confirmed' AND ca.Channel='whatsapp' "
            "AND JSON_VALUE(op.ResultMetadata,'$.asset.id')=ca.ExternalAccountId "
            "ORDER BY op.CompletedAt DESC,op.OperationId)" + account + " AS accountPhone"
        )

    def __init__(self, settings):
        self.profile = settings

    def transaction(self, write=False):
        return transaction(self.profile, write)

    def read(self):
        # Legacy configuration consumers receive bounded metadata, never a full
        # workspace.
        with self.transaction() as c:
            return {
                "clients": [],
                "threads": [],
                "contactGroups": [],
                "revision": revision(c),
            }

    def directory(self, q="", offset=0):
        with self.transaction() as c:
            values = rows(
                c.execute(
                    (
                        "SELECT u.UserId AS id,u.DisplayName AS n"
                        "ame,u.Active AS active FROM crm_access.A"
                        "ccessUser u JOIN crm_access.Role r ON r."
                        "InstitutionId=u.InstitutionId AND r.Role"
                        "Key=u.RoleKey WHERE u.InstitutionId=? AN"
                        "D u.Active=1 AND r.Active=1 AND EXISTS(S"
                        "ELECT 1 FROM OPENJSON(r.Actions) WHERE v"
                        "alue='inbox.write') AND (?='' OR u.Displ"
                        "ayName LIKE ?) ORDER BY u.DisplayName,u."
                        "UserId OFFSET ? ROWS FETCH NEXT 26 ROWS "
                        "ONLY"
                    ),
                    db.institution(self.profile),
                    q,
                    pattern(q),
                    offset,
                )
            )
            return {"items": values[:25], "hasMore": len(values) > 25}

    def policy(self):
        with self.transaction() as c:
            row = c.execute(
                (
                    "SELECT Enabled,ThresholdMinutes FROM crm"
                    "_inbox.SlaPolicy WHERE PolicyId=1"
                )
            ).fetchone()
            return {
                "configured": row is not None,
                "enabled": bool(row[0]) if row else False,
                "thresholdMinutes": row[1] if row else None,
                "revision": revision(c),
            }

    def listing(
        self,
        area,
        q="",
        stage="",
        tag="",
        city="",
        contactType="",
        queue="all",
        user="",
        channel="",
        offset=0,
        anchor="",
        program="",
        program_id=None,
        state="",
        temperature="",
        riskLevel="",
        after_revision="",
    ):
        with self.transaction() as c:
            if offset and not anchor:
                raise HTTPException(422, "page_anchor_required")
            actor = authorize(
                c,
                self.profile,
                request_authority.get(),
                "inbox.read" if area == "inbox" else "crm.read",
            )
            current_revision = revision(c)
            if anchor and anchor != current_revision:
                raise HTTPException(409, "page_changed")
            if area == "inbox" and not offset and after_revision == current_revision:
                return {"revision": current_revision, "unchanged": True}
            where = ["1=1"]
            params = []
            if area == "clients":
                where.append(ALIASES)
                # A grouped source can match; the canonical person is selected before
                # pagination.
                where.append(
                    (
                        "EXISTS(SELECT 1 FROM crm.Contact f WHERE"
                        " (f.ContactId=p.ContactId OR EXISTS(SELE"
                        "CT 1 FROM crm_workspace.Merge g WHERE g."
                        "Active=1 AND g.TargetContactId=p.Contact"
                        "Id AND g.SourceContactId=f.ContactId)) A"
                        "ND (?='' OR f.Name LIKE ? OR f.Phone LIK"
                        "E ?)) AND (?='' OR p.Stage=?) AND (?='' "
                        "OR EXISTS(SELECT 1 FROM STRING_SPLIT(p.T"
                        "ags,',') WHERE LTRIM(RTRIM(value))=?)) A"
                        "ND (?='' OR p.City=?) AND (?='' OR p.Typ"
                        "e=?)"
                    )
                )
                params.extend(
                    [
                        q,
                        pattern(q),
                        pattern(q),
                        stage,
                        stage,
                        tag,
                        tag,
                        city,
                        city,
                        contactType,
                        contactType,
                    ]
                )
            else:
                where.append(
                    (
                        "(?='' OR p.Name LIKE ? OR p.Phone LIKE ?"
                        " OR EXISTS(SELECT 1 FROM crm.Message WHE"
                        "RE ConversationId=v.ConversationId AND B"
                        "ody LIKE ?)) AND (?='' OR p.Stage=?)"
                    )
                )
                params.extend([q, pattern(q), pattern(q), pattern(q), stage, stage])
            if queue == "unread":
                where.append("v.Unread=1")
            elif queue == "mine":
                where.append("a.UserId=?")
                params.append(actor["UserId"])
            elif queue == "unassigned":
                where.append("a.UserId IS NULL")
            elif queue in ("human", "ai"):
                where.append("v.ControlMode=?")
                params.append(queue)
            elif queue in ("open", "waiting", "closed"):
                where.append("v.State=?")
                params.append(queue)
            elif queue == "hot":
                where.append(
                    (
                        "EXISTS(SELECT 1 FROM crm_channels.Conver"
                        "sationProfile WHERE ConversationId=v.Con"
                        "versationId AND (Temperature='hot' OR Le"
                        "adScore>=75))"
                    )
                )
            elif queue == "sla":
                where.append(f"({SLA_STATUS})='overdue'")
            if queue == "churn" or riskLevel:
                where.append(
                    (
                        "EXISTS(SELECT 1 FROM crm_marketing.Churn"
                        "Assessment x WHERE x.AssessmentId=(SELEC"
                        "T TOP(1) AssessmentId FROM crm_marketing"
                        ".ChurnAssessment WHERE ConversationId=v."
                        "ConversationId ORDER BY AsOfUtc DESC,Cre"
                        "atedAtUtc DESC,AssessmentId) AND v.State"
                        "<>'closed' AND x.Status='known' AND x.Ri"
                        "skLevel=? AND x.RiskScore BETWEEN 0"
                        " AND 100 AND x.FormulaVersion='churn-rub"
                        "ric-v1' AND x.StageSnapshot COLLATE Lati"
                        "n1_General_100_BIN2=COALESCE((SELECT tar"
                        "get.Stage FROM crm_workspace.Merge group"
                        "ed JOIN crm.Contact target ON target.Con"
                        "tactId=grouped.TargetContactId WHERE gro"
                        "uped.SourceContactId=p.ContactId AND gro"
                        "uped.Active=1),p.Stage) COLLATE Latin1_G"
                        "eneral_100_BIN2 AND x.InputSequence=(SEL"
                        "ECT MAX(Sequence) FROM crm.Message WHERE"
                        " ConversationId=v.ConversationId) AND x."
                        "AsOfUtc BETWEEN DATEADD(day,-1,SYSUTCDAT"
                        "ETIME()) AND SYSUTCDATETIME() AND JSON_V"
                        "ALUE(x.EvidenceJson,'$.status')='known' "
                        "AND JSON_VALUE(x.EvidenceJson,'$.formula"
                        "_version')='churn-rubric-v1' AND TRY_CON"
                        "VERT(bigint,JSON_VALUE(x.EvidenceJson,'$"
                        ".input_sequence'))=x.InputSequence AND T"
                        "RY_CONVERT(int,JSON_VALUE(x.EvidenceJson"
                        ",'$.score'))=x.RiskScore AND JSON_VALUE("
                        "x.EvidenceJson,'$.level') COLLATE Latin1"
                        "_General_100_BIN2=x.RiskLevel COLLATE La"
                        "tin1_General_100_BIN2 AND EXISTS(SELECT "
                        "1 FROM crm_channels.ExternalIdentity i W"
                        "HERE i.IdentityId=x.IdentityId AND i.Con"
                        "versationId=v.ConversationId) AND EXISTS"
                        "(SELECT 1 FROM crm_marketing.EvaluationR"
                        "un er WHERE er.RunId=x.RunId AND er.Stat"
                        "e='completed') AND (SELECT COUNT(*) FROM"
                        " OPENJSON(x.EvidenceJson,'$.evidence_mes"
                        "sage_ids')) BETWEEN 1 AND 100 AND NOT EX"
                        "ISTS(SELECT 1 FROM OPENJSON(x.EvidenceJs"
                        "on,'$.evidence_message_ids') e WHERE TRY"
                        "_CONVERT(uniqueidentifier,e.value) IS NU"
                        "LL OR NOT EXISTS(SELECT 1 FROM crm.Messa"
                        "ge m JOIN crm_channels.MessageRoute mr O"
                        "N mr.MessageId=m.MessageId AND mr.Identi"
                        "tyId=x.IdentityId WHERE m.ConversationId"
                        "=v.ConversationId AND m.MessageId=TRY_CO"
                        "NVERT(uniqueidentifier,e.value))))"
                    )
                )
                params.append(riskLevel or "high")
                if self.operational_channels:
                    # The visible badge uses the greater of a current verified
                    # assessment and a current quoted commercial signal.
                    assessment = where.pop()
                    level = params.pop()
                    signal = (
                        " FROM crm_access.Setting sm WHERE sm.InstitutionId=? "
                        "AND JSON_VALUE(sm.Document,'$.conversation_id')=CONVERT(nvarchar(36),v.ConversationId) "
                        "AND v.State<>'closed' AND TRY_CONVERT(bigint,JSON_VALUE(sm.Document,'$.source_sequence'))="
                        "(SELECT MAX(Sequence) FROM crm.Message WHERE ConversationId=v.ConversationId AND Direction='incoming') "
                        "AND JSON_VALUE(sm.Document,'$.commercial_risk.source')='commercial_signals' "
                    )
                    higher_signal = (
                        "EXISTS(SELECT 1" + signal
                        + "AND TRY_CONVERT(int,JSON_VALUE(sm.Document,'$.commercial_risk.score'))>?)"
                    )
                    requested_signal = (
                        "EXISTS(SELECT 1" + signal
                        + "AND JSON_VALUE(sm.Document,'$.commercial_risk.level')=? AND NOT "
                        + assessment.replace("x.RiskLevel=?", "x.RiskScore>TRY_CONVERT(int,JSON_VALUE(sm.Document,'$.commercial_risk.score'))")
                        + ")"
                    )
                    where.append("((" + assessment + " AND NOT " + higher_signal + ") OR " + requested_signal + ")")
                    params.extend([level, db.institution(self.profile), {"low": 39, "medium": 69, "high": 100}[level], db.institution(self.profile), level])
            if state:
                where.append("v.State=?")
                params.append(state)
            if temperature:
                where.append(
                    "EXISTS(SELECT 1 FROM crm_channels.ConversationProfile manual"
                    " WHERE manual.ConversationId=v.ConversationId AND manual.Temperature=?)"
                )
                params.append(temperature)
            if user:
                where.append("a.UserId=?")
                params.append(user)
            if program:
                where.append("p.Program LIKE ?")
                params.append(pattern(program))
            if program_id is not None:
                where.append("p.ProgramId=?")
                params.append(program_id)
            if channel:
                if self.operational_channels:
                    if channel == "local":
                        where.append(
                            (
                                "NOT EXISTS(SELECT 1 FROM crm_channels.External"
                                "Identity WHERE ConversationId=v.ConversationId"
                                ") AND NOT EXISTS(SELECT 1 FROM crm_channels2.E"
                                "xternalIdentity WHERE ConversationId=v.Convers"
                                "ationId)"
                            )
                        )
                    else:
                        where.append(
                            (
                                "(EXISTS(SELECT 1 FROM crm_channels.ExternalIde"
                                "ntity WHERE ConversationId=v.ConversationId AN"
                                "D Channel=?) OR EXISTS(SELECT 1 FROM crm_chann"
                                "els2.ExternalIdentity ci JOIN crm_channels2.In"
                                "tegration ca ON ca.InstitutionId=ci.Institutio"
                                "nId AND ca.IntegrationId=ci.IntegrationId WHER"
                                "E ci.ConversationId=v.ConversationId AND ca.Ch"
                                "annel=?))"
                            )
                        )
                        params.extend([channel, channel])
                elif channel == "local":
                    where.append(
                        (
                            "NOT EXISTS(SELECT 1 FROM crm_channels.Ex"
                            "ternalIdentity WHERE ConversationId=v.Co"
                            "nversationId)"
                        )
                    )
                else:
                    where.append(
                        (
                            "EXISTS(SELECT 1 FROM crm_channels.Extern"
                            "alIdentity WHERE ConversationId=v.Conver"
                            "sationId AND Channel=?)"
                        )
                    )
                    params.append(channel)
            predicate = " WHERE " + " AND ".join(where)
            sla = sla_join(self.operational_channels)
            total = c.execute(
                "SELECT COUNT(*)" + BASE + (sla if queue == "sla" else "") + predicate, *params
            ).fetchval()
            channel_expression = self.inbox_channel_expression()
            items = rows(
                c.execute(
                    (
                        "SELECT v.ConversationId AS conversationI"
                        "d,p.ContactId AS id,p.Name AS name,p.Pho"
                        "ne AS phone,p.City AS city,p.Stage AS st"
                        "age,p.Tags AS tags,v.State AS state,v.Pr"
                        "iority AS priority,v.ControlMode AS mode"
                        ",v.Unread AS unread,v.UpdatedAt AS updat"
                        "edAt,u.DisplayName AS assignee,a.UserId "
                        "AS userId,"
                    )
                    + SLA_STATUS
                    + f" AS slaStatus,{channel_expression} AS channel"
                    + (self.inbox_account_columns() if area == "inbox" else "")
                    + (
                        ",(SELECT TOP(1) LEFT(m.Body,220) FROM crm.Message m"
                        " WHERE m.ConversationId=v.ConversationId"
                        " ORDER BY m.CreatedAt DESC,m.Sequence DESC) AS preview"
                        ",(SELECT Temperature FROM crm_channels.ConversationProfile"
                        " WHERE ConversationId=v.ConversationId) AS temperature"
                        ",(SELECT LeadScore FROM crm_channels.ConversationProfile"
                        " WHERE ConversationId=v.ConversationId) AS leadScore"
                        ",p.Program AS program"
                        if area == "inbox"
                        else ""
                    )
                    + (
                        ",(SELECT TOP(1) asset.Kind FROM crm_channels4.MediaAsset asset "
                        "WHERE asset.MessageId=(SELECT TOP(1) lastMessage.MessageId FROM "
                        "crm.Message lastMessage WHERE lastMessage.ConversationId=v.ConversationId "
                        "ORDER BY lastMessage.CreatedAt DESC,lastMessage.Sequence DESC) ORDER BY asset.MediaId) AS previewKind"
                        ",(SELECT TOP(1) JSON_VALUE(asset.ProviderReference,'$.durationSeconds') "
                        "FROM crm_channels4.MediaAsset asset WHERE asset.MessageId=(SELECT TOP(1) "
                        "lastMessage.MessageId FROM crm.Message lastMessage "
                        "WHERE lastMessage.ConversationId=v.ConversationId ORDER BY lastMessage.CreatedAt DESC,lastMessage.Sequence DESC) "
                        "ORDER BY asset.MediaId) AS previewDuration"
                        if area == "inbox" and self.operational_channels else ""
                    )
                    + BASE
                    + sla
                    + predicate
                    + (
                        " ORDER BY v.UpdatedAt DESC,v.Conversatio"
                        "nId OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
                    ),
                    *params,
                    offset,
                    PAGE,
                )
            )
            for item in items:
                if area == "inbox" and channel:
                    item["channel"] = channel
                if area != "inbox":
                    item["risk"] = risk(c, item["id"])
            if area == "inbox":
                self.populate_inbox_risk(c, items)
            response = {
                "items": items,
                "total": total,
                "offset": offset,
                "limit": PAGE,
                "hasMore": offset + len(items) < total,
                "revision": current_revision,
            }
            if area == "inbox":
                response["socialProfiles"] = bool(getattr(self, "operational_channels", False))
                response["unreadByChannel"] = dict(c.execute(
                    "SELECT sources.Channel,COUNT(*) FROM "
                    f"(SELECT {channel_expression} AS Channel "
                    "FROM crm.Conversation v WHERE v.Unread=1) sources GROUP BY sources.Channel"
                ).fetchall())
            return response

    def detail(self, conversation):
        with self.transaction() as c:
            thread = db.one(
                c,
                (
                    "SELECT v.ConversationId,v.ContactId,v.St"
                    "ate,v.Priority,v.ControlMode,v.Unread,v."
                    "UpdatedAt,a.UserId,u.DisplayName AS Assi"
                    "gnee,(SELECT x.Epoch FROM crm_channels.ConversationControl x "
                    "WHERE x.ConversationId=v.ConversationId) AS ControlEpoch,"
                    + SLA_STATUS + " AS SlaStatus,"
                    "CASE WHEN sp.Enabled=1 AND v.State<>'closed' THEN pending.startedAt END AS SlaStartedAt,"
                    f"CASE WHEN sp.Enabled=1 AND v.State<>'closed' THEN {SLA_DEADLINE} END AS SlaDueAt,"
                    "sp.ThresholdMinutes AS SlaThresholdMinutes"
                )
                + BASE
                + sla_join(self.operational_channels)
                + " WHERE v.ConversationId=?",
                conversation,
            )
            if not thread:
                raise HTTPException(404, "conversation_not_found")
            control_epoch = str(thread.pop("ControlEpoch") or 0)
            sla = {
                "status": thread.pop("SlaStatus"),
                "startedAt": db.utc(thread.pop("SlaStartedAt")),
                "dueAt": db.utc(thread.pop("SlaDueAt")),
                "thresholdMinutes": thread.pop("SlaThresholdMinutes"),
            }
            original = db.uid(str(thread["ContactId"]))
            canonical = primary(c, original)
            ids = members(c, canonical)
            slots = ",".join("?" for _ in ids)
            notes = rows(
                c.execute(
                    (
                        "SELECT TOP(51) n.NoteId AS id,n.Body AS "
                        "body,n.CreatedAt AS createdAt,u.DisplayN"
                        "ame AS author FROM crm_workspace.Note n "
                        "JOIN crm_access.AccessUser u ON u.Instit"
                        "utionId=n.InstitutionId AND u.UserId=n.A"
                        "uthorId WHERE n.ContactId IN ("
                    )
                    + slots
                    + ") ORDER BY n.CreatedAt DESC,n.NoteId",
                    *ids,
                )
            )
            profile = db.one(
                c,
                (
                    "SELECT LeadScore,Temperature,UpdatedAt F"
                    "ROM crm_channels.ConversationProfile WHE"
                    "RE ConversationId=?"
                ),
                conversation,
            )
            in_flight = c.execute(
                (
                    "SELECT COUNT(*) FROM crm_channels.Messag"
                    "eRoute route JOIN crm_channels.outbound_"
                    "queue q ON q.QueueId=route.QueueId JOIN "
                    "crm.Message m ON m.MessageId=route.Messa"
                    "geId WHERE m.ConversationId=? AND route."
                    "StartedAt IS NOT NULL AND route.Complete"
                    "dAt IS NULL AND q.State IN('sending','un"
                    "certain')"
                ),
                conversation,
            ).fetchval()
            return {
                "client": read_contact(c, canonical),
                "thread": {
                    k: (
                        db.utc(v)
                        if isinstance(v, datetime)
                        else bool(v)
                        if k == "Unread"
                        else db.uid(str(v))
                        if isinstance(v, UUID)
                        or k in {"ConversationId", "ContactId", "UserId"}
                        and v is not None
                        else v
                    )
                    for k, v in thread.items()
                },
                "risk": self.conversation_risk(c, canonical, conversation),
                "sla": sla,
                "inFlightOrUncertain": in_flight,
                "manual": {
                    "score": profile["LeadScore"],
                    "temperature": profile["Temperature"],
                    "asOf": db.utc(profile["UpdatedAt"]),
                    "source": "manual",
                }
                if profile
                else None,
                "members": [read_contact(c, i) for i in ids],
                "notes": notes[:50],
                "notesHasMore": len(notes) > 50,
                "revision": revision(c),
                "controlEpoch": control_epoch,
                "readOnOpen": True,
                "academicAuthority": "SIIE",
                "academicBinding": "not_bound",
            }

    def messages(self, conversation, before=None):
        if before and int(before) > 9223372036854775807:
            raise HTTPException(422, "invalid_message_cursor")
        with self.transaction() as c:
            self.exists(c, conversation)
            items = rows(
                c.execute(
                    (
                        "SELECT TOP(51) m.MessageId AS id,m.Body "
                        "AS body,m.Direction AS direction,m.Creat"
                        "edAt AS createdAt,CONVERT(varchar(20),m."
                        "Sequence) AS sequence FROM crm.Message m"
                        " WHERE m.ConversationId=? AND (? IS NULL"
                        " OR m.Sequence<?) ORDER BY m.Sequence DE"
                        "SC"
                    ),
                    conversation,
                    before,
                    before,
                )
            )
            return {
                "items": list(reversed(items[:50])),
                "hasMore": len(items) > 50,
                "before": items[49]["sequence"] if len(items) >= 50 else None,
                "revision": revision(c),
            }

    @staticmethod
    def exists(c, conversation):
        row = c.execute(
            (
                "SELECT ContactId,State,ControlMode FROM "
                "crm.Conversation WHERE ConversationId=?"
            ),
            conversation,
        ).fetchone()
        if row is None:
            raise HTTPException(404, "conversation_not_found")
        return row

    def tasks(self, status="pending", q="", user="", contact="", offset=0, anchor=""):
        with self.transaction() as c:
            if offset and not anchor:
                raise HTTPException(422, "page_anchor_required")
            if anchor and anchor != revision(c):
                raise HTTPException(409, "page_changed")
            predicate = (
                " WHERE (?='' OR t.Status=?) AND (?='' OR"
                " t.Title LIKE ?) AND (?='' OR CONVERT(va"
                "rchar(36),t.UserId)=?)"
            )
            params = [status, status, q, pattern(q), user, user]
            if contact:
                ids = members(c, contact)
                predicate += " AND v.ContactId IN (" + ",".join("?" for _ in ids) + ")"
                params += ids
            joins = (
                " FROM crm_workspace.Task t JOIN crm.Conv"
                "ersation v ON v.ConversationId=t.Convers"
                "ationId LEFT JOIN crm_access.AccessUser "
                "u ON u.InstitutionId=t.InstitutionId AND"
                " u.UserId=t.UserId JOIN crm.Contact pers"
                "on ON person.ContactId=COALESCE((SELECT "
                "TargetContactId FROM crm_workspace.Merge"
                " g WHERE g.SourceContactId=v.ContactId A"
                "ND g.Active=1),v.ContactId)"
            )
            total = c.execute("SELECT COUNT(*)" + joins + predicate, *params).fetchval()
            items = rows(
                c.execute(
                    (
                        "SELECT t.TaskId AS id,t.ConversationId A"
                        "S conversationId,t.Title AS title,t.Stat"
                        "us AS status,t.Priority AS priority,t.Du"
                        "eAt AS dueAt,t.UserId AS userId,u.Displa"
                        "yName AS assignee,t.UpdatedAt AS updated"
                        "At,person.Name AS contactName,person.Con"
                        "tactId AS contactId"
                    )
                    + joins
                    + predicate
                    + (
                        " ORDER BY t.UpdatedAt DESC,t.TaskId OFFS"
                        "ET ? ROWS FETCH NEXT ? ROWS ONLY"
                    ),
                    *params,
                    offset,
                    PAGE,
                )
            )
            return {
                "items": items,
                "total": total,
                "hasMore": offset + len(items) < total,
                "revision": revision(c),
            }

    def groups(self, contact):
        with self.transaction() as c:
            contact = primary(c, contact)
            read_contact(c, contact)
            return {
                "items": rows(
                    c.execute(
                        (
                            "SELECT m.MergeId AS id,m.SourceContactId"
                            " AS sourceContactId,m.TargetContactId AS"
                            " targetContactId,p.Name AS sourceName FR"
                            "OM crm_workspace.Merge m JOIN crm.Contac"
                            "t p ON p.ContactId=m.SourceContactId WHE"
                            "RE m.TargetContactId=? AND m.Active=1 OR"
                            "DER BY m.CreatedAt,m.MergeId"
                        ),
                        contact,
                    )
                )
            }

    def activity(self, contact, offset=0):
        with self.transaction() as c:
            ids = members(c, contact)
            read_contact(c, ids[0])
            slots = ",".join("?" for _ in ids)
            values = rows(
                c.execute(
                    (
                        "SELECT a.EventId AS id,a.Action AS actio"
                        "n,u.DisplayName AS author,a.OccurredAt A"
                        "S createdAt FROM crm_access.Audit a LEFT"
                        " JOIN crm_access.AccessUser u ON u.Insti"
                        "tutionId=a.InstitutionId AND u.UserId=a."
                        "ActorId WHERE a.InstitutionId=? AND (a.R"
                        "esourceRef IN ("
                    )
                    + slots
                    + (
                        ") OR EXISTS(SELECT 1 FROM crm.Conversati"
                        "on v WHERE CONVERT(varchar(36),v.Convers"
                        "ationId)=a.ResourceRef AND v.ContactId I"
                        "N ("
                    )
                    + slots
                    + (
                        ")) OR EXISTS(SELECT 1 FROM crm_workspace"
                        ".Task t JOIN crm.Conversation v ON v.Con"
                        "versationId=t.ConversationId WHERE CONVE"
                        "RT(varchar(36),t.TaskId)=a.ResourceRef A"
                        "ND v.ContactId IN ("
                    )
                    + slots
                    + (
                        ")) OR EXISTS(SELECT 1 FROM crm_workspace"
                        ".Merge m WHERE CONVERT(varchar(36),m.Mer"
                        "geId)=a.ResourceRef AND m.TargetContactI"
                        "d=?)) ORDER BY a.OccurredAt DESC,a.Event"
                        "Id DESC OFFSET ? ROWS FETCH NEXT 26 ROWS"
                        " ONLY"
                    ),
                    db.institution(self.profile),
                    *ids,
                    *ids,
                    *ids,
                    ids[0],
                    offset,
                )
            )
            return {"items": values[:25], "hasMore": len(values) > 25}

    def notes(self, contact, offset=0):
        with self.transaction() as c:
            ids = members(c, contact)
            read_contact(c, ids[0])
            slots = ",".join("?" for _ in ids)
            values = rows(
                c.execute(
                    (
                        "SELECT n.NoteId AS id,n.Body AS body,n.C"
                        "reatedAt AS createdAt,u.DisplayName AS a"
                        "uthor FROM crm_workspace.Note n JOIN crm"
                        "_access.AccessUser u ON u.InstitutionId="
                        "n.InstitutionId AND u.UserId=n.AuthorId "
                        "WHERE n.ContactId IN ("
                    )
                    + slots
                    + (
                        ") ORDER BY n.CreatedAt DESC,n.NoteId OFF"
                        "SET ? ROWS FETCH NEXT 26 ROWS ONLY"
                    ),
                    *ids,
                    offset,
                )
            )
            return {"items": values[:25], "hasMore": len(values) > 25}

    def write(self, action, resource, body):
        if action != "policy":
            resource = db.uid(resource)
        permission = (
            "settings.crm.write"
            if action == "policy"
            else "inbox.write"
            if action in {"conversation", "control", "message", "read"}
            else "crm.write"
        )
        with transaction(
            self.profile,
            True,
            permission=permission,
            recent=action in {"merge", "undo"},
        ) as c:
            actor = authorize(c, self.profile, request_authority.get(), permission)
            actor_id = db.uid(str(actor["UserId"]))
            digest, prior = db.replay(
                c,
                self.profile,
                actor_id,
                body.operationId,
                "workspace." + action,
                resource,
                body.model_dump(mode="json"),
            )
            if prior is not None:
                return prior
            # Scoped commands validate the current thread in apply.
            if action not in {"message", "control", "read"} and body.revision != revision(c):
                raise HTTPException(409, "revision_conflict")
            if self.profile.ticket.get('version') in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'} and action in {'create','contact'}:
                from app.institutional.campaign_runtime import observe_contact
                observe_contact(c,self.profile,resource)
            result = self.apply(c, action, resource, body, actor_id)
            if self.profile.ticket.get('version') in {'cbn-institutional-ads-p9-v1', 'cbn-institutional-campaign-p8-v1', 'cbn-institutional-learning-p10-v1', 'cbn-institutional-operations-p11-v1'} and action in {'create','contact'}:
                observe_contact(c,self.profile,resource)
            c.execute(
                ("UPDATE crm_workspace.State SET Revision=Revision+1 WHERE StateId=1")
            )
            result = dict(result, revision=revision(c))
            db.record_operation(
                c,
                self.profile,
                actor_id,
                body.operationId,
                "workspace." + action,
                resource,
                digest,
                result,
            )
            db.audit(
                c,
                self.profile,
                actor_id,
                "workspace." + action,
                resource,
                revision=int(result["revision"]),
            )
            return result

    def apply(self, c, action, resource, body, actor):
        if action == "read":
            self.exists(c, resource)
            unread = mark_read(c, resource, body.readThrough)
            c.execute(
                "UPDATE crm.Conversation SET Unread=? WHERE ConversationId=?",
                unread,
                resource,
            )
            return {"conversationId": resource, "unread": unread}
        if action == "message" and body.mediaId:
            raise HTTPException(409, "media_transport_unavailable")
        if action == "policy":
            c.execute(
                (
                    "IF EXISTS(SELECT 1 FROM crm_inbox.SlaPol"
                    "icy WHERE PolicyId=1) UPDATE crm_inbox.S"
                    "laPolicy SET Enabled=?,ThresholdMinutes="
                    "?,UpdatedAt=SYSUTCDATETIME() WHERE Polic"
                    "yId=1 ELSE INSERT crm_inbox.SlaPolicy(Po"
                    "licyId,Enabled,ThresholdMinutes) VALUES("
                    "1,?,?)"
                ),
                body.enabled,
                body.thresholdMinutes,
                body.enabled,
                body.thresholdMinutes,
            )
            return {
                "configured": True,
                "enabled": body.enabled,
                "thresholdMinutes": body.thresholdMinutes,
            }
        if action in {"create", "contact"}:
            contact = body.client
            current = None if action == "create" else read_contact(c, resource)
            if contact.id != resource or primary(c, resource) != resource:
                raise HTTPException(409, "canonical_contact_required")
            previous_program = (
                (current.get("programId"), current.get("program"))
                if current
                else (None, "")
            )
            if (
                (contact.programId, contact.program) != previous_program
                or contact.institutionalProfile is not None
                and (
                    not current
                    or contact.institutionalProfile.model_dump()
                    != current.get("institutionalProfile")
                )
            ):
                raise HTTPException(422, "academic_mapping_not_bound")
            validate_contact(c, contact, current, foundation=True)
            if current is not None:
                from app.institutional.sales_contact import mark_manual
                mark_manual(c, self.profile, resource, current, contact)
            values = [
                getattr(contact, k)
                if k != "customValues"
                else json.dumps(contact.customValues, ensure_ascii=False)
                for k in CONTACT_KEYS[1:]
            ]
            if action == "create":
                c.execute(
                    "INSERT crm.Contact("
                    + CONTACT_COLUMNS
                    + ") VALUES("
                    + ",".join("?" for _ in CONTACT_KEYS)
                    + ")",
                    resource,
                    *values,
                )
                conversation = str(uuid4())
                c.execute(
                    (
                        "INSERT crm.Conversation(ConversationId,C"
                        "ontactId,State,Priority,Assignee,Control"
                        "Mode,Unread) VALUES(?,?,'open','normal',"
                        "NULL,'ai',0)"
                    ),
                    conversation,
                    resource,
                )
            else:
                c.execute(
                    "UPDATE crm.Contact SET "
                    + ",".join(key + "=?" for key in CONTACT_COLUMNS.split(",")[1:])
                    + " WHERE ContactId=?",
                    *values,
                    resource,
                )
                c.execute(
                    (
                        "UPDATE crm.Conversation SET UpdatedAt=SY"
                        "SUTCDATETIME() WHERE ContactId=?"
                    ),
                    resource,
                )
                conversation = str(
                    c.execute(
                        (
                            "SELECT ConversationId FROM crm.Conversat"
                            "ion WHERE ContactId=?"
                        ),
                        resource,
                    ).fetchval()
                ).lower()
            return {"contactId": resource, "conversationId": conversation}
        if action in {"conversation", "control", "message", "manual"}:
            original = self.exists(c, resource)
            if action == "control":
                if original[1] == "closed":
                    raise HTTPException(409, "conversation_closed")
                epoch = c.execute(
                    "SELECT Epoch FROM crm_channels.ConversationControl WHERE ConversationId=?",
                    resource,
                ).fetchval()
                if str(epoch or 0) != body.expectedEpoch:
                    raise HTTPException(409, "conversation_control_changed")
                if original[2] != body.mode:
                    change_control(c, resource, original[2], body.mode)
                    c.execute(
                        "UPDATE crm.Conversation SET ControlMode=?,UpdatedAt=SYSUTCDATETIME() "
                        "WHERE ConversationId=?",
                        body.mode,
                        resource,
                    )
            elif action == "conversation":
                active_user(c, self.profile, body.userId)
                change_control(c, resource, original[2], body.mode)
                unread = (
                    body.unread
                    if body.unread
                    else mark_read(c, resource, body.readThrough)
                )
                c.execute(
                    (
                        "UPDATE crm.Conversation SET State=?,Prio"
                        "rity=?,ControlMode=?,Unread=?,Assignee=?"
                        ",UpdatedAt=SYSUTCDATETIME() WHERE Conver"
                        "sationId=?"
                    ),
                    body.state,
                    body.priority,
                    body.mode,
                    unread,
                    body.userId,
                    resource,
                )
                c.execute(
                    "UPDATE crm_workspace.Assignment SET UserId=?,UpdatedAt=SYSUTCDATETIME() "
                    "WHERE ConversationId=?",
                    body.userId,
                    resource,
                )
                if c.rowcount == 0:
                    c.execute(
                        "INSERT crm_workspace.Assignment(ConversationId,InstitutionId,UserId) VALUES(?,?,?)",
                        resource,
                        db.institution(self.profile),
                        body.userId,
                    )
            elif action == "manual":
                save_assessment(c, resource, body.score, body.temperature)
            else:
                if original[1] == "closed" or original[2] != "human":
                    raise HTTPException(409, "human_open_conversation_required")
                if c.execute(
                    (
                        "SELECT 1 FROM crm_channels.ExternalIdent"
                        "ity WHERE ConversationId=?"
                    ),
                    resource,
                ).fetchone():
                    raise HTTPException(409, "provider_delivery_not_available")
                c.execute(
                    (
                        "INSERT crm.Message(MessageId,Conversatio"
                        "nId,Body,Direction) VALUES(?,?,?,'outgoi"
                        "ng')"
                    ),
                    str(uuid4()),
                    resource,
                    body.body,
                )
                c.execute(
                    (
                        "UPDATE crm.Conversation SET UpdatedAt=SY"
                        "SUTCDATETIME() WHERE ConversationId=?"
                    ),
                    resource,
                )
            return {"conversationId": resource}
        if action == "note":
            contact = primary(c, resource)
            read_contact(c, contact)
            c.execute(
                (
                    "INSERT crm_workspace.Note(NoteId,Contact"
                    "Id,InstitutionId,AuthorId,Body) VALUES(?"
                    ",?,?,?,?)"
                ),
                resource_id := str(uuid4()),
                contact,
                db.institution(self.profile),
                actor,
                body.body,
            )
            return {"noteId": resource_id, "contactId": contact}
        if action == "task":
            self.exists(c, body.conversationId)
            active_user(c, self.profile, body.userId)
            due = (
                datetime.fromisoformat(body.dueAt).replace(tzinfo=None)
                if body.dueAt
                else None
            )
            found = c.execute(
                ("SELECT ConversationId FROM crm_workspace.Task WHERE TaskId=?"),
                resource,
            ).fetchone()
            if found and db.uid(str(found[0])) != db.uid(body.conversationId):
                raise HTTPException(409, "task_conversation_immutable")
            if found:
                c.execute(
                    (
                        "UPDATE crm_workspace.Task SET UserId=?,T"
                        "itle=?,Status=?,Priority=?,DueAt=?,Updat"
                        "edAt=SYSUTCDATETIME() WHERE TaskId=?"
                    ),
                    body.userId,
                    body.title,
                    body.status,
                    body.priority,
                    due,
                    resource,
                )
            else:
                c.execute(
                    (
                        "INSERT crm_workspace.Task(TaskId,Institu"
                        "tionId,ConversationId,UserId,Title,Statu"
                        "s,Priority,DueAt) VALUES(?,?,?,?,?,?,?,?"
                        ")"
                    ),
                    resource,
                    db.institution(self.profile),
                    body.conversationId,
                    body.userId,
                    body.title,
                    body.status,
                    body.priority,
                    due,
                )
            return {"taskId": resource}
        if action == "merge":
            source, target = db.uid(body.sourceContactId), db.uid(body.targetContactId)
            if source == target:
                raise HTTPException(422, "distinct_contacts_required")
            for item in (source, target):
                read_contact(c, item)
            if c.execute(
                (
                    "SELECT 1 FROM crm_workspace.Merge WHERE "
                    "Active=1 AND (SourceContactId IN(?,?) OR"
                    " TargetContactId=?)"
                ),
                source,
                target,
                source,
            ).fetchone():
                raise HTTPException(409, "merge_group_changed")
            if (
                c.execute(
                    (
                        "SELECT COUNT(*) FROM crm_workspace.Merge"
                        " WHERE Active=1 AND TargetContactId=?"
                    ),
                    target,
                ).fetchval()
                >= 99
            ):
                raise HTTPException(409, "merge_group_limit")
            c.execute(
                (
                    "INSERT crm_workspace.Merge(MergeId,Sourc"
                    "eContactId,TargetContactId,Active) VALUE"
                    "S(?,?,?,1)"
                ),
                resource,
                source,
                target,
            )
            return {
                "mergeId": resource,
                "primaryContactId": target,
                "original_records_preserved": True,
            }
        if action == "undo":
            if not c.execute(
                ("SELECT 1 FROM crm_workspace.Merge WHERE MergeId=? AND Active=1"),
                resource,
            ).fetchone():
                raise HTTPException(409, "merge_not_active")
            c.execute(
                (
                    "UPDATE crm_workspace.Merge SET Active=0,"
                    "ReversedAt=SYSUTCDATETIME() WHERE MergeI"
                    "d=?"
                ),
                resource,
            )
            return {"mergeId": resource, "original_records_preserved": True}
        raise HTTPException(404, "resource_not_found")


def install(app, settings, workspace=None):
    workspace = workspace or Workspace(settings)
    prefix = "/api/institution/workspace"

    @app.get(prefix + "/policy")
    def policy():
        return workspace.policy()

    @app.put(prefix + "/policy")
    def policy_write(body: PolicyWrite):
        return workspace.write("policy", "sla", body)

    @app.get(prefix + "/clients")
    def clients(
        q: str = Query("", max_length=200),
        stage: str = Query("", max_length=60),
        tag: str = Query("", max_length=1000),
        city: str = Query("", max_length=100),
        contactType: str = Query("", max_length=100),
        program: str = Query("", max_length=200),
        programId: int | None = Query(None, ge=-2147483648, le=2147483647),
        offset: int = Query(0, ge=0, le=1000000),
        anchor: str = Query("", pattern=r"^([0-9]{1,19})?$"),
    ):
        return workspace.listing(
            "clients",
            q=q,
            stage=stage,
            tag=tag,
            city=city,
            contactType=contactType,
            program=program,
            program_id=programId,
            offset=offset,
            anchor=anchor,
        )

    @app.get(prefix + "/inbox")
    def inbox(
        q: str = Query("", max_length=200),
        stage: str = Query("", max_length=60),
        queue: Literal[
            "all",
            "unread",
            "mine",
            "unassigned",
            "human",
            "ai",
            "open",
            "waiting",
            "closed",
            "hot",
            "churn",
            "sla",
        ] = "all",
        user: str = Query("", max_length=36),
        channel: Literal[
            "", "local", "whatsapp", "facebook", "messenger", "instagram", "tiktok"
        ] = "",
        state: Literal["", "open", "waiting", "closed"] = "",
        temperature: Literal["", "cold", "warm", "hot"] = "",
        riskLevel: Literal["", "low", "medium", "high"] = "",
        offset: int = Query(0, ge=0, le=1000000),
        anchor: str = Query("", pattern=r"^([0-9]{1,19})?$"),
        afterRevision: str = Query("", pattern=r"^([0-9]{1,20})?$"),
    ):
        if user:
            db.uid(user)
        return workspace.listing(
            "inbox",
            q=q,
            stage=stage,
            queue=queue,
            user=user,
            channel=channel,
            state=state,
            temperature=temperature,
            riskLevel=riskLevel,
            after_revision=afterRevision,
            offset=offset,
            anchor=anchor,
        )

    @app.get(prefix + "/directory")
    def directory(
        q: str = Query("", max_length=100), offset: int = Query(0, ge=0, le=1000000)
    ):
        return workspace.directory(q, offset)

    @app.get(prefix + "/inbox/directory")
    def inbox_directory(
        q: str = Query("", max_length=100), offset: int = Query(0, ge=0, le=1000000)
    ):
        return workspace.directory(q, offset)

    @app.get(prefix + "/conversations/{conversation_id}")
    def detail(conversation_id: Identifier):
        return workspace.detail(conversation_id)

    @app.get(prefix + "/inbox/{conversation_id}/detail")
    def inbox_detail(conversation_id: Identifier):
        return workspace.detail(conversation_id)

    @app.get(prefix + "/conversations/{conversation_id}/messages")
    def messages(
        conversation_id: Identifier,
        before: str | None = Query(None, pattern=r"^[1-9][0-9]{0,18}$"),
    ):
        return workspace.messages(conversation_id, before)

    if getattr(workspace, "operational_channels", False):
        @app.get(prefix + "/conversations/{conversation_id}/social-profile")
        def social_profile(conversation_id: Identifier):
            return workspace.social_profile(conversation_id)

    @app.get(prefix + "/tasks")
    def tasks(
        status: Literal["", "pending", "completed", "cancelled"] = "pending",
        q: str = Query("", max_length=200),
        user: str = Query("", max_length=36),
        contact: str = Query("", max_length=36),
        offset: int = Query(0, ge=0, le=1000000),
        anchor: str = Query("", pattern=r"^([0-9]{1,19})?$"),
    ):
        if user:
            db.uid(user)
        if contact:
            db.uid(contact)
        return workspace.tasks(status, q, user, contact, offset, anchor)

    @app.get(prefix + "/clients/{contact_id}/groups")
    def groups(contact_id: Identifier):
        return workspace.groups(contact_id)

    @app.get(prefix + "/clients/{contact_id}/activity")
    def activity(contact_id: Identifier, offset: int = Query(0, ge=0, le=1000000)):
        return workspace.activity(contact_id, offset)

    @app.get(prefix + "/clients/{contact_id}/notes")
    def notes(contact_id: Identifier, offset: int = Query(0, ge=0, le=1000000)):
        return workspace.notes(contact_id, offset)

    @app.post(prefix + "/clients/{contact_id}")
    def create(contact_id: Identifier, body: ContactWrite):
        return workspace.write("create", contact_id, body)

    @app.put(prefix + "/clients/{contact_id}")
    def edit(contact_id: Identifier, body: ContactWrite):
        return workspace.write("contact", contact_id, body)

    @app.put(prefix + "/conversations/{conversation_id}")
    def conversation(conversation_id: Identifier, body: ConversationWrite):
        return workspace.write("conversation", conversation_id, body)

    @app.put(prefix + "/conversations/{conversation_id}/control")
    def set_control(conversation_id: Identifier, body: ControlWrite):
        return workspace.write("control", conversation_id, body)

    @app.put(prefix + "/conversations/{conversation_id}/read")
    def read_conversation(conversation_id: Identifier, body: ConversationRead):
        return workspace.write("read", conversation_id, body)

    @app.post(prefix + "/conversations/{conversation_id}/messages")
    def message(conversation_id: Identifier, body: MessageWrite):
        result = workspace.write("message", conversation_id, body)
        worker = getattr(app.state, "channel_workers", None)
        if worker is not None:
            worker.dispatch_wake.set()
        return result

    @app.put(prefix + "/conversations/{conversation_id}/manual")
    def manual(conversation_id: Identifier, body: ManualWrite):
        return workspace.write("manual", conversation_id, body)

    @app.post(prefix + "/clients/{contact_id}/notes")
    def note(contact_id: Identifier, body: NoteWrite):
        return workspace.write("note", contact_id, body)

    @app.put(prefix + "/tasks/{task_id}")
    def task(task_id: Identifier, body: TaskWrite):
        return workspace.write("task", task_id, body)

    @app.post(prefix + "/merges/{merge_id}")
    def merge(merge_id: Identifier, body: MergeWrite):
        return workspace.write("merge", merge_id, body)

    @app.post(prefix + "/merges/{merge_id}/undo")
    def undo(merge_id: Identifier, body: Command):
        return workspace.write("undo", merge_id, body)
