"""Explicit ADR-006 local-copy repository. No schema creation or core writes."""

import hashlib
import json
from contextlib import contextmanager
from typing import Annotated, Literal
from uuid import UUID

import pyodbc
from fastapi import FastAPI, HTTPException
from pydantic import Field, model_validator

from app.config import Settings
from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.catalog.infrastructure.sql_reader import SqlCatalogReader
from app.modules.contacts.domain.models import InstitutionalProfile
from app.schemas import LocalModel
from app.sql_target import connection_string, verify_identity

Identifier = Annotated[
    str,
    Field(
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    ),
]
Revision = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$")]
Short = Annotated[str, Field(max_length=100)]


class Contact(LocalModel):
    id: Identifier
    name: Short
    phone: Annotated[str, Field(max_length=40)]
    city: Short
    programId: Annotated[int, Field(ge=-2147483648, le=2147483647)] | None = None
    program: Annotated[str, Field(max_length=200)]
    schedule: Short
    stage: Annotated[str, Field(min_length=1, max_length=60)]
    tags: Annotated[str, Field(max_length=1000)]
    notes: Annotated[str, Field(max_length=1000)]
    type: Short
    interests: Annotated[str, Field(max_length=300)]
    institutionalProfile: InstitutionalProfile | None = None
    customValues: Annotated[
        dict[
            Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,39}$")],
            Annotated[str, Field(max_length=500)],
        ],
        Field(max_length=100),
    ]

    @model_validator(mode="after")
    def normalize(self):
        self.id = str(UUID(self.id))
        self.name, self.phone, self.stage = (
            self.name.strip(),
            self.phone.strip(),
            self.stage.strip(),
        )
        if not (self.name or self.phone) or not self.stage:
            raise ValueError("A contact identity and stage are required")
        if {"constructor", "prototype"} & self.customValues.keys():
            raise ValueError("Invalid field key")
        if self.programId is None and self.program:
            raise ValueError("Select a program from the catalog")
        return self


class Mutation(LocalModel):
    operationId: Identifier
    expectedRevision: Revision


class ContactMutation(Mutation):
    client: Contact
    conversationId: Identifier


class ConversationMutation(Mutation):
    state: Literal["open", "waiting", "closed"]
    priority: Literal["low", "normal", "high", "urgent"]
    assignee: Short = ""
    mode: Literal["human", "ai"]
    unread: bool
    readThroughSequence: (
        Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,18})$")] | None
    ) = None
    assessmentChanged: bool = False
    leadScore: Annotated[int, Field(ge=0, le=100, strict=True)] | None = None
    temperature: Literal["cold", "warm", "hot"] | None = None


class MessageMutation(Mutation):
    messageId: Identifier
    body: Annotated[str, Field(max_length=4000)]
    mediaId: Identifier | None = None
    delivery: Literal["local", "external"] = "local"
    identityId: Identifier | None = None

    @model_validator(mode="after")
    def nonblank(self):
        self.body = self.body.strip()
        if not self.body and not self.mediaId:
            raise ValueError("Message is empty")
        if (self.delivery == "external") != bool(self.identityId):
            raise ValueError("External delivery requires an explicit identity")
        return self


CONTACT_COLUMNS = (
    "ContactId,Name,Phone,City,ProgramId,Program,Schedule,St"
    "age,Tags,Notes,Type,Interests,CustomValues"
)
CONTACT_KEYS = (
    "id",
    "name",
    "phone",
    "city",
    "programId",
    "program",
    "schedule",
    "stage",
    "tags",
    "notes",
    "type",
    "interests",
    "customValues",
)
STATES = {"open": "Abierta", "waiting": "En espera", "closed": "Cerrada"}
PRIORITIES = {"low": "Baja", "normal": "Normal", "high": "Alta", "urgent": "Urgente"}


