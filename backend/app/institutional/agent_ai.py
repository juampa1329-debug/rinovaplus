"""Agent selections use canonical institutional models and encrypted credentials."""

import hashlib
import json
from types import SimpleNamespace
from typing import get_args

from app.institutional.auth import authorize
from app.institutional.comment_ai import DraftGateway
from app.institutional.crypto import unseal
from app.institutional.db import institution, key, rows
from app.institutional.policy import request_authority
from app.institutional.settings import setting
from app.institutional.store import transaction
from app.modules.ai.domain.models import Provider
from app.institutional.models import AI
from app.modules.ai.infrastructure.providers import AiError
from pydantic import ValidationError


class AgentAI:
    demo_template_model = "cbn-demo-unconfigured"

    def __init__(self, settings, gateway_factory=None):
        self.profile = settings
        self.repository = SimpleNamespace(read=self.read)
        self.credentials = SimpleNamespace(read=self.credential_state)
        self.gateway_factory = gateway_factory
        self.gateway = DraftGateway({})
        self.busy, self.outbound = False, False
        self.catalogs = {}

    def authorize(self, c):
        authority = request_authority.get()
        if authority is None:
            raise ValueError("P5ES_agent_authority_required")
        return authorize(c, self.profile, authority, authority["permission"])

    def read(self):
        with transaction(self.profile, anonymous=True) as c:
            self.authorize(c)
            ai = setting(c, self.profile, "ai")
            models = setting(c, self.profile, "models")
            document = ai["document"]
            try:
                # Reuse the schema that validated the saved institutional settings.
                # The shared demo schema has narrower timing/prompt/token bounds.
                config = AI(**{k: v for k, v in document.items() if k in AI.model_fields})
            except ValidationError:
                raise AiError("agents_ai_settings_invalid", 409) from None
            self.catalogs = {}
            return SimpleNamespace(
                settings=config, revision=(ai["revision"], models["revision"])
            )

    def connection_snapshot(self):
        with transaction(self.profile, anonymous=True) as c:
            self.authorize(c)
            values = rows(
                c,
                "SELECT SecretId,OwnerRef,VersionNo FROM crm_access.Secret "
                "WHERE InstitutionId=? AND Scope='provider' AND Kind='api_key' AND State='staged'",
                institution(self.profile),
            )
        revision = int(
            hashlib.sha256(
                json.dumps(
                    sorted((str(v["SecretId"]), v["VersionNo"]) for v in values)
                ).encode()
            ).hexdigest()[:12],
            16,
        )
        return {
            "providers": [
                {"id": p, "configured": any(v["OwnerRef"] == p for v in values)}
                for p in get_args(Provider)
            ],
            "credential_revision": revision,
        }

    def credential_state(self):
        value = self.connection_snapshot()
        return SimpleNamespace(
            revision=value["credential_revision"], outbound=self.read().settings.enabled
        )

    def refresh_credentials(self):
        with transaction(self.profile, anonymous=True) as c:
            self.authorize(c)
            values = rows(
                c,
                "SELECT * FROM crm_access.Secret WHERE InstitutionId=? "
                "AND Scope='provider' AND Kind='api_key' AND State='staged'",
                institution(self.profile),
            )
            keys = {}
            for row in values:
                keys[row["OwnerRef"]] = unseal(
                    key(self.profile),
                    {
                        "institution": institution(self.profile),
                        "scope": "provider",
                        "owner": row["OwnerRef"],
                        "kind": "api_key",
                        "version": row["VersionNo"],
                        "secret_id": str(row["SecretId"]).lower(),
                    },
                    row["Nonce"],
                    row["Ciphertext"],
                )
        self.gateway = (
            self.gateway_factory(keys) if self.gateway_factory else DraftGateway(keys)
        )
        self.outbound = self.read().settings.enabled
