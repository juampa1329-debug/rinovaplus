"""Versioned institutional sources and memory. No academic writes or provider IO."""

import base64
import hashlib
import json
import re
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timezone
from uuid import UUID, uuid5

from fastapi import HTTPException

from app.institutional.auth import authorize
from app.institutional.db import (
    audit,
    institution,
    one,
    record_operation,
    replay,
    rows,
    uid,
    utc,
)
from app.institutional.knowledge_models import RecordWrite
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.modules.agents.domain import digest
from app.modules.knowledge.service import extract, terms


def chunks(pages):
    """Count SQL nvarchar units, preserving Unicode and a bounded overlap."""
    result = []
    for page in pages:
        text = re.sub(
            r"\s+", " ", re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", page["text"])
        ).strip()
        start = 0
        while start < len(text):
            end, units = start, 0
            while (
                end < len(text)
                and units + (2 if ord(text[end]) > 0xFFFF else 1) <= 1600
            ):
                units += 2 if ord(text[end]) > 0xFFFF else 1
                end += 1
            if end < len(text):
                boundary = text.rfind(" ", start + (end - start) // 2, end)
                if boundary > start:
                    end = boundary
            result.append((page["page"], text[start:end]))
            if len(result) > 250:
                raise HTTPException(413, "knowledge_chunk_limit")
            if end == len(text):
                break
            start = max(start + 1, end - 60)
    if not result:
        raise HTTPException(415, "knowledge_empty")
    return result


def current(c, settings, key, *, conversation=None):
    value = one(
        c,
        (
            "SELECT r.*,v.Snapshot FROM crm_knowledge6.Record r JOIN cr"
            "m_knowledge6.Version v ON v.InstitutionId=r.InstitutionId "
            "AND v.RecordId=r.RecordId AND v.VersionNo=r.CurrentVersion"
            " WHERE r.InstitutionId=? AND r.RecordId=?"
        ),
        institution(settings),
        uid(key),
    )
    if (
        not value
        or (conversation is None and value["Kind"] == "private")
        or (
            conversation is not None
            and (
                value["Kind"] != "private"
                or uid(str(value["ConversationId"])) != conversation
            )
        )
    ):
        raise HTTPException(404, "knowledge_record_not_found")
    return value


def public(value):
    return {
        "id": uid(str(value["RecordId"])),
        "kind": value["Kind"],
        "state": value["State"],
        "revision": value["CurrentVersion"],
        "updated_at": utc(value["UpdatedAt"]),
        "document": json.loads(value["Snapshot"]),
        "academic_authority": False,
    }


def active_context(c, conversation):
    if not c.execute(
        "SELECT 1 FROM crm.Conversation WHERE ConversationId=?", conversation
    ).fetchone():
        raise HTTPException(404, "conversation_not_found")
    row = c.execute(
        "SELECT ContextId FROM crm_agents.Assignment WHERE ConversationId=?",
        conversation,
    ).fetchone()
    return uid(str(row[0])) if row and row[0] else None


def context_revision(c, conversation):
    key = active_context(c, conversation)
    if not key:
        return None
    return c.execute(
        (
            "SELECT Revision FROM crm_agents.Context WHERE ContextId=? "
            "AND ConversationId=?"
        ),
        key,
        conversation,
    ).fetchval()


def evidence(c, snapshot, conversation):
    row = c.execute(
        (
            "SELECT Body FROM crm.Message WHERE MessageId=? AND Convers"
            "ationId=? AND Direction='incoming'"
        ),
        snapshot["source_message_id"],
        conversation,
    ).fetchone()
    if (
        not row
        or snapshot["quote"] not in row[0]
        or snapshot["body"] not in snapshot["quote"]
    ):
        raise HTTPException(422, "memory_incoming_evidence_mismatch")


def scope(c, settings, snapshot, conversation):
    if conversation:
        evidence(c, snapshot, conversation)
        return "conversation", active_context(c, conversation)
    program, stage = snapshot["program_id"], snapshot["stage_id"]
    if (
        program
        and not c.execute(
            (
                "SELECT 1 FROM crm_agents5.Program WHERE InstitutionId=? AN"
                "D ProgramId=? AND Active=1"
            ),
            institution(settings),
            program,
        ).fetchone()
    ):
        raise HTTPException(422, "knowledge_program_not_reviewed")
    if (
        stage
        and not c.execute(
            (
                "SELECT 1 FROM crm_agents.Stage WHERE StageId=? AND Program"
                "Id=? AND ApprovedRevision=Revision"
            ),
            stage,
            program,
        ).fetchone()
    ):
        raise HTTPException(422, "knowledge_stage_not_reviewed")
    return ("program" if program else "institution"), None


def rebuild(c, key, version, snapshot, state, *, review=True):
    c.execute(
        (
            "DELETE t FROM crm_ai.KnowledgeTerm t JOIN crm_ai.Knowledge"
            "Chunk x ON x.ChunkId=t.ChunkId WHERE x.DocumentId=?"
        ),
        key,
    )
    c.execute("DELETE FROM crm_ai.KnowledgeChunk WHERE DocumentId=?", key)
    c.execute(
        (
            "UPDATE crm_ai.KnowledgeDocument SET Title=?,FileName=?,Con"
            "tentHash=?,ByteLength=?,State=?,Revision=? WHERE DocumentI"
            "d=?"
        ),
        snapshot["title"],
        snapshot["filename"],
        bytes.fromhex(snapshot["content_sha256"]),
        snapshot["byte_length"],
        "deleted" if state == "archived" else state,
        version,
        key,
    )
    for ordinal, (page, body) in enumerate(chunks(snapshot["pages"])):
        chunk = str(uuid5(UUID(key), f"{version}:{ordinal}"))
        c.execute(
            (
                "INSERT crm_ai.KnowledgeChunk(ChunkId,DocumentId,Ordinal,Pa"
                "geNumber,Body) VALUES(?,?,?,?,?)"
            ),
            chunk,
            key,
            ordinal,
            page,
            body,
        )
        for term, frequency in Counter(terms(body)).items():
            c.execute(
                "INSERT crm_ai.KnowledgeTerm(Term,ChunkId,Frequency) VALUES(?,?,?)",
                term,
                chunk,
                min(frequency, 32767),
            )
    if not review:
        return
    old = c.execute(
        "SELECT Revision FROM crm_agents.SourceScope WHERE DocumentId=?", key
    ).fetchone()
    args = (
        snapshot["program_id"],
        snapshot["stage_id"],
        snapshot["owner"],
        snapshot["valid_until"],
        version,
    )
    if old:
        c.execute(
            (
                "UPDATE crm_agents.SourceScope SET ProgramId=?,StageId=?,Ow"
                "ner=?,ValidUntil=?,DocumentRevision=?,Revision=Revision+1,"
                "ApprovedAt=SYSUTCDATETIME() WHERE DocumentId=?"
            ),
            *args,
            key,
        )
    else:
        c.execute(
            (
                "INSERT crm_agents.SourceScope(ProgramId,StageId,Owner,Vali"
                "dUntil,DocumentRevision,DocumentId,Revision) VALUES(?,?,?,"
                "?,?,?,1)"
            ),
            *args,
            key,
        )


class Knowledge:
    def __init__(self, settings):
        self.settings = settings

    @staticmethod
    def collection(authority, value):
        path = authority.get("resource", "")
        if ("/knowledge/" in path and value["Kind"] != "document") or (
            "/memory/" in path and value["Kind"] not in {"collective", "dna"}
        ):
            raise HTTPException(404, "knowledge_record_not_found")

    @contextmanager
    def tx(self, authority, write=False, conversation=None):
        permission = (
            "inbox." + ("write" if write else "read")
            if conversation
            else "sources.manage"
        )
        with transaction(self.settings, write, anonymous=True) as c:
            actor = authorize(c, self.settings, authority, permission)
            module = (
                "inbox"
                if conversation
                else (
                    "memory"
                    if "/memory" in authority.get("resource", "")
                    else "knowledge"
                )
            )
            if not setting(c, self.settings, "modules")["document"]["enabled"].get(
                module, False
            ):
                raise HTTPException(403, "module_disabled")
            if conversation:
                active_context(c, conversation)
            yield c, actor["UserId"]

    def listing(self, authority, kind=None, conversation=None):
        with self.tx(authority, conversation=conversation) as (c, _):
            where, args = (
                ("r.Kind='private' AND r.ConversationId=?", [conversation])
                if conversation
                else ("r.Kind<>'private'", [])
            )
            if kind:
                where += " AND r.Kind=?"
                args.append(kind)
            found = rows(
                c,
                (
                    "SELECT r.*,v.Snapshot FROM crm_knowledge6.Record r JOIN cr"
                    "m_knowledge6.Version v ON v.InstitutionId=r.InstitutionId "
                    "AND v.RecordId=r.RecordId AND v.VersionNo=r.CurrentVersion"
                    " WHERE r.InstitutionId=? AND "
                )
                + where
                + " ORDER BY r.UpdatedAt DESC,r.RecordId",
                institution(self.settings),
                *args,
            )
            context = active_context(c, conversation) if conversation else None
            return {
                "items": [
                    {
                        **public(v),
                        "context_current": (
                            uid(str(v["ContextId"])) if v["ContextId"] else None
                        )
                        == context
                        and (
                            not conversation
                            or json.loads(v["Snapshot"]).get("context_revision")
                            == context_revision(c, conversation)
                        ),
                    }
                    for v in found
                ],
                "context_id": context,
                "academic_authority": False,
            }

    def history(self, authority, key, conversation=None):
        with self.tx(authority, conversation=conversation) as (c, _):
            item = current(c, self.settings, key, conversation=conversation)
            self.collection(authority, item)
            found = rows(
                c,
                (
                    "SELECT VersionNo,State,Reason,CreatedAt,ActorId,Snapshot F"
                    "ROM crm_knowledge6.Version WHERE InstitutionId=? AND Recor"
                    "dId=? ORDER BY VersionNo DESC"
                ),
                institution(self.settings),
                key,
            )
            return {
                "items": [
                    {
                        "version": v["VersionNo"],
                        "state": v["State"],
                        "reason": v["Reason"],
                        "created_at": utc(v["CreatedAt"]),
                        "actor": str(v["ActorId"]),
                        "document": json.loads(v["Snapshot"]),
                    }
                    for v in found
                ]
            }

    def upload(self, authority, body):
        # Authenticate before bounded CPU work; recheck on commit.
        with self.tx(authority):
            pass
        if body.revision != 0:
            raise HTTPException(422, "upload_requires_new_record")
        if any(ch in body.filename for ch in ["/", "\\", "\x00"]):
            raise HTTPException(422, "knowledge_filename_invalid")
        if len(body.filename.encode("utf-16-le")) > 320:
            raise HTTPException(422, "knowledge_filename_invalid")
        try:
            raw = base64.b64decode(body.content_base64, validate=True)
        except ValueError:
            raise HTTPException(422, "knowledge_base64_invalid") from None
        pages = extract(raw, body.filename)
        chunks(pages)
        values = body.model_dump(
            mode="json", exclude={"content_base64", "filename", "record_id"}
        )
        request = RecordWrite(**values, kind="document", body="Documento cargado")
        return self.save(
            authority,
            str(body.record_id),
            request,
            document={
                "pages": pages,
                "filename": body.filename,
                "content_sha256": hashlib.sha256(raw).hexdigest(),
                "byte_length": len(raw),
            },
        )

    def save(self, authority, key, body, conversation=None, document=None):
        if (body.kind == "private") != bool(conversation):
            raise HTTPException(422, "knowledge_kind_boundary")
        snapshot = body.model_dump(
            mode="json", exclude={"operation_id", "revision", "reason"}
        )
        if body.kind == "document":
            raw = body.body.encode()
            snapshot.update(
                document
                or {
                    "pages": [{"page": 1, "text": body.body}],
                    "filename": "correccion.txt",
                    "content_sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_length": len(raw),
                }
            )
            chunks(snapshot["pages"])
        with self.tx(authority, True, conversation) as (c, actor):
            old = one(
                c,
                (
                    "SELECT Kind,CurrentVersion,ConversationId FROM crm_knowled"
                    "ge6.Record WHERE InstitutionId=? AND RecordId=?"
                ),
                institution(self.settings),
                key,
            )
            payload = {
                "snapshot": snapshot,
                "revision": body.revision,
                "conversation": conversation,
                "reason": body.reason,
            }
            hashed, prior = replay(
                c,
                self.settings,
                actor,
                str(body.operation_id),
                "knowledge.edit",
                key,
                payload,
            )
            if prior:
                return prior
            if old and (
                old["Kind"] != body.kind
                or (uid(str(old["ConversationId"])) if old["ConversationId"] else None)
                != conversation
            ):
                raise HTTPException(404, "knowledge_record_not_found")
            if body.revision != (old["CurrentVersion"] if old else 0):
                raise HTTPException(409, "revision_conflict")
            count = c.execute(
                "SELECT COUNT(*) FROM crm_knowledge6.Record WHERE InstitutionId=?",
                institution(self.settings),
            ).fetchval()
            if not old and count >= 500:
                raise HTTPException(409, "knowledge_record_limit")
            self.persist(
                c, actor, key, snapshot, "draft", body, old is None, conversation
            )
            result = {
                "saved": True,
                "id": key,
                "revision": body.revision + 1,
                "state": "draft",
            }
            record_operation(
                c,
                self.settings,
                actor,
                str(body.operation_id),
                "knowledge.edit",
                key,
                hashed,
                result,
            )
            return result

    def persist(
        self, c, actor, key, snapshot, state, body, creating=False, conversation=None
    ):
        kind = snapshot["kind"]
        selected_scope, context = scope(c, self.settings, snapshot, conversation)
        if state == "archived" and conversation:
            context = snapshot.get("context_id")
        if (
            state == "published"
            and date.fromisoformat(snapshot["valid_until"])
            < datetime.now(timezone.utc).date()
        ):
            raise HTTPException(409, "knowledge_expired")
        if (
            kind == "dna"
            and state == "published"
            and c.execute(
                (
                    "SELECT 1 FROM crm_knowledge6.Record WHERE InstitutionId=? "
                    "AND Kind='dna' AND State='published' AND RecordId<>?"
                ),
                institution(self.settings),
                key,
            ).fetchone()
        ):
            raise HTTPException(409, "knowledge_DNA_already_published")
        if (
            kind == "collective"
            and state == "published"
            and c.execute(
                (
                    "SELECT COUNT(*) FROM crm_knowledge6.Record WHERE Instituti"
                    "onId=? AND Kind='collective' AND State='published' AND Val"
                    "idUntil>=CONVERT(date,SYSUTCDATETIME()) AND RecordId<>?"
                ),
                institution(self.settings),
                key,
            ).fetchval()
            >= 20
        ):
            raise HTTPException(409, "knowledge_shared_context_limit")
        version = body.revision + 1
        headers = (
            selected_scope,
            snapshot["program_id"],
            snapshot["stage_id"],
            conversation,
            context,
            state,
            snapshot["visibility"],
            version,
            snapshot["valid_until"],
        )
        if creating:
            c.execute(
                (
                    "INSERT crm_knowledge6.Record(Scope,ProgramId,StageId,Conve"
                    "rsationId,ContextId,State,Visibility,CurrentVersion,ValidU"
                    "ntil,InstitutionId,RecordId,Kind) VALUES(?,?,?,?,?,?,?,?,?"
                    ",?,?,?)"
                ),
                *headers,
                institution(self.settings),
                key,
                kind,
            )
            if kind == "document":
                c.execute(
                    (
                        "INSERT crm_ai.KnowledgeDocument(DocumentId,Title,FileName,"
                        "ContentHash,ByteLength,State) VALUES(?,?,?,?,?,'draft')"
                    ),
                    key,
                    snapshot["title"],
                    snapshot["filename"],
                    bytes.fromhex(snapshot["content_sha256"]),
                    snapshot["byte_length"],
                )
        else:
            c.execute(
                (
                    "UPDATE crm_knowledge6.Record SET Scope=?,ProgramId=?,Stage"
                    "Id=?,ConversationId=?,ContextId=?,State=?,Visibility=?,Cur"
                    "rentVersion=?,ValidUntil=?,UpdatedAt=SYSUTCDATETIME() WHER"
                    "E InstitutionId=? AND RecordId=? AND CurrentVersion=?"
                ),
                *headers,
                institution(self.settings),
                key,
                body.revision,
            )
            if c.rowcount != 1:
                raise HTTPException(409, "revision_conflict")
        snapshot["context_id"] = context
        if conversation and state != "archived":
            snapshot["context_revision"] = context_revision(c, conversation)
        c.execute(
            (
                "INSERT crm_knowledge6.Version(InstitutionId,RecordId,Versi"
                "onNo,State,Snapshot,ActorId,OperationId,Reason) VALUES(?,?"
                ",?,?,?,?,?,?)"
            ),
            institution(self.settings),
            key,
            version,
            state,
            json.dumps(snapshot, ensure_ascii=False),
            actor,
            str(body.operation_id),
            body.reason,
        )
        if kind == "document":
            rebuild(c, key, version, snapshot, state)
        audit(
            c,
            self.settings,
            actor,
            "knowledge." + state,
            key,
            revision=version,
            kind=kind,
            scope=selected_scope,
        )
        from app.institutional.agents import invalidate

        invalidate(c, conversation)

    def transition(self, authority, key, action, body, conversation=None):
        if action not in {"publish", "archive", "restore", "reindex"}:
            raise HTTPException(404, "knowledge_action_unknown")
        if not body.confirmed:
            raise HTTPException(409, "knowledge_review_confirmation_required")
        with self.tx(authority, True, conversation) as (c, actor):
            hashed, prior = replay(
                c,
                self.settings,
                actor,
                str(body.operation_id),
                "knowledge." + action,
                key,
                {**body.model_dump(mode="json"), "conversation": conversation},
            )
            if prior:
                return prior
            old = current(c, self.settings, key, conversation=conversation)
            self.collection(authority, old)
            if old["CurrentVersion"] != body.revision:
                raise HTTPException(409, "revision_conflict")
            snapshot = json.loads(old["Snapshot"])
            state = "archived" if action == "archive" else "published"
            if action == "restore":
                prior_version = one(
                    c,
                    (
                        "SELECT Snapshot,State FROM crm_knowledge6.Version WHERE In"
                        "stitutionId=? AND RecordId=? AND VersionNo=?"
                    ),
                    institution(self.settings),
                    key,
                    body.version or 0,
                )
                if not prior_version or prior_version["State"] != "published":
                    raise HTTPException(409, "knowledge_approved_version_required")
                snapshot = json.loads(prior_version["Snapshot"])
            if (
                conversation
                and action != "archive"
                and (
                    snapshot.get("context_id") != active_context(c, conversation)
                    or snapshot.get("context_revision")
                    != context_revision(c, conversation)
                )
            ):
                raise HTTPException(409, "memory_conversation_context_changed")
            if action == "reindex":
                if old["Kind"] != "document":
                    raise HTTPException(422, "knowledge_document_required")
                rebuild(c, key, body.revision, snapshot, old["State"], review=False)
                audit(
                    c,
                    self.settings,
                    actor,
                    "knowledge.reindex",
                    key,
                    revision=body.revision,
                )
                result = {
                    "rebuilt": True,
                    "revision": body.revision,
                    "derived_only": True,
                }
            else:
                self.persist(
                    c, actor, key, snapshot, state, body, conversation=conversation
                )
                result = {
                    "saved": True,
                    "id": key,
                    "revision": body.revision + 1,
                    "state": state,
                }
            record_operation(
                c,
                self.settings,
                actor,
                str(body.operation_id),
                "knowledge." + action,
                key,
                hashed,
                result,
            )
            return result

    def search(self, authority, body):
        with self.tx(authority) as (c, _):
            found = search(
                c,
                self.settings,
                body.query,
                body.program_id,
                str(body.stage_id) if body.stage_id else None,
            )
            result = {"items": found, "method": "lexical_SQL", "current_only": True}
            if hasattr(body, "expected_document_id"):
                rank = next(
                    (
                        n + 1
                        for n, v in enumerate(found)
                        if v["document_id"] == str(body.expected_document_id)
                    ),
                    None,
                )
                result.update(rank=rank, reciprocal_rank=1 / rank if rank else 0)
            return result


def search(c, settings, query, program=None, stage=None, allowed=None):
    if not setting(c, settings, "modules")["document"]["enabled"].get(
        "knowledge", False
    ):
        return []
    tokens = list(dict.fromkeys(terms(query)))[:24]
    if not tokens or allowed == []:
        return []
    filters = [
        "r.InstitutionId=?",
        "r.Kind='document'",
        "r.State='published'",
        "r.Visibility='agent_context'",
        "r.ValidUntil>=CONVERT(date,SYSUTCDATETIME())",
        "d.State='published'",
        "d.Revision=r.CurrentVersion",
        "s.DocumentRevision=d.Revision",
        "s.ValidUntil>=CONVERT(date,SYSUTCDATETIME())",
    ]
    args = [institution(settings)]
    for column, value in [("ProgramId", program), ("StageId", stage)]:
        filters.append(
            "(r."
            + column
            + " IS NULL"
            + (" OR r." + column + "=?" if value is not None else "")
            + ")"
        )
        filters.append(
            "(s."
            + column
            + " IS NULL"
            + (" OR s." + column + "=?" if value is not None else "")
            + ")"
        )
        if value is not None:
            args.extend([value, value])
    if allowed is not None:
        filters.append("d.DocumentId IN(" + ",".join("?" for _ in allowed) + ")")
        args.extend(allowed)
    filters.append("t.Term IN(" + ",".join("?" for _ in tokens) + ")")
    args.extend(tokens)
    found = c.execute(
        (
            "SELECT TOP(5) x.ChunkId,d.DocumentId,d.Title,x.PageNumber,"
            "x.Body,d.Revision,s.Revision,COUNT(*),SUM(t.Frequency) FRO"
            "M crm_ai.KnowledgeTerm t JOIN crm_ai.KnowledgeChunk x ON x"
            ".ChunkId=t.ChunkId JOIN crm_ai.KnowledgeDocument d ON d.Do"
            "cumentId=x.DocumentId JOIN crm_agents.SourceScope s ON s.D"
            "ocumentId=d.DocumentId JOIN crm_knowledge6.Record r ON r.R"
            "ecordId=d.DocumentId WHERE "
        )
        + " AND ".join(filters)
        + (
            " GROUP BY x.ChunkId,d.DocumentId,d.Title,x.PageNumber,x.Bo"
            "dy,d.Revision,s.Revision ORDER BY COUNT(*) DESC,SUM(t.Freq"
            "uency) DESC,x.ChunkId"
        ),
        *args,
    ).fetchall()
    return [
        {
            "id": uid(str(r[0])),
            "document_id": uid(str(r[1])),
            "title": r[2],
            "page": r[3],
            "text": r[4],
            "revision": r[5],
            "scope_revision": r[6],
            "matched_terms": r[7],
            "source_kind": "document",
        }
        for r in found
    ]


def effective(c, settings, selection, conversation=None):
    """Filter metadata in SQL before retrieving immutable bodies."""
    config = selection["configuration"]
    context = selection.get("context") or {}
    program, stage = context.get("program_id"), context.get("stage_id")
    allowed = [
        "r.InstitutionId=?",
        "r.State='published'",
        "r.Visibility='agent_context'",
        "r.ValidUntil>=CONVERT(date,SYSUTCDATETIME())",
        "r.Kind IN('collective','dna')",
    ]
    args = [institution(settings)]
    for col, value in [("ProgramId", program), ("StageId", stage)]:
        allowed.append(
            "(r."
            + col
            + " IS NULL"
            + (" OR r." + col + "=?" if value is not None else "")
            + ")"
        )
        if value is not None:
            args.append(value)
    if "collective" not in config["memories"]:
        allowed.append("r.Kind='dna'")
    if not setting(c, settings, "modules")["document"]["enabled"].get("memory", False):
        allowed.append("1=0")
    found = rows(
        c,
        (
            "SELECT TOP(25) r.RecordId,r.Kind,r.CurrentVersion,v.Snapsh"
            "ot FROM crm_knowledge6.Record r JOIN crm_knowledge6.Versio"
            "n v ON v.InstitutionId=r.InstitutionId AND v.RecordId=r.Re"
            "cordId AND v.VersionNo=r.CurrentVersion WHERE "
        )
        + " AND ".join(allowed)
        + " ORDER BY r.Kind,r.RecordId",
        *args,
    )
    items = [
        {
            "id": uid(str(v["RecordId"])),
            "version": v["CurrentVersion"],
            "kind": v["Kind"],
            "origin": json.loads(v["Snapshot"])["origin"],
            "content": json.loads(v["Snapshot"]),
        }
        for v in found
    ]
    private = []
    if conversation and "customer_profile" in config["memories"]:
        context_id = active_context(c, conversation)
        where = "r.ContextId=?" if context_id else "r.ContextId IS NULL"
        vals = [context_id] if context_id else []
        if context_id:
            where += (
                " AND TRY_CONVERT(int,JSON_VALUE(v.Snapshot,'$.context_revision'))=?"
            )
            vals.append(context_revision(c, conversation))
        records = rows(
            c,
            (
                "SELECT TOP(25) r.RecordId,r.CurrentVersion,v.Snapshot FROM"
                " crm_knowledge6.Record r JOIN crm_knowledge6.Version v ON "
                "v.InstitutionId=r.InstitutionId AND v.RecordId=r.RecordId "
                "AND v.VersionNo=r.CurrentVersion WHERE r.InstitutionId=? A"
                "ND r.Kind='private' AND r.State='published' AND r.Visibili"
                "ty='conversation_only' AND r.ValidUntil>=CONVERT(date,SYSU"
                "TCDATETIME()) AND r.ConversationId=? AND "
            )
            + where
            + " ORDER BY r.RecordId",
            institution(settings),
            conversation,
            *vals,
        )
        private = [
            {
                "id": uid(str(v["RecordId"])),
                "version": v["CurrentVersion"],
                "content": json.loads(v["Snapshot"]),
            }
            for v in records
        ]
    return {
        "shared": items,
        "conversation": private,
        "fingerprint": digest([items, private]),
        "authority": "reviewed_CRM_not_verified_SIIE",
        "precedence": [
            "immutable_academic_and_privacy_rules",
            "reviewed_institution_DNA",
            "agent_restrictions",
            "quoted_sources_and_declared_facts",
        ],
    }


def enrich(c, settings, selection, program, stage):
    conversation = getattr(c, "agent_conversation", None)
    selection["context"] = {
        **(selection.get("context") or {}),
        "program_id": program,
        "stage_id": stage,
    }
    value = effective(c, settings, selection, conversation)
    selection["institution_dna"] = [v for v in value["shared"] if v["kind"] == "dna"]
    selection["knowledge_context"] = value
    selection["binding"] = digest([selection["binding"], value["fingerprint"]])
    return value


def freshness(c, settings, conversation=None):
    # Conservative replay invalidation. Hash stays internal; private bodies from
    # other conversations are never selected, even for an administrator.
    where = "Kind<>'private'"
    args = []
    if conversation:
        where = "(Kind<>'private' OR ConversationId=?)"
        args = [conversation]
    found = c.execute(
        (
            "SELECT RecordId,CurrentVersion,State,ValidUntil FROM crm_k"
            "nowledge6.Record WHERE InstitutionId=? AND "
        )
        + where
        + " ORDER BY RecordId",
        institution(settings),
        *args,
    ).fetchall()
    binding = (
        [active_context(c, conversation), context_revision(c, conversation)]
        if conversation
        else None
    )
    modules = setting(c, settings, "modules")
    return hashlib.sha256(
        json.dumps(
            [
                [[str(x) for x in r] for r in found],
                binding,
                modules["revision"],
                modules["document"],
            ],
            sort_keys=True,
        ).encode()
        + str(datetime.now(timezone.utc).date()).encode()
    ).digest()
