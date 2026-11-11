"""One endpoint identity for configuration, links and one-time secret rotation."""

from uuid import UUID, uuid5

from fastapi import HTTPException, Request
from pydantic import Field

from app.institutional.auth import authorize
from app.institutional.crypto import token
from app.institutional.db import (
    audit,
    institution,
    one,
    record_operation,
    replay,
    save_secret,
    uid,
    utc,
)
from app.institutional.models import Strict, Webhook, Webhooks, public_url
from app.institutional.settings import setting
from app.institutional.store import transaction


class EndpointCreate(Strict):
    operation_id: str
    provider: str = Field(pattern=r"^(meta|whatsapp|facebook|instagram|tiktok)$")
    integration_ids: list[str] = Field(min_length=1, max_length=50)
    callback_url: str = Field(default="", max_length=2048)
    signature_required: bool = True


class EndpointRotate(Strict):
    operation_id: str


def endpoint_id(settings, key):
    return str(uuid5(UUID(institution(settings)), "webhook/" + key))


def accounts(cursor, settings, provider, identities):
    found = []
    for identity in identities:
        value = one(
            cursor,
            "SELECT IntegrationId,ApplicationId,Provider,Channel,ExternalAccountId FROM crm_channels2.Integration WHERE InstitutionId=? AND IntegrationId=?",
            institution(settings),
            uid(identity),
        )
        if not value or not (
            provider == value["Provider"]
            or provider == value["Channel"]
            or provider == "facebook"
            and value["Channel"] == "messenger"
        ):
            raise HTTPException(422, "webhook_integration_mismatch")
        found.append(value)
    if not found or len({str(v["ApplicationId"]).lower() for v in found}) != 1:
        raise HTTPException(422, "webhook_single_application_required")
    return found


def synchronized_endpoint(cursor, settings, endpoint, *, creating=False):
    identities = accounts(
        cursor, settings, endpoint["provider"], endpoint["integration_ids"]
    )
    application = uid(str(identities[0]["ApplicationId"]))
    identity = endpoint_id(settings, endpoint["key"])
    current = one(
        cursor,
        "SELECT * FROM crm_channels2.WebhookEndpoint WHERE InstitutionId=? AND EndpointId=?",
        institution(settings),
        identity,
    )
    provider = "tiktok" if endpoint["provider"] == "tiktok" else "meta"
    duplicate = cursor.execute(
        "SELECT 1 FROM crm_channels2.WebhookEndpoint WHERE InstitutionId=? AND ApplicationId=? AND ChannelSelector=? AND EndpointId<>?",
        institution(settings),
        application,
        endpoint["provider"],
        identity,
    ).fetchone()
    if duplicate:
        raise HTTPException(409, "webhook_application_selector_exists")
    if current:
        if (
            uid(str(current["ApplicationId"])) != application
            or current["Provider"] != provider
        ):
            raise HTTPException(409, "webhook_application_immutable")
        cursor.execute(
            "UPDATE crm_channels2.WebhookEndpoint SET ChannelSelector=?,SignatureRequired=1,IsActive=0,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND EndpointId=?",
            endpoint["provider"],
            institution(settings),
            identity,
        )
    elif creating:
        cursor.execute(
            "INSERT crm_channels2.WebhookEndpoint(InstitutionId,EndpointId,ApplicationId,Provider,ChannelSelector,EndpointKey,SignatureProfile,SignatureRequired,IsActive,CreatedAt,UpdatedAt) VALUES(?,?,?,?,?,?,'required_not_activated',1,0,SYSUTCDATETIME(),SYSUTCDATETIME())",
            institution(settings),
            identity,
            application,
            provider,
            endpoint["provider"],
            endpoint["key"],
        )
    else:
        raise HTTPException(422, "webhook_server_owned_identity")
    cursor.execute(
        "UPDATE crm_channels2.EndpointIntegration SET IsActive=0 WHERE InstitutionId=? AND EndpointId=?",
        institution(settings),
        identity,
    )
    for account in identities:
        external = account["ExternalAccountId"]
        if not external:
            continue  # No fabricated routing identity before the real ID is configured.
        if not cursor.execute(
            "SELECT 1 FROM crm_channels2.EndpointIntegration WHERE InstitutionId=? AND EndpointId=? AND IntegrationId=? AND RouteKind='configured_account' AND ExternalId=?",
            institution(settings),
            identity,
            account["IntegrationId"],
            external,
        ).fetchone():
            cursor.execute(
                "INSERT crm_channels2.EndpointIntegration(InstitutionId,EndpointId,IntegrationId,ApplicationId,RouteKind,ExternalId,IsActive,CreatedAt) VALUES(?,?,?,?,'configured_account',?,0,SYSUTCDATETIME())",
                institution(settings),
                identity,
                account["IntegrationId"],
                application,
                external,
            )
    return identity


def synchronize(cursor, settings, document):
    current = setting(cursor, settings, "webhooks")["document"]
    existing = {endpoint["key"] for endpoint in current["endpoints"]}
    requested = {endpoint["key"] for endpoint in document["endpoints"]}
    for key in requested - existing:
        if not cursor.execute(
            "SELECT 1 FROM crm_channels2.WebhookEndpoint WHERE InstitutionId=? AND EndpointId=? AND EndpointKey=?",
            institution(settings),
            endpoint_id(settings, key),
            key,
        ).fetchone():
            raise HTTPException(422, "webhook_server_owned_identity")
    for endpoint in document["endpoints"]:
        synchronized_endpoint(cursor, settings, endpoint)
    for key in existing - requested:
        cursor.execute(
            "UPDATE crm_channels2.WebhookEndpoint SET IsActive=0,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND EndpointId=?",
            institution(settings),
            endpoint_id(settings, key),
        )