def payload_hash(action: str, entity_id: str, body: Mutation) -> bytes:
    data = body.model_dump(exclude={"operationId", "expectedRevision"})
    if isinstance(body, MessageMutation) and body.mediaId is None:
        data.pop("mediaId", None)
    if isinstance(body, MessageMutation) and body.delivery == "local":
        data.pop("delivery", None)
        data.pop("identityId", None)
    if isinstance(body, ConversationMutation):
        if body.readThroughSequence is None:
            data.pop("readThroughSequence", None)
        if not body.assessmentChanged:
            for key in ("assessmentChanged", "leadScore", "temperature"):
                data.pop(key, None)
    # Preserve exact pre-C2 replay hashes; an omitted profile is not a clear.
    if (
        isinstance(body, ContactMutation)
        and data["client"].get("institutionalProfile") is None
    ):
        data["client"].pop("institutionalProfile", None)
    value = json.dumps(
        [action, str(UUID(entity_id)), data],
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(value.encode("utf-8")).digest()


def verify_target(cursor, settings: Settings):
    try:
        if settings.mode == "local_foundation":
            from app.foundation import verify

            verify(cursor, settings)
            return
        verify_identity(cursor, settings)
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise CatalogUnavailable() from error
    row = cursor.execute("""SELECT CONVERT(nvarchar(128),value)
         FROM sys.extended_properties
         WHERE class=3 AND major_id=SCHEMA_ID(N'crm')
         AND name=N'crm.contract'""").fetchone()
    if row is None or tuple(row) != ("ADR-006-v1",):
        raise CatalogUnavailable()
    from app.sql_workspace_shape import SHAPE_SQL

    shape = cursor.execute(SHAPE_SQL).fetchone()
    if shape is None or not shape[0]:
        raise CatalogUnavailable()


class SqlWorkspace:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def foundation(self):
        return self.settings.mode == "local_foundation"

    @contextmanager
    def transaction(self, write=False):
        connection = None
        cursor = None
        try:
            connection = pyodbc.connect(
                connection_string(self.settings), timeout=5, autocommit=False
            )
            connection.timeout = 10
            cursor = connection.cursor()
            # ODBC autocommit=False owns the transaction; BEGIN would nest it.
            cursor.execute("SET XACT_ABORT ON;")
            # ponytail: one global revision/lock for this local low-volume workspace.
            lock = cursor.execute(
                """DECLARE @result int;
                EXEC @result=sys.sp_getapplock @Resource=N'crm.local.commit',
                @LockMode=?, @LockOwner='Transaction', @LockTimeout=5000;
                SELECT @result;""",
                "Exclusive" if write else "Shared",
            ).fetchone()
            if lock is None or lock[0] < 0:
                raise CatalogUnavailable()
            verify_target(cursor, self.settings)
            yield cursor
            connection.commit()
        except BaseException:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()

    @staticmethod
    def revision(cursor):
        revision = cursor.execute(
            "SELECT COALESCE(MAX(Revision),0) FROM crm.Operation"
        ).fetchone()[0]
        if cursor.execute("SELECT OBJECT_ID(N'crm_channels.Audit')").fetchone()[0]:
            revision += cursor.execute(
                "SELECT COUNT_BIG(*) FROM crm_channels.Audit WHERE Action IN('incoming_message','admissions_reply','admissions_handoff')"
            ).fetchone()[0]
        return str(revision)

    def snapshot(self, cursor):
        rows = cursor.execute(
            f"SELECT TOP (501) {CONTACT_COLUMNS} "
            "FROM crm.Contact ORDER BY CreatedAt,ContactId"
        ).fetchall()
        if len(rows) > 500:
            raise HTTPException(503, "workspace_limit_reached")
        clients = []
        for row in rows:
            client = dict(zip(CONTACT_KEYS, row, strict=True))
            client["id"] = str(client["id"]).lower()
            client["customValues"] = json.loads(client["customValues"])
            clients.append(client)
        from app.modules.contacts.api.router import decorate

        if not self.foundation:
            decorate(cursor, clients)
        from app.modules.contacts.application.merge import relations

        contact_groups = [] if self.foundation else relations(cursor)
        threads = []
        for row in cursor.execute(
            (
                "SELECT ConversationId,ContactId,State,Priority,Assignee"
                ",ControlMode,Unread FROM crm.Conversation ORDER BY Crea"
                "tedAt,ConversationId"
            )
        ).fetchall():
            threads.append(
                {
                    "id": str(row[0]).lower(),
                    "clientId": str(row[1]).lower(),
                    "channel": "Local",
                    "mode": row[5],
                    "unread": bool(row[6]),
                    "messages": [],
                    "workflow": {
                        "state": STATES[row[2]],
                        "priority": PRIORITIES[row[3]],
                        "assignee": row[4] or "Sin asignar",
                        "revision": 0,
                        "tasks": [],
                        "events": [],
                    },
                }
            )
        by_id = {thread["id"]: thread for thread in threads}
        if (
            not self.foundation
            and cursor.execute(
                "SELECT OBJECT_ID(N'crm_channels.ExternalIdentity')"
            ).fetchone()[0]
        ):
            labels = {
                "whatsapp": "WhatsApp",
                "messenger": "Messenger",
                "instagram": "Instagram",
                "facebook": "Facebook",
                "tiktok": "TikTok",
            }
            for linked in cursor.execute(
                "SELECT ConversationId,Channel FROM crm_channels.ExternalIdentity"
            ).fetchall():
                if str(linked[0]).lower() in by_id:
                    by_id[str(linked[0]).lower()]["channel"] = labels[linked[1]]
        messages = cursor.execute(
            (
                "SELECT TOP (2001) MessageId,ConversationId,Body,Directi"
                "on FROM crm.Message ORDER BY Sequence"
            )
        ).fetchall()
        if len(messages) > 2000:
            raise HTTPException(503, "workspace_limit_reached")
        for row in messages:
            by_id[str(row[1]).lower()]["messages"].append(
                {"id": str(row[0]).lower(), "body": row[2], "direction": row[3]}
            )
        return {
            "clients": clients,
            "threads": threads,
            "revision": self.revision(cursor),
            "contactGroups": contact_groups,
        }

    def read(self):
        with self.transaction() as cursor:
            return self.snapshot(cursor)

    def mutate(self, action: str, entity_id: str, body: Mutation, *, compact=False):
        with self.transaction(write=True) as cursor:
            return self.mutate_in(cursor, action, entity_id, body, compact=compact)

    def mutate_in(
        self, cursor, action, entity_id, body, *, compact=False, capture_identity=True
    ):
        """Execute the existing writer in its caller-owned transaction."""
        if self.foundation:
            # Reject unsupported requests even on idempotent replay, before SQL.
            unsupported = (
                isinstance(body, ContactMutation)
                and (
                    body.client.programId is not None
                    or body.client.institutionalProfile is not None
                )
                or isinstance(body, ConversationMutation)
                and (
                    body.mode != "human"
                    or body.assignee
                    or body.assessmentChanged
                    or body.leadScore is not None
                    or body.temperature is not None
                    or body.readThroughSequence is not None
                )
                or isinstance(body, MessageMutation)
                and (
                    body.mediaId is not None
                    or body.delivery != "local"
                    or body.identityId is not None
                )
            )
            if unsupported:
                raise HTTPException(503, "foundation_capability_unavailable")
            capture_identity = False
        digest = payload_hash(action, entity_id, body)
        previous = cursor.execute(
            "SELECT PayloadHash,Revision FROM crm.Operation WHERE OperationId=?",
            body.operationId,
        ).fetchone()
        if previous is not None:
            if bytes(previous[0]) != digest:
                raise HTTPException(409, "operation_changed")
            return (
                {"revision": self.revision(cursor)}
                if compact
                else self.snapshot(cursor)
            )
        if body.expectedRevision != self.revision(cursor):
            raise HTTPException(409, "workspace_changed")
        message_id = None
        prior_identity = None
        if isinstance(body, ContactMutation):
            client = body.client
            if str(UUID(entity_id)) != client.id:
                raise HTTPException(422, "client_id_mismatch")
            contact_id, conversation_id = client.id, body.conversationId
            if capture_identity and action != "create_contact":
                from app.modules.contacts.application.merge import before_write

                prior_identity = before_write(cursor, contact_id)
            from app.modules.crm_configuration.application.service import (
                validate_contact,
            )

            previous = None
            if action != "create_contact":
                previous_row = cursor.execute(
                    "SELECT Stage,Tags,CustomValues FROM crm.Contact WHERE ContactId=?",
                    contact_id,
                ).fetchone()
                if previous_row is not None:
                    previous = {
                        "stage": previous_row[0],
                        "tags": previous_row[1],
                        "customValues": json.loads(previous_row[2]),
                    }
            validate_contact(cursor, client, previous, foundation=self.foundation)
            if client.programId is not None:
                program = cursor.execute(
                    ("SELECT NombrePrograma FROM dbo.ACProgramas WHERE Id_Programa=?"),
                    client.programId,
                ).fetchone()
                if program is None or (program[0] or "") != client.program:
                    raise HTTPException(422, "invalid_program")
            values = [getattr(client, key) for key in CONTACT_KEYS[1:-1]] + [
                json.dumps(client.customValues, ensure_ascii=False)
            ]
            if action == "create_contact":
                if cursor.execute(
                    "SELECT ContactId FROM crm.Contact WHERE ContactId=?",
                    contact_id,
                ).fetchone():
                    raise HTTPException(409, "client_id_exists")
                cursor.execute(
                    f"INSERT crm.Contact ({CONTACT_COLUMNS}) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    contact_id,
                    *values,
                )
                cursor.execute(
                    (
                        "INSERT crm.Conversation (ConversationId,ContactId,State"
                        ",Priority,Assignee,ControlMode,Unread) VALUES (?,?,'ope"
                        "n','normal',NULL,'human',0)"
                    ),
                    conversation_id,
                    contact_id,
                )
            else:
                relationship = cursor.execute(
                    "SELECT ConversationId FROM crm.Conversation WHERE ContactId=?",
                    contact_id,
                ).fetchone()
                if relationship is None:
                    raise HTTPException(404, "client_not_found")
                if str(relationship[0]).lower() != str(UUID(conversation_id)):
                    raise HTTPException(409, "conversation_changed")
                cursor.execute(
                    (
                        "UPDATE crm.Contact SET Name=?,Phone=?,City=?,ProgramId="
                        "?,Program=?,Schedule=?,Stage=?,Tags=?,Notes=?,Type=?,In"
                        "terests=?,CustomValues=?,UpdatedAt=SYSUTCDATETIME() WHE"
                        "RE ContactId=?"
                    ),
                    *values,
                    contact_id,
                )
            from app.modules.contacts.api.router import save_profile

            if not self.foundation:
                save_profile(cursor, client)
        else:
            conversation_id = str(UUID(entity_id))
            thread = cursor.execute(
                (
                    "SELECT ContactId,State,ControlMode FROM crm.Conversatio"
                    "n WHERE ConversationId=?"
                ),
                conversation_id,
            ).fetchone()
            if thread is None:
                raise HTTPException(404, "conversation_not_found")
            contact_id = str(thread[0])
            if isinstance(body, ConversationMutation):
                from app.modules.inbox.application.state import (
                    change_control,
                    installed,
                    mark_read,
                    save_assessment,
                )

                if not self.foundation:
                    change_control(
                        cursor,
                        conversation_id,
                        (thread[2], thread[1]),
                        (body.mode, body.state),
                    )
                unread = body.unread
                if not self.foundation and not unread and installed(cursor):
                    unread = mark_read(
                        cursor, conversation_id, body.readThroughSequence
                    )
                if body.assessmentChanged:
                    save_assessment(
                        cursor, conversation_id, body.leadScore, body.temperature
                    )
                guarded = cursor.execute(
                    "IF SCHEMA_ID(N'crm_inbox') IS NOT NULL "
                    "SELECT Assignee FROM crm.Conversation WHERE ConversationId=? "
                    "ELSE SELECT ?",
                    conversation_id,
                    body.assignee,
                ).fetchone()
                if guarded is not None and (guarded[0] or "") != body.assignee:
                    raise HTTPException(422, "use_stable_assignment")
                cursor.execute(
                    (
                        "UPDATE crm.Conversation SET State=?,Priority=?,Assignee"
                        "=?,ControlMode=?,Unread=?,UpdatedAt=SYSUTCDATETIME() WH"
                        "ERE ConversationId=?"
                    ),
                    body.state,
                    body.priority,
                    body.assignee or None,
                    body.mode,
                    unread,
                    conversation_id,
                )
            elif isinstance(body, MessageMutation):
                if thread[1] == "closed" or thread[2] != "human":
                    raise HTTPException(409, "human_open_conversation_required")
                message_id = body.messageId
                media = None
                if body.mediaId:
                    from app.modules.inbox.application.media import attachment

                    channel = None
                    if body.delivery == "external":
                        identity = cursor.execute(
                            "SELECT Channel FROM crm_channels.ExternalIdentity WHERE IdentityId=? AND ConversationId=?",
                            body.identityId,
                            conversation_id,
                        ).fetchone()
                        if not identity:
                            raise HTTPException(409, "channel_identity_changed")
                        channel = identity[0]
                    media = attachment(
                        cursor,
                        conversation_id,
                        body.mediaId,
                        body.delivery,
                        channel,
                        body.body,
                    )
                cursor.execute(
                    (
                        "INSERT crm.Message (MessageId,ConversationId,Body,Direc"
                        "tion) VALUES (?,?,?,'outgoing')"
                    ),
                    message_id,
                    conversation_id,
                    body.body or f"[{media['kind']}]",
                )
                cursor.execute(
                    (
                        "UPDATE crm.Conversation SET UpdatedAt=SYSUTCDATETIME() "
                        "WHERE ConversationId=?"
                    ),
                    conversation_id,
                )
                from app.modules.channels.workers import enqueue_message

                if media:
                    from app.modules.inbox.application.media import link

                    link(cursor, conversation_id, body.mediaId, message_id)

                if body.delivery == "external":
                    enqueue_message(
                        cursor,
                        conversation_id,
                        message_id,
                        body.body,
                        body.identityId,
                        body.mediaId,
                    )
        cursor.execute(
            (
                "INSERT crm.Operation (OperationId,Action,PayloadHash,Co"
                "ntactId,ConversationId,MessageId,Actor) VALUES (?,?,?,?"
                ",?,?,'local-operator')"
            ),
            body.operationId,
            action,
            digest,
            contact_id,
            conversation_id,
            message_id,
        )
        if prior_identity is not None:
            from app.modules.contacts.application.merge import after_write

            after_write(cursor, prior_identity, contact_id, body.operationId, digest)
        return {"revision": self.revision(cursor)} if compact else self.snapshot(cursor)


class LocalCopyCatalogReader(SqlCatalogReader):
    """Fixed catalog projections under the authorized local-copy guard."""

    def _read(self, sql, limit, offset, filters=()):
        try:
            with SqlWorkspace(self._settings).transaction() as cursor:
                return cursor.execute(sql, *filters, offset, limit).fetchmany(limit)
        except pyodbc.Error as error:
            raise CatalogUnavailable() from error


def matches_client(
    client,
    query="",
    stage="",
    tag="",
    city="",
    contact_type="",
    program_id=None,
    program="",
):
    def normalize(value):
        return str(value or "").strip().lower()

    return (
        (not stage or client["stage"] == stage)
        and (
            not normalize(tag)
            or normalize(tag)
            in [normalize(value) for value in client["tags"].split(",")]
        )
        and (not normalize(city) or normalize(client["city"]) == normalize(city))
        and (
            not normalize(contact_type)
            or normalize(client["type"]) == normalize(contact_type)
        )
        and (
            program_id is None
            and not program
            or program_id is not None
            and client["programId"] == program_id
            or client["programId"] is None
            and bool(normalize(program))
            and normalize(client["program"]) == normalize(program)
        )
        and normalize(query)
        in " ".join(str(client[key]) for key in ("name", "phone")).lower()
    )


def install_sql_workspace(application: FastAPI):
    application.state.sql_workspace = SqlWorkspace(application.state.settings)
