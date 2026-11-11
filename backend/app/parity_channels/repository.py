"""Institution-bound local configuration and safe legacy projections."""

import hmac
import json
import uuid

from fastapi import HTTPException

from app.parity_channels.guard import transaction
from app.parity_channels.policy import COLUMNS, canonical, namespace
from tools.foundation_snapshot import quote_name

PROJECTIONS = {
    "applications": (
        "Application",
        "ApplicationId",
        (
            "ApplicationId",
            "Provider",
            "ClientId",
            "ApiVersion",
            "IssuerProfile",
            "RedirectUri",
            "EgressProfile",
            "State",
            "RowVersion",
        ),
    ),
    "integrations": (
        "Integration",
        "IntegrationId",
        (
            "IntegrationId",
            "ApplicationId",
            "Provider",
            "Channel",
            "Environment",
            "DisplayName",
            "ExternalAccountId",
            "ParentExternalId",
            "ApiVersion",
            "DispatchMode",
            "RequestedStatus",
            "VerifiedStatus",
            "InitialStageKey",
            "InitialStageConfigHash",
            "RowVersion",
        ),
    ),
    "identities": (
        "ExternalIdentity",
        "IdentityId",
        ("IdentityId", "IntegrationId", "ExternalId", "ContactId", "ConversationId"),
    ),
    "comments": (
        "SocialComment",
        "CommentId",
        (
            "CommentId",
            "IntegrationId",
            "ExternalId",
            "AuthorExternalId",
            "Body",
            "ReceivedAt",
        ),
    ),
    **{
        key: (
            table,
            idcol,
            tuple(c for c in COLUMNS["crm_channels2." + table] if c != "InstitutionId"),
        )
        for key, table, idcol in (
            ("secrets", "SecretVersion", "SecretId"),
            ("receipts", "WebhookReceipt", "ReceiptId"),
            ("events", "WebhookEvent", "EventId"),
            ("messages", "ExternalMessage", "ExternalMessageId"),
            ("jobs", "SendJob", "QueueId"),
            ("bindings", "LegacyBinding", "BindingId"),
        )
    },
}


def result_row(columns, row):
    return {
        c: bytes(v).hex()
        if isinstance(v, bytes)
        else str(v).lower()
        if isinstance(v, uuid.UUID)
        else v
        for c, v in zip(columns, row, strict=True)
    }


