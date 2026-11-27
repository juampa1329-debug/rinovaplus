"""Institutional P8 routes; no legacy campaign router or second sender."""

from fastapi import Query, Request

from app.institutional.campaign_models import Command, Review, Save, Simulate
from app.institutional.campaigns import Campaigns
from app.institutional.db import uid


def install(app, settings, gateway=None):
    from app.institutional.campaign_delivery import install as install_delivery

    install_delivery(app, settings)
    service = Campaigns(settings, gateway)
    from app.institutional.campaign_assets import Upload, download, upload

    @app.post("/api/institution/campaigns/assets")
    def upload_asset(request: Request, body: Upload):
        return upload(service, request.state.authority, body)

    @app.get("/api/institution/campaigns/assets/{asset}")
    def download_asset(request: Request, asset: str):
        return download(service, request.state.authority, uid(asset))

    @app.get("/api/institution/campaigns/options")
    def options(request: Request):
        return service.metadata(request.state.authority)

    @app.get("/api/institution/campaigns")
    def listing(request: Request):
        return service.listing(request.state.authority)

    @app.get("/api/institution/campaigns/{record}")
    def get(request: Request, record: str):
        return service.get(request.state.authority, uid(record))

    @app.put("/api/institution/campaigns/{record}")
    def save(request: Request, record: str, body: Save):
        return service.save(request.state.authority, uid(record), body)

    @app.get("/api/institution/campaigns/{record}/versions")
    def versions(request: Request, record: str, offset: int = Query(default=0, ge=0)):
        return service.history(request.state.authority, uid(record), offset)

    @app.get("/api/institution/campaigns/{record}/preview")
    def preview(request: Request, record: str):
        return service.preview(request.state.authority, uid(record))

    @app.post("/api/institution/campaigns/{record}/preflight")
    def preflight(request: Request, record: str, body: Command):
        return service.preflight(request.state.authority, uid(record), body)

    @app.post("/api/institution/campaigns/{record}/simulate")
    def simulate(request: Request, record: str, body: Simulate):
        return service.simulate(request.state.authority, uid(record), body)

    @app.get("/api/institution/campaigns/{record}/runs")
    def runs(request: Request, record: str, offset: int = Query(default=0, ge=0),
             q: str = Query(default="", max_length=120),
             state: str = Query(default="", max_length=20),
             step: int = Query(default=-1, ge=-1, le=19)):
        return service.runs(request.state.authority, uid(record), offset, q, state, step)

    @app.get("/api/institution/campaigns/{record}/metrics")
    def metrics(request: Request, record: str):
        return service.metrics(request.state.authority, uid(record))

    @app.get("/api/institution/campaigns/{record}/runs/{run}")
    def trace(request: Request, record: str, run: str):
        return service.trace(request.state.authority, uid(record), uid(run))

    @app.post("/api/institution/campaigns/{record}/{action}")
    def action(request: Request, record: str, action: str, body: Review):
        id = uid(record)
        return (
            service.copy_restore(request.state.authority, id, action, body)
            if action in {"copy", "restore"}
            else service.action(request.state.authority, id, action, body)
        )
