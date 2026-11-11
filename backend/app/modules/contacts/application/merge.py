"""Reversible local CRM identity groups; original conversation records stay put."""

import hashlib
import json
import sys
from typing import Annotated, Literal
from uuid import UUID, uuid4

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import Field, ValidationError, field_validator

from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.schemas import LocalModel
from app.sql_workspace import (
    CONTACT_COLUMNS,
    CONTACT_KEYS,
    Contact,
    ContactMutation,
    Identifier,
)
from app.sql_workspace_shape import SHAPE_SQL

MERGE_SHAPE = SHAPE_SQL.replace("N'crm'", "N'crm_merge'").replace(
    "N'crm.shape'", "N'crm_merge.shape'"
)
SCALAR_FIELDS = [
    "name",
    "phone",
    "city",
    "schedule",
    "stage",
    "tags",
    "notes",
    "type",
    "interests",
]
PROFILE_FIELDS = [
    "givenNames",
    "firstSurname",
    "secondSurname",
    "email",
    "aspirationPeriodId",
]
Fingerprint = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
FieldKey = Annotated[str, Field(min_length=1, max_length=64)]


class MergePreview(LocalModel):
    sourceContactId: Identifier
    targetContactId: Identifier
    choices: Annotated[
        dict[FieldKey, Literal["source", "target"]], Field(max_length=220)
    ] = Field(default_factory=dict)


class MergeCommit(MergePreview):
    operationId: Identifier
    expectedFingerprint: Fingerprint
    confirmedSamePerson: Literal[True]

    @field_validator("confirmedSamePerson", mode="before")
    @classmethod
    def strict_confirmation(cls, value):
        if value is not True:
            raise ValueError("Explicit human confirmation required")
        return value


class UndoPreview(LocalModel):
    mergeId: Identifier
    choices: Annotated[
        dict[FieldKey, Literal["current", "before"]], Field(max_length=220)
    ] = Field(default_factory=dict)


class UndoCommit(UndoPreview):
    operationId: Identifier
    expectedFingerprint: Fingerprint
    confirmedUndo: Literal[True]

    @field_validator("confirmedUndo", mode="before")
    @classmethod
    def strict_confirmation(cls, value):
        if value is not True:
            raise ValueError("Explicit human confirmation required")
        return value


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).digest()


def present(c, required=False):
    legacy = getattr(sys.modules.get(__name__), "present", None)
    if legacy is not None and legacy is not present:
        return legacy(c, required=True) if required else legacy(c)
    row = c.execute("SELECT SCHEMA_ID(N'crm_merge')").fetchone()
    if row is None or row[0] is None:
        if required:
            raise HTTPException(503, "contact_merge_unavailable")
        return False
    marker = c.execute(
        (
            "SELECT CONVERT(nvarchar(80),value) FROM sys.extended_propert"
            "ies WHERE class=3 AND major_id=SCHEMA_ID(N'crm_merge') AND n"
            "ame=N'crm_merge.contract'"
        )
    ).fetchone()
    shape = c.execute(MERGE_SHAPE).fetchone()
    if marker is None or marker[0] != "merge-v1" or shape is None or not shape[0]:
        raise CatalogUnavailable()
    return True


def relations(c):
    if not present(c):
        return []
    return [
        {
            "mergeId": str(r[0]).lower(),
            "sourceContactId": str(r[1]).lower(),
            "targetContactId": str(r[2]).lower(),
        }
        for r in c.execute(
            (
                "SELECT MergeId,SourceContactId,TargetContactId FROM crm_merg"
                "e.MergeCase WHERE Active=1 ORDER BY CreatedAt,MergeId"
            )
        ).fetchall()
    ]


def membership(c, contact):
    contact = str(UUID(contact))
    links = relations(c)
    primary = next(
        (r["targetContactId"] for r in links if r["sourceContactId"] == contact),
        contact,
    )
    members = [
        primary,
        *[r["sourceContactId"] for r in links if r["targetContactId"] == primary],
    ]
    return {
        "primaryContactId": primary,
        "memberContactIds": members,
        "links": [r for r in links if r["targetContactId"] == primary],
    }


