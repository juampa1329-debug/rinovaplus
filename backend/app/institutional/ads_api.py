"""Native Ads routes. All supported writes are local; no spend/publish endpoint."""

from datetime import date

from fastapi import Query, Request

from app.institutional.ads import Ads, get, public
from app.institutional.ads_models import (
    Command,
    Credential,
    Process,
    SaveAccount,
    SaveCampaign,
    SaveIntake,
)
from app.institutional.ads_receipts import process
from app.institutional.db import uid


def install(app, settings):
    service = Ads(settings)

    @app.get("/api/institution/ads/options")
    def options(request: Request):
        return service.options(request.state.authority)

    @app.get("/api/institution/ads/summary")
    def summary(
        request: Request,
        account_id: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ):
        return service.summary(
            request.state.authority,
            uid(account_id) if account_id else None,
            start.isoformat() if start else None,
            end.isoformat() if end else None,
        )

    @app.get("/api/institution/ads/accounts")
    def accounts(request: Request, offset: int = Query(0, ge=0, le=10000)):
        return service.listing(request.state.authority, "account", offset=offset)

    @app.post("/api/institution/ads/accounts")
    def save_account(request: Request, body: SaveAccount):
        return service.save_account(request.state.authority, body)

    @app.patch("/api/institution/ads/accounts/{id}")
    def patch_account(request: Request, id: str, body: SaveAccount):
        return service.save_account(request.state.authority, body, uid(id))

    @app.post("/api/institution/ads/accounts/{id}/credential")
    def credential(request: Request, id: str, body: Credential):
        return service.credential(request.state.authority, uid(id), body)

    @app.get("/api/institution/ads/accounts/{id}/history")
    def history(request: Request, id: str, offset: int = Query(0, ge=0, le=10000)):
        return service.history(request.state.authority, uid(id), offset)

    @app.post("/api/institution/ads/accounts/{id}/process")
    def run(request: Request, id: str, body: Process):
        return process(service, request.state.authority, uid(id), body)

    @app.post("/api/institution/ads/accounts/{id}/processes/{run}/retry")
    def retry(request: Request, id: str, run: str, body: Process):
        return process(service, request.state.authority, uid(id), body, uid(run))

    @app.get("/api/institution/ads/campaigns")
    def campaigns(
        request: Request,
        account_id: str | None = None,
        offset: int = Query(0, ge=0, le=10000),
    ):
        return service.listing(
            request.state.authority,
            "campaign",
            account_id=uid(account_id) if account_id else None,
            offset=offset,
        )

    @app.post("/api/institution/ads/campaigns")
    def save_campaign(request: Request, body: SaveCampaign):
        return service.save_campaign(request.state.authority, body)

    @app.patch("/api/institution/ads/campaigns/{id}")
    def patch_campaign(request: Request, id: str, body: SaveCampaign):
        return service.save_campaign(request.state.authority, body, uid(id))

    @app.get("/api/institution/ads/processes")
    def processes(
        request: Request,
        account_id: str | None = None,
        offset: int = Query(0, ge=0, le=10000),
    ):
        return service.listing(
            request.state.authority,
            "run",
            account_id=uid(account_id) if account_id else None,
            offset=offset,
        )

    # Static routes are registered explicitly; unrecognized kinds never reach SQL.
    def install_kind(kind, route):
        @app.get("/api/institution/ads/" + route)
        def listing(
            request: Request,
            account_id: str | None = None,
            status: str = Query("all", max_length=16),
            offset: int = Query(0, ge=0, le=10000),
            start: date | None = None,
            end: date | None = None,
        ):
            return service.listing(
                request.state.authority,
                kind,
                account_id=uid(account_id) if account_id else None,
                status=status,
                offset=offset,
                start=start.isoformat() if start else None,
                end=end.isoformat() if end else None,
            )

        @app.post("/api/institution/ads/" + route + "/import")
        def imported(request: Request, body: SaveIntake):
            return service.import_intake(request.state.authority, body, kind)

        @app.patch("/api/institution/ads/" + route + "/{id}")
        def patched(request: Request, id: str, body: SaveIntake):
            return service.import_intake(request.state.authority, body, kind, uid(id))

        @app.post("/api/institution/ads/" + route + "/{id}/to-inbox")
        def inbox(request: Request, id: str, body: Command):
            return service.to_inbox(request.state.authority, uid(id), body, kind)

    install_kind("lead", "leads")
    install_kind("comment", "comments")

    @app.get("/api/institution/ads/intakes/{id}")
    def detail(request: Request, id: str):
        with service.tx(request.state.authority) as (c, _):
            return public(c, settings, get(c, settings, uid(id), "intake"), "intake")
