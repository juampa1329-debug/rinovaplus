"""Controlled draft generation with real SQL credentials/budgets; no paid inference."""

from uuid import uuid4

from app.institutional.comment_ai import Drafts
from app.institutional.comment_effects import Effect
from app.institutional.db import institution
from app.institutional.store import transaction
from tools.qualify_p3_workspace import Browser


def qualify(settings, browser, authority, integration, comment, check):
    def post(path, body, method="POST", expected=200):
        return browser.request(
            path, method, dict(operation_id=str(uuid4()), **body), expected=expected
        ).json()

    post(
        "comments/" + comment["id"] + "/suggest",
        {"row_version": comment["row_version"]},
        expected=409,
    )
    check("unconfigured_AI_is_explicitly_unavailable", True)
    models = browser.request("settings/models").json()
    selections = [
        v
        for v in models["document"]["selections"]
        if (v["provider"], v["category"]) != ("gemini", "text")
    ]
    selections.append(
        {
            "provider": "gemini",
            "category": "text",
            "selected_model": "owned-controlled-model",
            "display_name": "Modelo controlado",
            "voice_id": "",
        }
    )
    post(
        "settings/models",
        {"revision": models["revision"], "document": {"selections": selections}},
        method="PUT",
    )
    ai = browser.request("settings/ai").json()
    post(
        "settings/ai",
        {"revision": ai["revision"], "document": dict(ai["document"], enabled=True)},
        method="PUT",
    )
    post(
        "credentials",
        {
            "scope": "provider",
            "owner": "gemini",
            "kind": "api_key",
            "value": "owned-ai-fixture-" + uuid4().hex,
        },
        method="PUT",
    )
    budget = browser.request("settings/budgets").json()
    post(
        "settings/budgets",
        {
            "revision": budget["revision"],
            "document": dict(
                budget["document"], daily_tokens=1000000, daily_usd_micros=1000000
            ),
        },
        method="PUT",
    )
    post(
        "channels/" + integration + "/comment-ai-policy",
        {
            "input_micros_per_million": 1000,
            "output_micros_per_million": 2000,
            "daily_requests": 10,
            "source_url": "https://pricing.example.test/owned-controlled-fixture",
        },
        method="PUT",
    )
    calls = []

    class Gateway:
        async def generate(self, provider, model, settings, system, messages):
            assert provider == "gemini" and model == "owned-controlled-model"
            assert "SQL" not in messages[0]["content"]
            calls.append(model)
            return (
                "Gracias por tu interés. Nuestro equipo de admisiones puede orientarte."
            )

    with transaction(settings, anonymous=True) as c:
        before = c.execute("SELECT COUNT(*) FROM crm_channels2.SendJob").fetchval()
    service = Drafts(settings, gateway=Gateway())
    body = Effect(operation_id=str(uuid4()), row_version=comment["row_version"])
    result = service.suggest(authority, comment["id"], body)
    repeat = service.suggest(authority, comment["id"], body)
    check(
        "AI_draft_replay_without_second_inference",
        result == repeat and result["status"] == "confirmed" and len(calls) == 1,
    )
    with transaction(settings, anonymous=True) as c:
        after = c.execute("SELECT COUNT(*) FROM crm_channels2.SendJob").fetchval()
        consumed = c.execute(
            "SELECT COUNT(*) FROM crm_access.BudgetUsage WHERE InstitutionId=? "
            "AND Amount>0 AND Kind IN('tokens','usd')",
            institution(settings),
        ).fetchval()
    check(
        "AI_draft_never_enqueues_a_reply",
        before == after and result["automatic_send"] is False,
    )
    check(
        "AI_reserves_token_and_declared_price_limits",
        consumed == 2
        and result["budget_reserved_tokens"] > 0
        and result["budget_reserved_usd_micros"] > 0,
    )
    budget = browser.request("settings/budgets").json()
    post(
        "settings/budgets",
        {
            "revision": budget["revision"],
            "document": dict(budget["document"], daily_tokens=0),
        },
        method="PUT",
    )
    post(
        "comments/" + comment["id"] + "/suggest",
        {"row_version": comment["row_version"]},
        expected=429,
    )
    check("zero_AI_budget_denies_before_provider_IO", len(calls) == 1)
    email = "owned-viewer-" + uuid4().hex[:8] + "@cbn.invalid"
    password = "Owned viewer qualification passphrase 47!"
    post(
        "users",
        {
            "email": email,
            "full_name": "Consulta controlada P4",
            "password": password,
            "role": "viewer",
        },
    )
    viewer = Browser(browser.client.app)
    viewer.login(email, password)
    viewer.request(
        "comments/" + comment["id"] + "/suggest",
        "POST",
        {"operation_id": str(uuid4()), "row_version": comment["row_version"]},
        expected=403,
    )
    check("viewer_cannot_start_AI_or_channel_mutations", True)