def read_contact(c, contact):
    row = c.execute(
        f"SELECT {CONTACT_COLUMNS} FROM crm.Contact WHERE ContactId=?", contact
    ).fetchone()
    if row is None:
        raise HTTPException(404, "contact_not_found")
    value = dict(zip(CONTACT_KEYS, row, strict=True))
    value["id"] = str(value["id"]).lower()
    value["customValues"] = json.loads(value["customValues"])
    from app.modules.contacts.api.router import decorate

    return decorate(c, [value])[0]


def group_view(c, contact):
    group = membership(c, contact)
    members = []
    for member in group["memberContactIds"]:
        row = c.execute(
            "SELECT ConversationId FROM crm.Conversation WHERE ContactId=?", member
        ).fetchone()
        if row is None:
            raise HTTPException(409, "group_conversation_missing")
        value = read_contact(c, member)
        members.append(
            {
                "contactId": member,
                "conversationId": str(row[0]).lower(),
                "name": value["name"],
                "phone": value["phone"],
                "channel": "Local",
            }
        )
    return {
        **group,
        "members": members,
        "primaryContact": read_contact(c, group["primaryContactId"]),
        "primaryConversationId": members[0]["conversationId"],
    }


def historical_ids(c, contact):
    """Keep privacy scope after undo as well as after subsequent ficha edits."""
    ids = {str(UUID(contact))}
    if not present(c):
        return ids
    pairs = c.execute(
        "SELECT SourceContactId,TargetContactId FROM crm_merge.MergeCase"
    ).fetchall()
    while True:
        expanded = ids | {
            str(v).lower()
            for pair in pairs
            if any(str(v).lower() in ids for v in pair)
            for v in pair
        }
        if expanded == ids:
            return ids
        ids = expanded


def identifiers(value):
    profile = value.get("institutionalProfile") or {}
    names = [
        value.get("name", ""),
        *[profile.get(k, "") for k in ["givenNames", "firstSurname", "secondSurname"]],
    ]
    return sorted(
        {
            str(v)
            for v in [
                *names,
                *[part for name in names for part in name.split()],
                value.get("phone", ""),
                profile.get("document", ""),
                profile.get("email", ""),
            ]
            if v
        }
    )


def privacy_scope(c, contact):
    ids = historical_ids(c, contact)
    values = {v for key in ids for v in identifiers(read_contact(c, key))}
    if present(c):
        placeholders = ",".join("?" for _ in ids)
        for row in c.execute(
            "SELECT IdentifiersJson FROM crm_merge.Operation WHERE SourceContactId IN ("
            + placeholders
            + ") OR TargetContactId IN ("
            + placeholders
            + ")",
            *sorted(ids),
            *sorted(ids),
        ).fetchall():
            values.update(json.loads(row[0]))
    return sorted(values)


def analysis_guard(c, ids):
    legacy = getattr(sys.modules.get(__name__), "analysis_guard", None)
    if legacy is not None and legacy is not analysis_guard:
        return legacy(c, ids)
    if c.execute("SELECT SCHEMA_ID(N'crm_analysis')").fetchone()[0] is None:
        return
    placeholders = ",".join("?" for _ in ids)
    if c.execute(
        (
            "SELECT TOP(1) a.AttemptId FROM crm_analysis.Attempt a JOIN c"
            "rm.Conversation v ON v.ConversationId=a.ConversationId WHERE"
            " a.Status='reserved' AND v.ContactId IN ("
        )
        + placeholders
        + ")",
        *ids,
    ).fetchone():
        raise HTTPException(409, "analysis_attempt_reserved")


def invalidate_analysis(c, ids):
    if c.execute("SELECT SCHEMA_ID(N'crm_analysis')").fetchone()[0] is None:
        return
    placeholders = ",".join("?" for _ in ids)
    c.execute(
        (
            "UPDATE s SET Generation=Generation+1,Revision=Revision+1,Sta"
            "tus='pending',Failures=0,ErrorCode=NULL,LeaseToken=NULL,Leas"
            "eUntil=NULL,NextAttemptAt=SYSUTCDATETIME() FROM crm_analysis"
            ".ConversationState s JOIN crm.Conversation v ON v.Conversati"
            "onId=s.ConversationId WHERE v.ContactId IN ("
        )
        + placeholders
        + ")",
        *ids,
    )


def field_keys(left, right):
    return [
        *SCALAR_FIELDS,
        "program",
        *["profile." + k for k in PROFILE_FIELDS],
        "profile.document",
        *[
            "custom." + k
            for k in sorted(left["customValues"].keys() | right["customValues"].keys())
        ],
    ]


