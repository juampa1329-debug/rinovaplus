"""Scentra field contract over institution-bound SQL configuration, without IO."""

import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import Field, field_validator

from app.institutional.auth import authorize
from app.institutional.db import audit, institution, one, record_operation, replay, uid
from app.institutional.models import Strict, public_url
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.parity_channels.policy import namespace
from tools.foundation_snapshot import quote_name

CATALOG = (
    Path(__file__).resolve().parents[3] / "docs/adaptation/sql/p2-channel-fields.json"
)


def contract():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


class AccountCreate(Strict):
    operation_id: str
    channel: Literal["whatsapp", "instagram", "facebook", "messenger", "tiktok"]
    display_name: str = Field(min_length=1, max_length=160)
    application_id: str | None = None
    issuer_profile: Literal[
        "meta_whatsapp",
        "facebook_login",
        "instagram_login",
        "tiktok_business",
        "tiktok_login_kit",
    ]
    client_id: str = Field(default="", max_length=128)
    api_version: str = Field(default="", max_length=20, pattern=r"^[A-Za-z0-9._-]*$")

    @field_validator("display_name")
    @classmethod
    def sql_name(cls, value):
        if len(value.encode("utf-16-le")) > 320:
            raise ValueError("display_name_too_long")
        return value

    @field_validator("client_id")
    @classmethod
    def ascii_client(cls, value):
        value = value.strip()
        if any(ord(char) < 33 or ord(char) > 126 for char in value):
            raise ValueError("invalid_client_id")
        return value


def compatible(channel, issuer):
    return issuer in {
        "whatsapp": {"meta_whatsapp"},
        "instagram": {"instagram_login", "facebook_login"},
        "facebook": {"facebook_login"},
        "messenger": {"facebook_login"},
        "tiktok": {"tiktok_business", "tiktok_login_kit"},
    }.get(channel, set())


class AccountEdit(Strict):
    operation_id: str
    revision: int = Field(ge=0)
    row_version: str = Field(pattern=r"^[0-9a-f]{16}$")
    application_version: str = Field(pattern=r"^[0-9a-f]{16}$")
    values: dict


def validate_field(field, value):
    kind = field.get("value_type")
    if kind == "string":
        if type(value) is not str:
            raise ValueError("invalid_field_type")
        value = value.strip()
        maximum = field.get("max_length")
        if maximum is not None and len(value.encode("utf-16-le")) // 2 > maximum:
            raise ValueError("field_too_long")
        if len(value) < (field.get("min_length") or 0) or any(
            ord(c) < 32 for c in value
        ):
            raise ValueError("invalid_field_value")
        if field.get("enum") and value not in field["enum"]:
            raise ValueError("invalid_field_option")
        if field.get("config_key", "").endswith("base_url"):
            public_url(value)
    elif kind == "string_array":
        if type(value) is not list or any(
            type(v) is not str
            or not v
            or any(c.isspace() or c == "," or ord(c) < 32 for c in v)
            for v in value
        ):
            raise ValueError("invalid_field_list")
        # Source save preserves ordering/case/duplicates; operational normalization is
        # separate.
    elif kind == "boolean":
        if type(value) is not bool:
            raise ValueError("invalid_field_type")
    elif kind == "integer":
        if type(value) is not int:
            raise ValueError("invalid_field_type")
        limits = field.get("range") or {}
        if value < limits.get("minimum", value) or value > limits.get("maximum", value):
            raise ValueError("field_out_of_range")
    else:
        raise ValueError("unsupported_field_type")
    return value


