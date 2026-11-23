"""An operator-selected primary and ordered language backups, not an agent rewrite."""

from fastapi import Request
from pydantic import Field

from app.institutional.models import Strict
from app.modules.ai.domain.resilience import LanguageResilience


class SaveLanguagePolicy(Strict):
    operation_id: str
    revision: int = Field(ge=1)
    language_resilience: LanguageResilience


def install(app, settings):
    @app.put("/api/institution/settings/ai/language-policy")
    def save(request: Request, body: SaveLanguagePolicy):
        from app.institutional.ai_policy import save as persist

        return persist(
            settings,
            request.state.authority,
            body.operation_id,
            body.revision,
            {"language_resilience": body.language_resilience.model_dump()},
            "language.policy",
        )