def field_value(value, key):
    if key == "program":
        return {"programId": value["programId"], "program": value["program"]}
    if key.startswith("profile."):
        profile = value.get("institutionalProfile") or {}
        if key == "profile.document":
            return {
                "documentTypeId": profile.get("documentTypeId"),
                "document": profile.get("document", ""),
            }
        return profile.get(key[8:])
    if key.startswith("custom."):
        return value["customValues"].get(key[7:])
    return value[key]


def select_fields(base, alternative, choices, alternative_name):
    unknown = choices.keys() - set(field_keys(base, alternative))
    if unknown:
        raise HTTPException(422, "unknown_merge_field")
    result = json.loads(json.dumps(base))
    for key, choice in choices.items():
        if choice != alternative_name:
            continue
        if key == "program":
            result.update(field_value(alternative, key))
        elif key.startswith("custom."):
            name = key[7:]
            if name in alternative["customValues"]:
                result["customValues"][name] = alternative["customValues"][name]
            else:
                result["customValues"].pop(name, None)
        elif key.startswith("profile."):
            from app.modules.contacts.domain.models import InstitutionalProfile

            result["institutionalProfile"] = (
                result.get("institutionalProfile")
                or InstitutionalProfile().model_dump()
            )
            if key == "profile.document":
                result["institutionalProfile"].update(field_value(alternative, key))
            else:
                result["institutionalProfile"][key[8:]] = (
                    alternative.get("institutionalProfile")
                    or InstitutionalProfile().model_dump()
                )[key[8:]]
        else:
            result[key] = alternative[key]
    return result