class Channels:
    def __init__(self, settings):
        self.settings = settings

    def created(self, cursor, identity):
        return {}

    def edited(self, cursor, identity):
        pass

    def catalog(self, authority):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "settings.channels.read")
        data = contract()
        return {
            "groups": data["groups"],
            "fields": [
                {
                    k: f.get(k)
                    for k in (
                        "id",
                        "group",
                        "label",
                        "config_key",
                        "input_type",
                        "options",
                        "field_kind",
                        "editable_in_p2",
                        "value_type",
                        "max_length",
                        "min_length",
                        "enum",
                        "range",
                        "requires_provider_action",
                    )
                }
                for f in data["fields"]
            ],
            "provider_operations_available": False,
        }

    def _item(self, c, identity):
        value = one(
            c,
            (
                "SELECT i.*,a.ClientId,a.RowVersion AS Applicat"
                "ionVersion FROM crm_channels2.Integration i JO"
                "IN crm_channels2.Application a ON a.Institutio"
                "nId=i.InstitutionId AND a.ApplicationId=i.Appl"
                "icationId WHERE i.InstitutionId=? AND i.Integr"
                "ationId=?"
            ),
            institution(self.settings),
            uid(identity),
        )
        if not value:
            raise HTTPException(404, "account_not_found")
        configured = one(
            c,
            (
                "SELECT Document,Revision FROM crm_access.Chann"
                "elSetting WHERE InstitutionId=? AND Integratio"
                "nId=?"
            ),
            institution(self.settings),
            uid(identity),
        )
        document = json.loads(configured["Document"]) if configured else {}
        groups = {
            g["id"]
            for g in contract()["groups"]
            if value["Channel"] in g["applies_to_channels"]
        }
        fields = {}
        for field in contract()["fields"]:
            if field["group"] == "webhooks":
                continue
            if field["group"] not in groups or field["field_kind"] in {
                "secret",
                "transient",
            }:
                continue
            mapping = field.get("p2_mapping") or {}
            storage = field.get("p2_storage") or {}
            if mapping.get("destination") == "existing_column":
                fields[field["id"]] = value.get(mapping["column"])
            elif mapping.get("destination") == "ChannelSetting JSON":
                fields[field["id"]] = document.get(mapping["p2_flat_json_key"])
            elif storage.get("column") in value:
                fields[field["id"]] = value[storage["column"]]
            else:
                fields[field["id"]] = None
        return {
            "id": uid(str(value["IntegrationId"])),
            "application_id": uid(str(value["ApplicationId"])),
            "channel": value["Channel"],
            "display_name": value["DisplayName"],
            "provider": value["Provider"],
            "revision": configured["Revision"] if configured else 0,
            "row_version": bytes(value["RowVersion"]).hex(),
            "application_version": bytes(value["ApplicationVersion"]).hex(),
            "fields": fields,
            "verified_status": value["VerifiedStatus"],
            "provider_operations_available": False,
        }

    def read(self, authority):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "settings.channels.read")
            identities = c.execute(
                (
                    "SELECT TOP(1000) IntegrationId FROM crm_channe"
                    "ls2.Integration WHERE InstitutionId=? ORDER BY"
                    " CreatedAt,IntegrationId"
                ),
                institution(self.settings),
            ).fetchall()
            result = [self._item(c, str(r[0])) for r in identities]
        return {"items": result}

    def create(self, authority, body):
        provider = "tiktok" if body.channel == "tiktok" else "meta"
        if not compatible(body.channel, body.issuer_profile):
            raise HTTPException(422, "application_channel_mismatch")
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.channels.write", recent=True
            )
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.create",
                body.channel,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            maximum = setting(c, self.settings, "budgets")["document"][
                "max_active_integrations"
            ]
            if (
                c.execute(
                    (
                        "SELECT COUNT(*) FROM crm_channels2.Integration"
                        " WHERE InstitutionId=?"
                    ),
                    institution(self.settings),
                ).fetchval()
                >= maximum
            ):
                raise HTTPException(409, "integration_capacity_reached")
            if body.application_id:
                app = one(
                    c,
                    (
                        "SELECT * FROM crm_channels2.Application WHERE "
                        "InstitutionId=? AND ApplicationId=? AND Provid"
                        "er=? AND State<>'retired'"
                    ),
                    institution(self.settings),
                    uid(body.application_id),
                    provider,
                )
                if not app:
                    raise HTTPException(422, "application_not_found")
                if app["IssuerProfile"] != body.issuer_profile or not compatible(
                    body.channel, app["IssuerProfile"]
                ):
                    raise HTTPException(422, "application_channel_mismatch")
                if body.client_id and body.client_id != app["ClientId"]:
                    raise HTTPException(409, "application_identity_immutable")
            else:
                client = body.client_id.strip()
                if not client:
                    raise HTTPException(422, "application_client_id_required")
                app = one(
                    c,
                    (
                        "SELECT * FROM crm_channels2.Application WHERE "
                        "InstitutionId=? AND Provider=? AND ClientId=? "
                        "AND IssuerProfile=?"
                    ),
                    institution(self.settings),
                    provider,
                    client,
                    body.issuer_profile,
                )
                if not app:
                    app = {
                        "ApplicationId": str(uuid4()),
                        "ClientId": client,
                        "IssuerProfile": body.issuer_profile,
                    }
                    c.execute(
                        (
                            "INSERT crm_channels2.Application(InstitutionId"
                            ",ApplicationId,Provider,ClientId,ApiVersion,Is"
                            "suerProfile,RedirectUri,EgressProfile,State,Cr"
                            "eatedAt,UpdatedAt) VALUES(?,?,?,?,?,?,'','not_"
                            "configured','draft',SYSUTCDATETIME(),SYSUTCDAT"
                            "ETIME())"
                        ),
                        institution(self.settings),
                        app["ApplicationId"],
                        provider,
                        client,
                        body.api_version,
                        app["IssuerProfile"],
                    )
            identity = str(uuid4())
            c.execute(
                (
                    "INSERT crm_channels2.Integration(InstitutionId"
                    ",IntegrationId,ApplicationId,Provider,Channel,"
                    "Environment,DisplayName,ApiVersion,DispatchMod"
                    "e,RequestedStatus,VerifiedStatus,ExternalNames"
                    "pace,CreatedAt,UpdatedAt) VALUES(?,?,?,?,?,'de"
                    "velopment',?,?,?,'disconnected','unverified',?"
                    ",SYSUTCDATETIME(),SYSUTCDATETIME())"
                ),
                institution(self.settings),
                identity,
                str(app["ApplicationId"]),
                provider,
                body.channel,
                body.display_name,
                body.api_version,
                "meta_cloud" if provider == "meta" else "tiktok_oauth",
                namespace(provider, app["ClientId"], app["IssuerProfile"]),
            )
            result = self._item(c, identity)
            issued = self.created(c, identity)
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.create",
                body.channel,
                digest,
                result,
            )
            audit(c, self.settings, actor["UserId"], "channels.create", identity)
        return {**result, **issued}

    def save(self, authority, identity, body):
        identity = uid(identity)
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.channels.write", recent=True
            )
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.edit",
                identity,
                body.model_dump(mode="json"),
            )
            if prior:
                return prior
            item = self._item(c, identity)
            if (item["revision"], item["row_version"], item["application_version"]) != (
                body.revision,
                body.row_version,
                body.application_version,
            ):
                raise HTTPException(409, "revision_conflict")
            groups = {
                g["id"]
                for g in contract()["groups"]
                if item["channel"] in g["applies_to_channels"]
            }
            allowed = {
                f["id"]: f
                for f in contract()["fields"]
                if f["group"] in groups
                and f.get("p2_write_allowed")
                and f["field_kind"] == "input"
                and f["group"] != "webhooks"
            }
            if not set(body.values) <= set(allowed):
                raise HTTPException(422, "field_not_editable")
            old = c.execute(
                (
                    "SELECT Document FROM crm_access.ChannelSetting"
                    " WHERE InstitutionId=? AND IntegrationId=?"
                ),
                institution(self.settings),
                identity,
            ).fetchval()
            document = json.loads(old) if old else {}
            updates = {}
            for field_id, raw in body.values.items():
                field = allowed[field_id]
                try:
                    value = validate_field(field, raw)
                except ValueError:
                    raise HTTPException(422, "invalid_channel_field") from None
                mapping = field["p2_mapping"]
                if mapping["destination"] == "ChannelSetting JSON":
                    document[mapping["p2_flat_json_key"]] = value
                    continue
                column = mapping["column"]
                if column == "ClientId":
                    if value != item["fields"].get(field_id):
                        raise HTTPException(409, "application_identity_immutable")
                    continue
                # Historical external identities must not silently move to another
                # account.
                if column in {"ExternalAccountId", "ParentExternalId"}:
                    previous = item["fields"].get(field_id)
                    if previous and previous != value:
                        raise HTTPException(409, "account_identity_immutable")
                    value = value or None
                if column in updates and updates[column] != value:
                    raise HTTPException(422, "conflicting_field_contexts")
                updates[column] = value
            if updates:
                c.execute(
                    "UPDATE crm_channels2.Integration SET "
                    + ",".join(quote_name(k) + "=?" for k in updates)
                    + (
                        ",UpdatedAt=SYSUTCDATETIME() WHERE InstitutionI"
                        "d=? AND IntegrationId=? AND RowVersion=?"
                    ),
                    *updates.values(),
                    institution(self.settings),
                    identity,
                    bytes.fromhex(body.row_version),
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "revision_conflict")
            text = json.dumps(document, ensure_ascii=False)
            if body.revision:
                c.execute(
                    (
                        "UPDATE crm_access.ChannelSetting SET Document="
                        "?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME"
                        "(),UpdatedBy=? WHERE InstitutionId=? AND Integ"
                        "rationId=? AND Revision=?"
                    ),
                    text,
                    actor["UserId"],
                    institution(self.settings),
                    identity,
                    body.revision,
                )
                if c.rowcount != 1:
                    raise HTTPException(409, "revision_conflict")
            else:
                c.execute(
                    (
                        "INSERT crm_access.ChannelSetting(InstitutionId"
                        ",IntegrationId,Document,Revision,UpdatedAt,Upd"
                        "atedBy) VALUES(?,?,?,1,SYSUTCDATETIME(),?)"
                    ),
                    institution(self.settings),
                    identity,
                    text,
                    actor["UserId"],
                )
            self.edited(c, identity)
            result = self._item(c, identity)
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "channels.edit",
                identity,
                digest,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "channels.edit",
                identity,
                fields=sorted(body.values),
                revision=body.revision + 1,
            )
        return result


def install_channels(app, settings, service=None):
    service = service or Channels(settings)

    @app.get("/api/institution/channels/catalog")
    def catalog(request: Request):
        return service.catalog(request.state.authority)

    @app.get("/api/institution/channels")
    def accounts(request: Request):
        return service.read(request.state.authority)

    @app.post("/api/institution/channels")
    def create(request: Request, body: AccountCreate):
        return service.create(request.state.authority, body)

    @app.put("/api/institution/channels/{identity}")
    def save(request: Request, identity: str, body: AccountEdit):
        return service.save(request.state.authority, identity, body)