def write_document(cursor, settings, actor, current, document):
    text = Webhooks.model_validate(document).model_dump_json()
    cursor.execute(
        "UPDATE crm_access.Setting SET Document=?,Revision=Revision+1,UpdatedBy=?,UpdatedAt=SYSUTCDATETIME() WHERE InstitutionId=? AND Section='webhooks' AND Revision=?",
        text,
        actor,
        institution(settings),
        current["revision"],
    )
    if cursor.rowcount != 1:
        raise HTTPException(409, "revision_conflict")
    cursor.execute(
        "INSERT crm_access.SettingHistory(InstitutionId,Section,Revision,Document,RecordedAt,ActorId) VALUES(?,'webhooks',?,?,SYSUTCDATETIME(),?)",
        institution(settings),
        current["revision"] + 1,
        text,
        actor,
    )


def metadata_item(cursor, settings, endpoint):
    identity = endpoint_id(settings, endpoint["key"])
    value = one(
        cursor,
        "SELECT ApplicationId,SignatureRequired,IsActive,LastSeenAt,RowVersion FROM crm_channels2.WebhookEndpoint WHERE InstitutionId=? AND EndpointId=?",
        institution(settings),
        identity,
    )
    if not value:
        raise HTTPException(503, "webhook_resource_unavailable")
    return {
        **endpoint,
        "id": identity,
        "application_id": uid(str(value["ApplicationId"])),
        "actual_active": bool(value["IsActive"]),
        "actual_signature_required": bool(value["SignatureRequired"]),
        "last_seen_at": utc(value["LastSeenAt"]),
        "row_version": bytes(value["RowVersion"]).hex(),
        "provider_operations_available": False,
    }


class Endpoints:
    def __init__(self, settings):
        self.settings = settings

    def read(self, authority):
        with transaction(self.settings, anonymous=True) as c:
            authorize(c, self.settings, authority, "settings.webhooks.read")
            current = setting(c, self.settings, "webhooks")
            items = [
                metadata_item(c, self.settings, endpoint)
                for endpoint in current["document"]["endpoints"]
            ]
        return {"items": items, "revision": current["revision"]}

    def create(self, authority, body):
        public_url(body.callback_url)
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.webhooks.write", recent=True
            )
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "webhooks.create",
                body.provider,
                body.model_dump(mode="json"),
            )
            if prior:
                return {**prior, "secrets_already_issued": True}
            current = setting(c, self.settings, "webhooks")
            endpoint = Webhook(
                key="ep_" + token().replace("-", "").replace("_", "")[:32],
                provider=body.provider,
                callback_url=body.callback_url,
                signature_required=body.signature_required,
                integration_ids=body.integration_ids,
            ).model_dump(mode="json")
            identity = synchronized_endpoint(c, self.settings, endpoint, creating=True)
            document = {"endpoints": [*current["document"]["endpoints"], endpoint]}
            write_document(c, self.settings, actor["UserId"], current, document)
            result = {
                "endpoint": metadata_item(c, self.settings, endpoint),
                "revision": current["revision"] + 1,
            }
            verify, signature = token(), token()
            save_secret(
                c,
                self.settings,
                "webhook",
                "endpoint:" + identity,
                "verify_token",
                verify,
            )
            save_secret(
                c,
                self.settings,
                "webhook",
                "endpoint:" + identity,
                "webhook_secret",
                signature,
            )
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "webhooks.create",
                body.provider,
                digest,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "webhooks.create",
                identity,
                revision=current["revision"] + 1,
            )
        return {
            **result,
            "verify_token_once": verify,
            "signature_secret_once": signature,
        }

    def rotate(self, authority, identity, body):
        identity = uid(identity)
        with transaction(self.settings, True, anonymous=True) as c:
            actor = authorize(
                c, self.settings, authority, "settings.webhooks.write", recent=True
            )
            digest, prior = replay(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "webhooks.rotate",
                identity,
                {},
            )
            if prior:
                return {**prior, "secrets_already_issued": True}
            found = c.execute(
                "SELECT 1 FROM crm_channels2.WebhookEndpoint WHERE InstitutionId=? AND EndpointId=?",
                institution(self.settings),
                identity,
            ).fetchone()
            if not found:
                raise HTTPException(404, "webhook_not_found")
            verify, signature = token(), token()
            first = save_secret(
                c,
                self.settings,
                "webhook",
                "endpoint:" + identity,
                "verify_token",
                verify,
            )
            second = save_secret(
                c,
                self.settings,
                "webhook",
                "endpoint:" + identity,
                "webhook_secret",
                signature,
            )
            result = {
                "id": identity,
                "verify_version": first["version"],
                "signature_version": second["version"],
            }
            record_operation(
                c,
                self.settings,
                actor["UserId"],
                body.operation_id,
                "webhooks.rotate",
                identity,
                digest,
                result,
            )
            audit(
                c,
                self.settings,
                actor["UserId"],
                "webhooks.rotate",
                identity,
                version=second["version"],
            )
        return {
            **result,
            "verify_token_once": verify,
            "signature_secret_once": signature,
        }


def install(app, settings):
    service = Endpoints(settings)

    @app.get("/api/institution/webhooks")
    def endpoints(request: Request):
        return service.read(request.state.authority)

    @app.post("/api/institution/webhooks")
    def create_endpoint(request: Request, body: EndpointCreate):
        return service.create(request.state.authority, body)

    @app.post("/api/institution/webhooks/{identity}/rotate")
    def rotate_endpoint(request: Request, identity: str, body: EndpointRotate):
        return service.rotate(request.state.authority, identity, body)