class ContactMerge:
    def __init__(self, workspace):
        self.workspace = workspace

    def state(self, c, ids):
        # Any concurrent confirmation invalidates the global preview revision.
        return [
            self.workspace.revision(c),
            str(
                c.execute(
                    "SELECT COALESCE(MAX(Revision),0) FROM crm_merge.Operation"
                ).fetchone()[0]
            ),
            [read_contact(c, i) for i in ids],
            [membership(c, i) for i in ids],
            [
                str(tuple(r))
                for r in c.execute(
                    (
                        "SELECT ConversationId,UpdatedAt FROM crm.Conversation ORDER "
                        "BY ConversationId"
                    )
                ).fetchall()
            ],
            str(
                c.execute(
                    "SELECT COALESCE(MAX(Revision),0) FROM crm_config.Operation"
                ).fetchone()[0]
            ),
            str(
                c.execute(
                    "SELECT COALESCE(MAX(Revision),0) FROM crm_inbox.Operation"
                ).fetchone()[0]
            ),
        ]

    def prepare(self, c, body, undo=False):
        present(c, required=True)
        if undo:
            row = c.execute(
                (
                    "SELECT SourceContactId,TargetContactId,Active,BeforeJson,App"
                    "liedJson,AppliedCrmRevision FROM crm_merge.MergeCase WHERE M"
                    "ergeId=?"
                ),
                body.mergeId,
            ).fetchone()
            if row is None or not row[2]:
                raise HTTPException(409, "merge_not_active")
            source, target = str(row[0]).lower(), str(row[1]).lower()
            before, applied = json.loads(row[3]), json.loads(row[4])
            current = read_contact(c, target)
            later = (
                c.execute(
                    (
                        "SELECT TOP(1) Revision FROM crm.Operation WHERE ContactId=? "
                        "AND Action='edit_contact' AND Revision>?"
                    ),
                    target,
                    row[5],
                ).fetchone()
                is not None
            )
            changed = later or current != applied
            choices = {
                key: "current" if changed else "before"
                for key in field_keys(current, before)
            } | body.choices
            result = select_fields(current, before, choices, "before")
            # Absence is restored only for a fully selected pre-merge target image.
            restore_absent = (
                before.get("institutionalProfile") is None
                and all(
                    choices[k] == "before" for k in choices if k.startswith("profile.")
                )
                and applied.get("institutionalProfile") is not None
            )
            if restore_absent:
                result["institutionalProfile"] = None
            left, right = current, before
        else:
            source, target = (
                str(UUID(body.sourceContactId)),
                str(UUID(body.targetContactId)),
            )
            links = relations(c)
            if source == target or any(
                r["sourceContactId"] == target
                or r["sourceContactId"] == source
                or r["targetContactId"] == source
                for r in links
            ):
                raise HTTPException(409, "invalid_merge_group")
            left, right = read_contact(c, target), read_contact(c, source)
            choices = {key: "target" for key in field_keys(left, right)} | body.choices
            result = select_fields(left, right, choices, "source")
            changed, restore_absent = False, False
        ids = sorted(historical_ids(c, target) | historical_ids(c, source))
        blocked = None
        try:
            analysis_guard(c, ids)
        except HTTPException as error:
            blocked = error.detail
        from app.modules.crm_configuration.application.service import validate_contact
        from app.modules.contacts.api.router import validate_catalogs

        validation_error = None
        try:
            contact = Contact.model_validate(result)
            validate_contact(c, contact, left)
            if contact.institutionalProfile:
                validate_catalogs(
                    c,
                    contact.institutionalProfile.documentTypeId,
                    contact.institutionalProfile.aspirationPeriodId,
                )
            if contact.programId is not None:
                program = c.execute(
                    "SELECT NombrePrograma FROM dbo.ACProgramas WHERE Id_Programa=?",
                    contact.programId,
                ).fetchone()
                if program is None or program[0] != contact.program:
                    raise HTTPException(422, "invalid_program")
        except ValidationError:
            validation_error = "invalid_selected_fields"
        except HTTPException as error:
            if error.status_code != 422:
                raise
            validation_error = "selected_fields_not_valid_in_current_catalog"
        fingerprint = digest(
            [
                "undo" if undo else "merge",
                body.mergeId if undo else [source, target],
                choices,
                self.state(c, ids),
            ]
        ).hex()
        preview = {
            "sourceContactId": source,
            "targetContactId": target,
            "fingerprint": fingerprint,
            "blockedReason": blocked,
            "validationError": validation_error,
            "laterConfirmations": changed,
            "fields": [
                {
                    "key": key,
                    "current": field_value(left, key),
                    "alternative": field_value(right, key),
                    "selected": choices[key],
                }
                for key in field_keys(left, right)
            ],
            "members": group_view(c, target)["members"],
            "source": next(
                m for m in group_view(c, source)["members"] if m["contactId"] == source
            ),
        }
        return preview, result, ids, choices, restore_absent

    def preview(self, body, undo=False):
        with self.workspace.transaction() as c:
            return self.prepare(c, body, undo)[0]

    def commit(self, body, undo=False):
        action = "undo" if undo else "merge"
        payload = body.model_dump(exclude={"operationId"})
        hashed = digest([action, payload])
        with self.workspace.transaction(write=True) as c:
            present(c, required=True)
            replay = c.execute(
                (
                    "SELECT PayloadHash,MergeId FROM crm_merge.Operation WHERE Op"
                    "erationId=?"
                ),
                body.operationId,
            ).fetchone()
            if replay:
                if bytes(replay[0]) != hashed:
                    raise HTTPException(409, "operation_changed")
                return {
                    "mergeId": str(replay[1]).lower(),
                    "replayed": True,
                    "revision": self.workspace.revision(c),
                }
            if c.execute(
                "SELECT OperationId FROM crm.Operation WHERE OperationId=?",
                body.operationId,
            ).fetchone():
                raise HTTPException(409, "operation_id_in_use")
            preview, result, ids, choices, restore_absent = self.prepare(c, body, undo)
            if preview["fingerprint"] != body.expectedFingerprint:
                raise HTTPException(409, "merge_preview_changed")
            if preview["validationError"]:
                raise HTTPException(422, preview["validationError"])
            analysis_guard(c, ids)
            target, source = preview["targetContactId"], preview["sourceContactId"]
            before = read_contact(c, target)
            conversation = c.execute(
                "SELECT ConversationId FROM crm.Conversation WHERE ContactId=?", target
            ).fetchone()[0]
            mutation = ContactMutation(
                operationId=body.operationId,
                expectedRevision=self.workspace.revision(c),
                conversationId=str(conversation),
                client=Contact.model_validate(result),
            )
            self.workspace.mutate_in(
                c,
                "edit_contact",
                target,
                mutation,
                compact=True,
                capture_identity=False,
            )
            if undo and restore_absent:
                c.execute("DELETE FROM crm_identity.Profile WHERE ContactId=?", target)
            applied = read_contact(c, target)
            merge_id = str(UUID(body.mergeId)) if undo else str(uuid4())

            def serial(value):
                return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

            if undo:
                c.execute(
                    (
                        "UPDATE crm_merge.MergeCase SET Active=0,UndoneAt=SYSUTCDATET"
                        "IME(),UndoBeforeJson=?,UndoAppliedJson=? WHERE MergeId=?"
                    ),
                    serial(before),
                    serial(applied),
                    merge_id,
                )
            else:
                c.execute(
                    (
                        "INSERT crm_merge.MergeCase(MergeId,SourceContactId,TargetCon"
                        "tactId,Active,BeforeJson,AppliedJson,ChoicesJson,AppliedCrmR"
                        "evision) VALUES(?,?,?,1,?,?,?,?)"
                    ),
                    merge_id,
                    source,
                    target,
                    serial(before),
                    serial(applied),
                    serial(choices),
                    int(self.workspace.revision(c)),
                )
            known = sorted(
                {v for i in ids for v in identifiers(read_contact(c, i))}
                | set(identifiers(before))
            )
            c.execute(
                (
                    "INSERT crm_merge.Operation(OperationId,Action,MergeId,Source"
                    "ContactId,TargetContactId,PayloadHash,IdentifiersJson,Actor)"
                    " VALUES(?,?,?,?,?,?,?,'local-operator')"
                ),
                body.operationId,
                action,
                merge_id,
                source,
                target,
                hashed,
                serial(known),
            )
            invalidate_analysis(c, ids)
            return {
                "mergeId": merge_id,
                "replayed": False,
                "revision": self.workspace.revision(c),
            }


