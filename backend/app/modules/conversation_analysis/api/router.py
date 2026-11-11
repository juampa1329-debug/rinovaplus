"""Isolated SQL analysis consumer; inference is always outside transactions."""

import hashlib
import json
from uuid import uuid4

from fastapi import HTTPException

from app.modules.conversation_analysis.domain.models import PROMPT_VERSION, redact
from app.modules.conversation_events.api.router import EVENT_SHAPE, ConversationEvents, source_queries
from app.modules.inbox.application.service import rows

ANALYSIS_SHAPE = EVENT_SHAPE.replace("N'crm_events'", "N'crm_analysis'").replace(
    "N'crm_events.shape'", "N'crm_analysis.shape'"
)
POLICY_SELECT = (
    "SELECT Revision AS revision,Enabled AS enabled,Provider AS provi"
    "der,Model AS model,\n InputScope AS inputScope,ScopeAccepted AS s"
    "copeAccepted,DailyRequests AS dailyRequests,\n DailyOutputTokens "
    "AS dailyOutputTokens,OutputTokens AS outputTokens FROM crm_analy"
    "sis.Policy WHERE PolicyId=1"
)
STATE_SELECT = (
    "SELECT ConversationId AS id,Revision AS revision,Generation AS g"
    "eneration,Binding AS binding,\n ContextGeneration AS contextGener"
    "ation,ContextJson AS contextJson,AnalyzedAt AS analyzedAt,\n Cont"
    "extProvider AS provider,ContextModel AS model,ContextPromptVersi"
    "on AS promptVersion,ContextPolicyRevision AS policyRevision,\n Fi"
    "ngerprint AS fingerprint,Status AS status,ErrorCode AS errorCode"
    " FROM crm_analysis.ConversationState WHERE ConversationId=?"
)
UNCONSUMED = (
    "NOT EXISTS(SELECT 1 FROM crm_analysis.Receipt r WHERE r.EventId="
    "e.EventId\n AND r.ConversationId=e.ConversationId AND r.Generatio"
    "n=s.Generation)"
)
OWNER = (
    "ConversationId=? AND LeaseToken=? AND Status='processing' AND Le"
    "aseUntil>SYSUTCDATETIME() AND Revision=?"
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


class ConversationAnalysis:
    def __init__(self, workspace):
        self.workspace = workspace

    @staticmethod
    def verify(cursor):
        ConversationEvents.verify(cursor)
        version = cursor.execute(
            (
                "SELECT CONVERT(nvarchar(128),value) FROM sys.extende"
                "d_properties WHERE class=3 AND major_id=SCHEMA_ID(N'"
                "crm_analysis') AND name=N'crm_analysis.contract'"
            )
        ).fetchval()
        if version != "analysis-v1" or not cursor.execute(ANALYSIS_SHAPE).fetchval():
            raise HTTPException(503, "analysis_not_installed_or_changed")

    @staticmethod
    def policy(cursor):
        found = rows(cursor.execute(POLICY_SELECT))
        if found:
            found[0]["revision"] = str(found[0]["revision"])
        return found[0] if found else None

    @staticmethod
    def identity(cursor, conversation):
        row = cursor.execute(
            (
                "SELECT p.Name,p.Phone FROM crm.Contact p JOIN crm.Co"
                "nversation c ON c.ContactId=p.ContactId WHERE c.Conv"
                "ersationId=?"
            ),
            conversation,
        ).fetchone()
        if not row:
            raise HTTPException(404, "conversation_not_found")
        from app.modules.contacts.application.merge import privacy_scope
        from app.modules.contacts.api.router import private_identifiers

        return [
            row[0],
            row[1],
            *str(row[0]).split(),
            *private_identifiers(cursor, conversation),
            *privacy_scope(
                cursor,
                str(
                    cursor.execute(
                        "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
                        conversation,
                    ).fetchone()[0]
                ),
            ),
        ]

    @staticmethod
    def fingerprint(cursor, conversation):
        # ponytail: reference scans fit local volume; measure before indexing.
        sources = []
        for source in source_queries(cursor).values():
            sources.append(
                sorted(
                    str(tuple(row))
                    for row in cursor.execute(
                        "SELECT SourceId,SourceRevision FROM ("
                        + source
                        + ") s WHERE ConversationId=?",
                        conversation,
                    ).fetchall()
                )
            )
        sources.append(
            sorted(
                str(tuple(row))
                for row in cursor.execute(
                    (
                        "SELECT FeedbackId,SourceRevision FROM crm_an"
                        "alysis.Feedback WHERE ConversationId=?"
                    ),
                    conversation,
                ).fetchall()
            )
        )
        from app.modules.contacts.application.merge import membership

        contact = str(
            cursor.execute(
                "SELECT ContactId FROM crm.Conversation WHERE ConversationId=?",
                conversation,
            ).fetchone()[0]
        )
        sources.append(
            [
                membership(cursor, contact),
                ConversationAnalysis.identity(cursor, conversation),
            ]
        )
        return digest(sources)

    def configuration(self):
        with self.workspace.transaction() as c:
            self.verify(c)
            policy = self.policy(c)
            usage = rows(
                c.execute(
                    (
                        "SELECT COUNT_BIG(*) AS requests,COALESCE(SUM"
                        "(CONVERT(bigint,ReservedOutputTokens)),0) AS"
                        " reservedOutputTokens FROM crm_analysis.Atte"
                        "mpt WHERE CreatedAt>=CONVERT(date,SYSUTCDATE"
                        "TIME())"
                    )
                )
            )[0]
            coverage = rows(
                c.execute(
                    (
                        "SELECT COUNT_BIG(*) AS conversations,\n          "
                        "   SUM(CASE WHEN s.ContextJson IS NOT NULL THEN "
                        "1 ELSE 0 END) AS withContext,\n             SUM(C"
                        "ASE WHEN s.Status='processing' THEN 1 ELSE 0 END"
                        ") AS processing,\n             SUM(CASE WHEN s.St"
                        "atus='failed' THEN 1 ELSE 0 END) AS failed\n     "
                        "        FROM crm.Conversation c LEFT JOIN crm_an"
                        "alysis.ConversationState s ON s.ConversationId=c"
                        ".ConversationId"
                    )
                )
            )[0]
            return {
                "revision": policy["revision"] if policy else "0",
                "policy": policy,
                "usage": usage,
                "coverage": coverage,
            }

    @staticmethod
    def coverage(cursor, conversation, generation):
        total = cursor.execute(
            "SELECT COUNT_BIG(*) FROM crm.Message WHERE ConversationId=?", conversation
        ).fetchval()
        covered = cursor.execute(
            (
                "SELECT COUNT_BIG(*) FROM crm_analysis.Receipt r JOIN"
                " crm_events.Event e ON e.EventId=r.EventId WHERE r.C"
                "onversationId=? AND r.Generation=? AND e.SourceKind="
                "'message'"
            ),
            conversation,
            generation,
        ).fetchval()
        pending = cursor.execute(
            (
                "SELECT COUNT_BIG(*) FROM crm_events.Event e WHERE e."
                "ConversationId=? AND NOT EXISTS(SELECT 1 FROM crm_an"
                "alysis.Receipt r WHERE r.EventId=e.EventId AND r.Con"
                "versationId=e.ConversationId AND r.Generation=?)"
            ),
            conversation,
            generation,
        ).fetchval()
        feedback = cursor.execute(
            (
                "SELECT COUNT_BIG(*) FROM crm_analysis.Feedback WHERE"
                " ConversationId=? AND ConsumedGeneration<?"
            ),
            conversation,
            generation,
        ).fetchval()
        return {
            "totalMessages": int(total),
            "coveredMessages": int(covered),
            "pendingReferences": int(pending + feedback),
        }

    @staticmethod
    def replay(cursor, operation_id, action, fingerprint):
        row = cursor.execute(
            (
                "SELECT Action,RequestHash,ResponseJson FROM crm_anal"
                "ysis.Operation WHERE OperationId=?"
            ),
            operation_id,
        ).fetchone()
        if row:
            if row[0] != action or row[1] != fingerprint:
                raise HTTPException(409, "operation_id_conflict")
            return json.loads(row[2])
        return None

    @staticmethod
    def record(cursor, operation_id, action, fingerprint, result):
        cursor.execute(
            (
                "INSERT crm_analysis.Operation(OperationId,Action,Req"
                "uestHash,ResponseJson,CreatedAt) VALUES(?,?,?,?,SYSU"
                "TCDATETIME())"
            ),
            operation_id,
            action,
            fingerprint,
            json.dumps(result),
        )
        return result

    def save_policy(self, body, validate=None):
        values = body.model_dump(exclude={"operationId", "expectedRevision"})
        fingerprint = digest(values)
        with self.workspace.transaction(write=True) as c:
            self.verify(c)
            replay = self.replay(c, body.operationId, "policy", fingerprint)
            if replay is not None:
                return replay
            current = self.policy(c)
            revision = current["revision"] if current else "0"
            if revision != body.expectedRevision:
                raise HTTPException(409, "analysis_policy_conflict")
            if validate:
                validate()
            next_revision = int(revision) + 1
            args = (
                next_revision,
                body.enabled,
                body.provider,
                body.model,
                body.inputScope,
                body.scopeAccepted,
                body.dailyRequests,
                body.dailyOutputTokens,
                body.outputTokens,
            )
            if current:
                c.execute(
                    (
                        "UPDATE crm_analysis.Policy SET Revision=?,En"
                        "abled=?,Provider=?,Model=?,InputScope=?,Scop"
                        "eAccepted=?,DailyRequests=?,DailyOutputToken"
                        "s=?,OutputTokens=?,UpdatedAt=SYSUTCDATETIME("
                        ") WHERE PolicyId=1"
                    ),
                    *args,
                )
            else:
                c.execute(
                    (
                        "INSERT crm_analysis.Policy(PolicyId,Revision"
                        ",Enabled,Provider,Model,InputScope,ScopeAcce"
                        "pted,DailyRequests,DailyOutputTokens,OutputT"
                        "okens,UpdatedAt) VALUES(1,?,?,?,?,?,?,?,?,?,"
                        "SYSUTCDATETIME())"
                    ),
                    *args,
                )
            return self.record(
                c,
                body.operationId,
                "policy",
                fingerprint,
                {"revision": str(next_revision)},
            )

    def feedback(self, conversation, body):
        fingerprint = digest([conversation, body.model_dump(exclude={"operationId"})])
        with self.workspace.transaction(write=True) as c:
            self.verify(c)
            replay = self.replay(c, body.operationId, "feedback", fingerprint)
            if replay is not None:
                return replay
            state = rows(c.execute(STATE_SELECT, conversation))
            if not state or not state[0]["contextJson"]:
                raise HTTPException(409, "analysis_required_for_feedback")
            if str(state[0]["revision"]) != body.expectedRevision:
                raise HTTPException(409, "analysis_revision_conflict")
            text = redact(body.text, self.identity(c, conversation))
            c.execute(
                (
                    "INSERT crm_analysis.Feedback(FeedbackId,Conversa"
                    "tionId,SourceRevision,Text,CreatedAt) VALUES(?,?"
                    ",?,?,SYSUTCDATETIME())"
                ),
                body.operationId,
                conversation,
                int(body.expectedRevision),
                text,
            )
            c.execute(
                (
                    "UPDATE crm_analysis.ConversationState SET Revisi"
                    "on=Revision+1,Status='pending',Failures=0,LeaseT"
                    "oken=NULL,LeaseUntil=NULL,NextAttemptAt=SYSUTCDA"
                    "TETIME() WHERE ConversationId=?"
                ),
                conversation,
            )
            return self.record(
                c,
                body.operationId,
                "feedback",
                fingerprint,
                {"revision": str(int(body.expectedRevision) + 1)},
            )

    def retry(self, operation_id):
        with self.workspace.transaction(write=True) as c:
            self.verify(c)
            replay = self.replay(c, operation_id, "retry", digest("retry"))
            if replay is not None:
                return replay
            c.execute(
                (
                    "UPDATE crm_analysis.ConversationState SET Status"
                    "='pending',Failures=0,ErrorCode=NULL,NextAttempt"
                    "At=SYSUTCDATETIME(),Revision=Revision+1 WHERE Co"
                    "nversationId IN(SELECT TOP(25) ConversationId FR"
                    "OM crm_analysis.ConversationState WHERE Status='"
                    "failed' ORDER BY ConversationId)"
                )
            )
            return self.record(
                c, operation_id, "retry", digest("retry"), {"retried": c.rowcount}
            )

    def conversation(self, conversation, binding=None):
        with self.workspace.transaction() as c:
            self.verify(c)
            known = self.identity(c, conversation)
            policy = self.policy(c)
            found = rows(c.execute(STATE_SELECT, conversation))
            state = found[0] if found else None
            context = (
                json.loads(state["contextJson"])
                if state and state["contextJson"]
                else None
            )
            if context:
                for claims in context.values():
                    for claim in claims:
                        claim["text"] = redact(claim["text"], known)
            coverage = self.coverage(
                c, conversation, state["generation"] if state else 1
            )
            stale = bool(
                state
                and (
                    state["binding"] != binding
                    or state["fingerprint"] != self.fingerprint(c, conversation)
                    or state["contextGeneration"] != state["generation"]
                )
            )
            partial = (
                coverage["coveredMessages"] < coverage["totalMessages"]
                or coverage["pendingReferences"] > 0
            )
            stale = stale or bool(context and partial)
            evidence = []
            if context:
                ids = list(
                    dict.fromkeys(
                        ref
                        for claims in context.values()
                        for claim in claims
                        for ref in claim["evidenceIds"]
                    )
                )
                for identifier in ids:
                    row = rows(
                        c.execute(
                            (
                                "SELECT MessageId AS id,Direction AS "
                                "direction,CreatedAt AS createdAt FRO"
                                "M crm.Message WHERE MessageId=? AND "
                                "ConversationId=?"
                            ),
                            identifier,
                            conversation,
                        )
                    )
                    if not row:
                        row = rows(
                            c.execute(
                                (
                                    "SELECT FeedbackId AS id,'human_f"
                                    "eedback' AS direction,CreatedAt "
                                    "AS createdAt FROM crm_analysis.F"
                                    "eedback WHERE FeedbackId=? AND C"
                                    "onversationId=?"
                                ),
                                identifier,
                                conversation,
                            )
                        )
                    evidence.extend(row)
            feedback = rows(
                c.execute(
                    (
                        "SELECT TOP(20) FeedbackId AS id,Text AS text"
                        ",SourceRevision AS sourceRevision,CreatedAt "
                        "AS createdAt FROM crm_analysis.Feedback WHER"
                        "E ConversationId=? ORDER BY CreatedAt DESC,F"
                        "eedbackId"
                    ),
                    conversation,
                )
            )
            for item in feedback:
                item["text"] = redact(item["text"], known)
            return {
                "revision": str(state["revision"]) if state else "0",
                "status": state["status"]
                if state
                else "not_configured"
                if not policy
                else "pending",
                "context": context,
                "stale": stale,
                "partial": partial,
                **coverage,
                "analyzedAt": state["analyzedAt"] if state else None,
                "errorCode": state["errorCode"] if state else None,
                "enabled": bool(policy and policy["enabled"]),
                "evidence": evidence,
                "feedback": feedback,
                "provenance": {
                    key: state[key]
                    for key in [
                        "provider",
                        "model",
                        "promptVersion",
                        "policyRevision",
                        "contextGeneration",
                    ]
                }
                if context
                else None,
            }

    def reserve(self, binding):
        with self.workspace.transaction(write=True) as c:
            self.verify(c)
            policy = self.policy(c)
            if (
                not policy
                or not policy["enabled"]
                or not binding.startswith(policy["revision"] + ":")
            ):
                return None
            c.execute(
                (
                    "INSERT crm_analysis.ConversationState(Conversati"
                    "onId,Revision,Generation,Binding,Status,Failures"
                    ",NextAttemptAt) SELECT ConversationId,0,1,?,'pen"
                    "ding',0,DATEADD(second,5,SYSUTCDATETIME()) FROM "
                    "crm.Conversation x WHERE NOT EXISTS(SELECT 1 FRO"
                    "M crm_analysis.ConversationState s WHERE s.Conve"
                    "rsationId=x.ConversationId)"
                ),
                binding,
            )
            c.execute(
                (
                    "UPDATE crm_analysis.ConversationState SET Genera"
                    "tion=Generation+1,Binding=?,Revision=Revision+1,"
                    "Status='pending',Failures=0,LeaseToken=NULL,Leas"
                    "eUntil=NULL,NextAttemptAt=DATEADD(second,5,SYSUT"
                    "CDATETIME()) WHERE Binding<>?"
                ),
                binding,
                binding,
            )
            c.execute(
                (
                    "UPDATE crm_analysis.Attempt SET Status='expired'"
                    ",CompletedAt=SYSUTCDATETIME(),ErrorCode='lease_e"
                    "xpired' WHERE Status='reserved' AND CreatedAt<DA"
                    "TEADD(second,-60,SYSUTCDATETIME())"
                )
            )
            c.execute(
                (
                    "UPDATE crm_analysis.ConversationState SET Status"
                    "=CASE WHEN Failures>=3 THEN 'failed' ELSE 'pendi"
                    "ng' END,LeaseToken=NULL,LeaseUntil=NULL,ErrorCod"
                    "e='lease_expired' WHERE Status='processing' AND "
                    "LeaseUntil<=SYSUTCDATETIME()"
                )
            )
            state = rows(
                c.execute(
                    (
                        "SELECT TOP(1) s.ConversationId AS id,s.Revis"
                        "ion AS revision,s.Generation AS generation,s"
                        ".ContextGeneration AS contextGeneration,s.Co"
                        "ntextJson AS contextJson FROM crm_analysis.C"
                        "onversationState s\n             WHERE s.Stat"
                        "us<>'processing' AND s.Failures<3 AND s.Next"
                        "AttemptAt<=SYSUTCDATETIME() AND\n            "
                        " (s.Status='pending' OR EXISTS(SELECT 1 FROM"
                        " crm_events.Event e WHERE e.ConversationId=s"
                        ".ConversationId AND e.State='prepared' AND "
                    )
                    + UNCONSUMED
                    + (
                        ") OR EXISTS(SELECT 1 FROM crm_analysis.Feedb"
                        "ack f WHERE f.ConversationId=s.ConversationI"
                        "d AND f.ConsumedGeneration<s.Generation))\n  "
                        "           ORDER BY s.NextAttemptAt,s.Conver"
                        "sationId"
                    )
                )
            )
            if not state:
                return None
            state = state[0]
            conversation = state["id"]
            generation = state["generation"]
            # New references only; no MAX identity cursor and no historical text replay.
            events = rows(
                c.execute(
                    (
                        "SELECT TOP(100) e.EventId AS id,e.SourceKind"
                        " AS kind,e.SourceId AS sourceId FROM crm_eve"
                        "nts.Event e\n             JOIN crm_analysis.C"
                        "onversationState s ON s.ConversationId=e.Con"
                        "versationId\n             WHERE e.Conversatio"
                        "nId=? AND e.State='prepared' AND "
                    )
                    + UNCONSUMED
                    + (
                        " ORDER BY CASE WHEN e.SourceKind='message' T"
                        "HEN 0 ELSE 1 END,e.EventId"
                    ),
                    conversation,
                )
            )
            message_events = [e for e in events if e["kind"] == "message"][:6]
            selected = [e for e in events if e["kind"] != "message"] + message_events
            known = self.identity(c, conversation)
            messages = []
            for event in message_events:
                value = rows(
                    c.execute(
                        (
                            "SELECT MessageId AS id,Body AS body,Dire"
                            "ction AS direction FROM crm.Message WHER"
                            "E MessageId=? AND ConversationId=?"
                        ),
                        event["sourceId"],
                        conversation,
                    )
                )
                if value:
                    messages.extend(value)
            feedback = rows(
                c.execute(
                    (
                        "SELECT TOP(5) FeedbackId AS id,Text AS body "
                        "FROM crm_analysis.Feedback WHERE Conversatio"
                        "nId=? AND ConsumedGeneration<? ORDER BY Crea"
                        "tedAt,FeedbackId"
                    ),
                    conversation,
                    generation,
                )
            )
            previous = (
                json.loads(state["contextJson"])
                if state["contextJson"] and state["contextGeneration"] == generation
                else None
            )
            # Wait for R3A references instead of inventing an empty result.
            total = c.execute(
                "SELECT COUNT(*) FROM crm.Message WHERE ConversationId=?", conversation
            ).fetchval()
            if not messages and not previous and total:
                c.execute(
                    (
                        "UPDATE crm_analysis.ConversationState SET Ne"
                        "xtAttemptAt=DATEADD(second,10,SYSUTCDATETIME"
                        "()),ErrorCode='waiting_source_references' WH"
                        "ERE ConversationId=?"
                    ),
                    conversation,
                )
                return None
            if not messages and not feedback:
                for event in selected:
                    c.execute(
                        (
                            "INSERT crm_analysis.Receipt(Conversation"
                            "Id,Generation,EventId,CompletedAt) VALUE"
                            "S(?,?,?,SYSUTCDATETIME())"
                        ),
                        conversation,
                        generation,
                        event["id"],
                    )
                c.execute(
                    (
                        "UPDATE crm_analysis.ConversationState SET St"
                        "atus=?,Fingerprint=?,Revision=Revision+1,Nex"
                        "tAttemptAt=DATEADD(second,5,SYSUTCDATETIME()"
                        ") WHERE ConversationId=?"
                    ),
                    (
                        "pending"
                        if self.coverage(c, conversation, generation)["coveredMessages"]
                        < total
                        else "current"
                    )
                    if previous
                    else "no_messages",
                    self.fingerprint(c, conversation),
                    conversation,
                )
                return None
            usage = c.execute(
                (
                    "SELECT COUNT_BIG(*),COALESCE(SUM(CONVERT(bigint,"
                    "ReservedOutputTokens)),0) FROM crm_analysis.Atte"
                    "mpt WHERE CreatedAt>=CONVERT(date,SYSUTCDATETIME"
                    "())"
                )
            ).fetchone()
            if (
                usage[0] >= policy["dailyRequests"]
                or usage[1] + policy["outputTokens"] > policy["dailyOutputTokens"]
            ):
                raise HTTPException(429, "analysis_daily_budget_exhausted")
            attempt = str(uuid4())
            revision = state["revision"] + 1
            c.execute(
                (
                    "UPDATE crm_analysis.ConversationState SET Revisi"
                    "on=?,Status='processing',LeaseToken=?,LeaseUntil"
                    "=DATEADD(second,60,SYSUTCDATETIME()),Failures=Fa"
                    "ilures+1 WHERE ConversationId=?"
                ),
                revision,
                attempt,
                conversation,
            )
            c.execute(
                (
                    "INSERT crm_analysis.Attempt(AttemptId,Conversati"
                    "onId,Generation,PolicyRevision,ReservedOutputTok"
                    "ens,Status,CreatedAt) VALUES(?,?,?,?,?,'reserved"
                    "',SYSUTCDATETIME())"
                ),
                attempt,
                conversation,
                generation,
                int(policy["revision"]),
                policy["outputTokens"],
            )
            references = {}
            payload_messages = []
            for index, message in enumerate(messages):
                alias = "m" + str(index + 1)
                references[alias] = (message["id"], message["direction"])
                payload_messages.append(
                    {
                        "reference": alias,
                        "direction": message["direction"],
                        "text": redact(message["body"], known),
                    }
                )
            payload_feedback = []
            for index, item in enumerate(feedback):
                alias = "f" + str(index + 1)
                references[alias] = (item["id"], "human_feedback")
                payload_feedback.append(
                    {"reference": alias, "text": redact(item["body"], known)}
                )
            if previous:
                prior_ids = list(
                    dict.fromkeys(
                        ref
                        for claims in previous.values()
                        for claim in claims
                        for ref in claim["evidenceIds"]
                    )
                )
                aliases = {}
                for index, identifier in enumerate(prior_ids):
                    direction = c.execute(
                        (
                            "SELECT Direction FROM crm.Message WHERE "
                            "MessageId=? AND ConversationId=?"
                        ),
                        identifier,
                        conversation,
                    ).fetchval()
                    if (
                        direction is None
                        and c.execute(
                            (
                                "SELECT 1 FROM crm_analysis.Feedback "
                                "WHERE FeedbackId=? AND ConversationI"
                                "d=?"
                            ),
                            identifier,
                            conversation,
                        ).fetchval()
                    ):
                        direction = "human_feedback"
                    if direction is None:
                        raise HTTPException(409, "analysis_evidence_source_missing")
                    alias = "c" + str(index + 1)
                    aliases[identifier] = alias
                    references[alias] = (identifier, direction)
                for claims in previous.values():
                    for claim in claims:
                        claim["evidenceIds"] = [
                            aliases[x] for x in claim["evidenceIds"]
                        ]
                        claim["text"] = redact(claim["text"], known)
            payload = {
                "previousContext": previous,
                "messages": payload_messages,
                "humanFeedback": payload_feedback,
            }
            return {
                "id": conversation,
                "attempt": attempt,
                "revision": revision,
                "generation": generation,
                "binding": binding,
                "policy": policy,
                "fingerprint": self.fingerprint(c, conversation),
                "events": [e["id"] for e in selected],
                "feedback": [f["id"] for f in feedback],
                "payload": payload,
                "references": references,
                "known": known,
            }

    def job_current(self, job):
        with self.workspace.transaction() as c:
            self.verify(c)
            owner = c.execute(
                "SELECT 1 FROM crm_analysis.ConversationState WHERE " + OWNER,
                job["id"],
                job["attempt"],
                job["revision"],
            ).fetchval()
            return bool(owner and self.fingerprint(c, job["id"]) == job["fingerprint"])

    def complete(self, job, context, binding, strategy=None):
        with self.workspace.transaction(write=True) as c:
            self.verify(c)
            policy = self.policy(c)
            owner = c.execute(
                "SELECT 1 FROM crm_analysis.ConversationState WHERE " + OWNER,
                job["id"],
                job["attempt"],
                job["revision"],
            ).fetchval()
            valid = (
                owner
                and policy
                and policy["enabled"]
                and policy["revision"] == job["policy"]["revision"]
                and binding == job["binding"]
                and self.fingerprint(c, job["id"]) == job["fingerprint"]
            )
            if not valid:
                c.execute(
                    (
                        "UPDATE crm_analysis.Attempt SET Status='stal"
                        "e',CompletedAt=SYSUTCDATETIME(),ErrorCode='i"
                        "nput_or_configuration_changed' WHERE Attempt"
                        "Id=? AND Status='reserved'"
                    ),
                    job["attempt"],
                )
                if owner:
                    c.execute(
                        (
                            "UPDATE crm_analysis.ConversationState SE"
                            "T Status='pending',LeaseToken=NULL,Lease"
                            "Until=NULL,Failures=0,NextAttemptAt=DATE"
                            "ADD(second,5,SYSUTCDATETIME()),Revision="
                            "Revision+1 WHERE ConversationId=?"
                        ),
                        job["id"],
                    )
                return False
            for event in job["events"]:
                c.execute(
                    (
                        "INSERT crm_analysis.Receipt(ConversationId,G"
                        "eneration,EventId,CompletedAt) VALUES(?,?,?,"
                        "SYSUTCDATETIME())"
                    ),
                    job["id"],
                    job["generation"],
                    event,
                )
            for feedback in job["feedback"]:
                c.execute(
                    (
                        "UPDATE crm_analysis.Feedback SET ConsumedGen"
                        "eration=? WHERE FeedbackId=? AND Conversatio"
                        "nId=?"
                    ),
                    job["generation"],
                    feedback,
                    job["id"],
                )
            coverage = self.coverage(c, job["id"], job["generation"])
            status = (
                "pending"
                if coverage["pendingReferences"]
                or coverage["coveredMessages"] < coverage["totalMessages"]
                else "current"
            )
            c.execute(
                (
                    "UPDATE crm_analysis.ConversationState SET Contex"
                    "tJson=?,ContextGeneration=Generation,ContextProv"
                    "ider=?,ContextModel=?,ContextPromptVersion=?,Con"
                    "textPolicyRevision=?,AnalyzedAt=SYSUTCDATETIME()"
                    ",Fingerprint=?,Status=?,LeaseToken=NULL,LeaseUnt"
                    "il=NULL,Failures=0,ErrorCode=NULL,NextAttemptAt="
                    "DATEADD(second,5,SYSUTCDATETIME()),Revision=Revi"
                    "sion+1 WHERE ConversationId=?"
                ),
                json.dumps(context, ensure_ascii=False),
                job["policy"]["provider"],
                job["policy"]["model"],
                PROMPT_VERSION,
                int(job["policy"]["revision"]),
                job["fingerprint"],
                status,
                job["id"],
            )
            c.execute(
                (
                    "UPDATE crm_analysis.Attempt SET Status='succeede"
                    "d',CompletedAt=SYSUTCDATETIME() WHERE AttemptId="
                    "?"
                ),
                job["attempt"],
            )
            if strategy is not None:
                from app.modules.conversation_strategy.api.router import save_plan

                save_plan(c, job, strategy)
            return True

    def fail(self, job, code):
        with self.workspace.transaction(write=True) as c:
            self.verify(c)
            c.execute(
                (
                    "UPDATE crm_analysis.Attempt SET Status='failed',"
                    "CompletedAt=SYSUTCDATETIME(),ErrorCode=? WHERE A"
                    "ttemptId=? AND Status='reserved'"
                ),
                code,
                job["attempt"],
            )
            c.execute(
                (
                    "UPDATE crm_analysis.ConversationState SET Status"
                    "=CASE WHEN Failures>=3 THEN 'failed' ELSE 'pendi"
                    "ng' END,LeaseToken=NULL,LeaseUntil=NULL,ErrorCod"
                    "e=?,NextAttemptAt=DATEADD(second,30,SYSUTCDATETI"
                    "ME()),Revision=Revision+1 WHERE "
                )
                + OWNER,
                code,
                job["id"],
                job["attempt"],
                job["revision"],
            )
