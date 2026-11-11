"""Institutional P7 API; no legacy campaign worker or alternate outbox."""

from fastapi import Query, Request
from fastapi.responses import Response

from app.institutional.broadcast_models import (
    CadenceWrite,
    CampaignWrite,
    Command,
    ConsentWrite,
    Review,
    TemplatePause,
    TemplateWrite,
)
from app.institutional.broadcasts import Broadcasts
from app.institutional.db import uid


def install(app, settings, gateway=None):
    service = Broadcasts(settings, gateway)

    @app.get("/api/institution/broadcasts/options")
    def options(request: Request):
        return service.metadata(request.state.authority)

    @app.get("/api/institution/broadcasts")
    def listing(request: Request):
        return service.listing(request.state.authority)

    @app.get(("/api/institution/broadcasts/accounts/{integration}/identities"))
    def identities(request: Request, integration: str):
        return service.identities(request.state.authority, uid(integration))

    @app.get(("/api/institution/broadcasts/accounts/{integration}/cadence"))
    def cadence(request: Request, integration: str):
        return service.cadence(request.state.authority, uid(integration))

    @app.put(("/api/institution/broadcasts/accounts/{integration}/cadence"))
    def save_cadence(request: Request, integration: str, body: CadenceWrite):
        return service.cadence(request.state.authority, uid(integration), body)

    @app.put(("/api/institution/broadcasts/accounts/{integration}/consent/{identity}"))
    def consent(request: Request, integration: str, identity: str, body: ConsentWrite):
        return service.save_consent(
            request.state.authority, uid(integration), uid(identity), body
        )

    @app.post(("/api/institution/broadcasts/accounts/{integration}/templates/sync"))
    def sync(request: Request, integration: str, body: Command):
        return service.sync(request.state.authority, uid(integration), body)

    @app.put(
        ("/api/institution/broadcasts/accounts/{integration}/templates/{template}")
    )
    def draft(request: Request, integration: str, template: str, body: TemplateWrite):
        return service.create_template(
            request.state.authority, uid(integration), uid(template), body
        )

    @app.post(("/api/institution/broadcasts/templates/{template}/submit"))
    def submit(request: Request, template: str, body: Review):
        return service.submit_template(request.state.authority, uid(template), body)

    @app.post(("/api/institution/broadcasts/templates/{template}/pause"))
    def pause_template(request: Request, template: str, body: TemplatePause):
        return service.pause_template(request.state.authority, uid(template), body)

    @app.get("/api/institution/broadcasts/{campaign}/export")
    def export(
        request: Request,
        campaign: str,
        state: str = Query(
            default="",
            pattern=(
                "^$|^(prepared|queued|sending|accepted|"
                "sent|delivered|read|failed|uncertain|b"
                "locked|cancelled|replied)$"
            ),
        ),
        search: str = Query(default="", max_length=100),
    ):
        return Response(
            service.export(
                request.state.authority, uid(campaign), state=state, search=search
            ),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="destinatarios.csv"',
                "Cache-Control": "no-store",
            },
        )

    @app.get("/api/institution/broadcasts/{campaign}/report")
    def report(
        request: Request,
        campaign: str,
        offset: int = Query(default=0, ge=0),
        state: str = Query(
            default="",
            pattern=(
                "^$|^(prepared|queued|sending|accepted|"
                "sent|delivered|read|failed|uncertain|b"
                "locked|cancelled|replied)$"
            ),
        ),
        search: str = Query(default="", max_length=100),
    ):
        return service.report(
            request.state.authority, uid(campaign), offset, state=state, search=search
        )

    @app.get("/api/institution/broadcasts/{campaign}/preview")
    def preview(request: Request, campaign: str):
        return service.preview(request.state.authority, uid(campaign))

    @app.get("/api/institution/broadcasts/{campaign}")
    def get(request: Request, campaign: str):
        return service.get(request.state.authority, uid(campaign))

    @app.put("/api/institution/broadcasts/{campaign}")
    def save(request: Request, campaign: str, body: CampaignWrite):
        return service.save(request.state.authority, uid(campaign), body)

    @app.post("/api/institution/broadcasts/{campaign}/{action}")
    def action(request: Request, campaign: str, action: str, body: Review):
        return service.action(request.state.authority, uid(campaign), action, body)