def before_write(c, contact):
    if not present(c):
        return None
    if any(r["sourceContactId"] == contact for r in relations(c)):
        raise HTTPException(409, "alias_contact_read_only")
    if c.execute(
        (
            "SELECT TOP(1) MergeId FROM crm_merge.MergeCase WHERE SourceC"
            "ontactId=? OR TargetContactId=?"
        ),
        contact,
        contact,
    ).fetchone():
        ids = sorted(historical_ids(c, contact))
        analysis_guard(c, ids)
        return read_contact(c, contact)
    return None


def after_write(c, previous, contact, operation, hashed):
    if previous is None:
        return
    known = sorted(
        set(identifiers(previous)) | set(identifiers(read_contact(c, contact)))
    )
    c.execute(
        (
            "INSERT crm_merge.Operation(OperationId,Action,MergeId,Source"
            "ContactId,TargetContactId,PayloadHash,IdentifiersJson,Actor)"
            " VALUES(?,'identifiers',NULL,?,?,?,?,'local-operator')"
        ),
        operation,
        contact,
        contact,
        hashed,
        json.dumps(known, ensure_ascii=False),
    )
    invalidate_analysis(c, sorted(historical_ids(c, contact)))


def install_contact_merge(app: FastAPI):
    app.state.contact_merge = ContactMerge(app.state.sql_workspace)
    router = APIRouter(
        prefix="/api/local/crm/contact-merges", tags=["local-contact-merge"]
    )

    def execute(request, body, *, write=False, undo=False):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            service = request.app.state.contact_merge
            value = service.commit(body, undo) if write else service.preview(body, undo)
            return JSONResponse(value, headers={"Cache-Control": "no-store"})
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "local_sql_unavailable") from None

    @router.post("/preflight")
    def preview(request: Request, body: MergePreview):
        return execute(request, body)

    @router.get("/contacts/{contact_id}")
    def group(request: Request, contact_id: Identifier):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            with request.app.state.sql_workspace.transaction() as c:
                return JSONResponse(
                    group_view(c, contact_id), headers={"Cache-Control": "no-store"}
                )
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "local_sql_unavailable") from None

    @router.post("")
    def commit(request: Request, body: MergeCommit):
        return execute(request, body, write=True)

    @router.post("/undo/preflight")
    def undo_preview(request: Request, body: UndoPreview):
        return execute(request, body, undo=True)

    @router.post("/undo")
    def undo(request: Request, body: UndoCommit):
        return execute(request, body, write=True, undo=True)

    app.include_router(router)