class Repository:
    def __init__(self, settings):
        self.settings = settings
        self.institution = settings.ticket["context"][0][1]

    def read(self, kind, entity=None, limit=50, after=None):
        table, pk, columns = PROJECTIONS[kind]
        where = "InstitutionId=?"
        params = [self.institution]
        if entity is not None:
            where += " AND " + quote_name(pk) + "=?"
            params.append(str(entity))
        if after is not None:
            where += " AND " + quote_name(pk) + ">?"
            params.append(str(after))
        with transaction(self.settings) as cursor:
            rows = cursor.execute(
                "SELECT TOP (?) "
                + ",".join(map(quote_name, columns))
                + " FROM crm_channels2."
                + quote_name(table)
                + " WHERE "
                + where
                + " ORDER BY "
                + quote_name(pk),
                limit,
                *params,
            ).fetchall()
            values = [result_row(columns, r) for r in rows]
        if entity is not None:
            if not values:
                raise HTTPException(404, "entity_not_found")
            return values[0]
        return {
            "items": values,
            "next": str(rows[-1][columns.index(pk)]) if len(rows) == limit else None,
        }

    def operation(self, operation):
        with transaction(self.settings) as cursor:
            row = cursor.execute(
                (
                    "SELECT Status,ResultCode,ResultMetadata FROM "
                    "crm_channels2.ProviderOperation WHERE "
                    "InstitutionId=? AND OperationId=?"
                ),
                self.institution,
                str(operation),
            ).fetchone()
            if not row:
                raise HTTPException(404, "operation_not_found")
            return {"status": row[0], "code": row[1], "result": json.loads(row[2])}

    def write(self, action, payload, operation, entity=None, revision=None):
        allowed = {
            "create_application": {
                "Provider",
                "ClientId",
                "ApiVersion",
                "IssuerProfile",
                "RedirectUri",
            },
            "create_integration": {
                "ApplicationId",
                "Channel",
                "DisplayName",
                "Environment",
                "ExternalAccountId",
                "ParentExternalId",
                "ApiVersion",
            },
            "edit_application": {"ApiVersion"},
            "edit_integration": {"DisplayName", "ApiVersion"},
        }
        if action not in allowed or set(payload) != allowed[action]:
            raise HTTPException(422, "invalid_configuration_fields")
        data = payload.copy()
        operation = str(operation)
        entity = str(entity) if entity else None
        key = bytes.fromhex(self.settings.review["operation_key"])
        digest = hmac.digest(key, canonical([action, entity, revision, data]), "sha256")
        effect = hmac.digest(
            key, canonical(["local_effect", action, entity, revision, data]), "sha256"
        )
        with transaction(self.settings, write=True) as cursor:
            prior = cursor.execute(
                (
                    "SELECT RequestDigest,Status,ResultMetadata FROM "
                    "crm_channels2.ProviderOperation WHERE "
                    "InstitutionId=? AND OperationId=?"
                ),
                self.institution,
                operation,
            ).fetchone()
            if prior:
                if not hmac.compare_digest(bytes(prior[0]), digest):
                    raise HTTPException(409, "operation_payload_conflict")
                if prior[1] != "confirmed":
                    raise HTTPException(409, "operation_requires_reconciliation")
                return json.loads(prior[2])
            table = "Application" if action.endswith("application") else "Integration"
            pk = table + "Id"
            target = entity or str(uuid.uuid4())
            if action == "create_application":
                app = target
                if cursor.execute(
                    (
                        "SELECT 1 FROM crm_channels2.Application WHERE "
                        "InstitutionId=? AND Provider=? AND ClientId=? AND "
                        "IssuerProfile=?"
                    ),
                    self.institution,
                    data["Provider"],
                    data["ClientId"],
                    data["IssuerProfile"],
                ).fetchone():
                    raise HTTPException(409, "application_identity_exists")
            elif action == "create_integration":
                app = str(data.pop("ApplicationId"))
                row = cursor.execute(
                    (
                        "SELECT Provider,ClientId,IssuerProfile FROM "
                        "crm_channels2.Application WHERE InstitutionId=? "
                        "AND ApplicationId=?"
                    ),
                    self.institution,
                    app,
                ).fetchone()
                if not row:
                    raise HTTPException(404, "application_not_found")
                channel = data["Channel"]
                provider = "tiktok" if channel == "tiktok" else "meta"
                if row[0] != provider:
                    raise HTTPException(422, "application_channel_mismatch")
                issuers = {
                    "whatsapp": {"meta_whatsapp"},
                    "tiktok": {"tiktok_business"},
                    "facebook": {"facebook_login"},
                    "messenger": {"facebook_login"},
                    "instagram": {"facebook_login", "instagram_login"},
                }
                if row[2] not in issuers[channel]:
                    raise HTTPException(422, "application_issuer_mismatch")
                data.update(
                    ApplicationId=app,
                    Provider=provider,
                    ExternalNamespace=namespace(provider, row[1], row[2]),
                    DispatchMode="disabled",
                    RequestedStatus="disconnected",
                    VerifiedStatus="unverified",
                )
                if (
                    data["ExternalAccountId"] is not None
                    and cursor.execute(
                        (
                            "SELECT 1 FROM crm_channels2.Integration WHERE "
                            "InstitutionId=? AND Provider=? AND Channel=? AND "
                            "ExternalNamespace=? AND ExternalAccountId=?"
                        ),
                        self.institution,
                        provider,
                        channel,
                        data["ExternalNamespace"],
                        data["ExternalAccountId"],
                    ).fetchone()
                ):
                    raise HTTPException(409, "external_account_exists")
            else:
                row = cursor.execute(
                    "SELECT "
                    + ("ApplicationId" if table == "Integration" else pk)
                    + ",RowVersion FROM crm_channels2."
                    + table
                    + " WHERE InstitutionId=? AND "
                    + pk
                    + "=?",
                    self.institution,
                    target,
                ).fetchone()
                if not row:
                    raise HTTPException(404, "entity_not_found")
                if bytes(row[1]).hex() != revision:
                    raise HTTPException(409, "stale_revision")
                app = str(row[0])
            if cursor.execute(
                (
                    "SELECT 1 FROM crm_channels2.ProviderOperation "
                    "WHERE InstitutionId=? AND ApplicationId=? AND "
                    "Action=? AND EffectKey=?"
                ),
                self.institution,
                app,
                action,
                effect,
            ).fetchone():
                raise HTTPException(409, "effect_already_recorded")
            if action.startswith("create_"):
                if table == "Application":
                    data.update(EgressProfile="disabled-c12", State="draft")
                data = {"InstitutionId": self.institution, pk: target, **data}
                cursor.execute(
                    "INSERT crm_channels2."
                    + table
                    + "("
                    + ",".join(map(quote_name, data))
                    + ",CreatedAt,UpdatedAt) VALUES("
                    + ",".join("?" for _ in data)
                    + ",SYSUTCDATETIME(),SYSUTCDATETIME())",
                    *data.values(),
                )
            else:
                cursor.execute(
                    "UPDATE crm_channels2."
                    + table
                    + " SET "
                    + ",".join(quote_name(c) + "=?" for c in data)
                    + ",UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND "
                    + pk
                    + "=? AND RowVersion=?",
                    *data.values(),
                    self.institution,
                    target,
                    bytes.fromhex(revision),
                )
                if cursor.rowcount != 1:
                    raise HTTPException(409, "stale_revision")
            rev = bytes(
                cursor.execute(
                    "SELECT RowVersion FROM crm_channels2."
                    + table
                    + " WHERE InstitutionId=? AND "
                    + pk
                    + "=?",
                    self.institution,
                    target,
                ).fetchval()
            ).hex()
            result = {
                "id": target.lower(),
                "revision": rev,
                "operation": operation.lower(),
                "status": "saved_local_draft",
            }
            cursor.execute(
                (
                    "INSERT crm_channels2.ProviderOperation(Institution"
                    "Id,OperationId,ApplicationId,IntegrationId,ActorRe"
                    "f,Action,RequestDigest,Status,ResultCode,ResultMet"
                    "adata,CreatedAt,CompletedAt,EffectKey) VALUES(?,?,"
                    "?,?,?,?,?,'confirmed','local_only',?,SYSUTCDATETIM"
                    "E(),SYSUTCDATETIME(),?)"
                ),
                self.institution,
                operation,
                app,
                target if table == "Integration" else None,
                "local-owner:SQL-C12",
                action,
                digest,
                canonical(result).decode(),
                effect,
            )
            cursor.execute(
                (
                    "INSERT crm_channels2.Audit(InstitutionId,AuditId,I"
                    "ntegrationId,ActorRef,Action,OperationId,ResultCod"
                    "e,CreatedAt) VALUES(?,?,?,'local-"
                    "owner:SQL-C12',?,?,'local_only',SYSUTCDATETIME())"
                ),
                self.institution,
                str(uuid.uuid4()),
                target if table == "Integration" else None,
                action,
                operation,
            )
            return result
