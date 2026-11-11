"""Explicit learning routes within institutional auth, CSRF and module guards."""

from fastapi import Query, Request

from app.institutional.db import uid
from app.institutional.learning import Learning
from app.institutional.learning_models import (
    DatasetWrite,
    GrantWrite,
    Inference,
    PackWrite,
    SampleWrite,
    Selection,
    TrainWrite,
)


def install(app, settings):
    service = Learning(settings)

    @app.get("/api/institution/learning/catalog")
    def catalog(request: Request):
        return service.catalog(request.state.authority)

    @app.get("/api/institution/learning/packs")
    def packs(request: Request, offset: int = Query(0, ge=0, le=10000)):
        return service.listing(request.state.authority, "packs", offset=offset)

    @app.post("/api/institution/learning/packs")
    def create(request: Request, body: PackWrite):
        return service.save_pack(request.state.authority, body)

    @app.get("/api/institution/learning/packs/{pack}")
    def detail(request: Request, pack: str):
        return service.detail(request.state.authority, uid(pack))

    @app.patch("/api/institution/learning/packs/{pack}")
    def edit(request: Request, pack: str, body: PackWrite):
        return service.save_pack(request.state.authority, body, uid(pack))

    @app.post("/api/institution/learning/packs/{pack}/grants")
    def grant(request: Request, pack: str, body: GrantWrite):
        return service.grant(request.state.authority, uid(pack), body)

    @app.post("/api/institution/learning/packs/{pack}/samples")
    def sample(request: Request, pack: str, body: SampleWrite):
        return service.capture(request.state.authority, uid(pack), body)

    @app.post("/api/institution/learning/packs/{pack}/datasets")
    def dataset(request: Request, pack: str, body: DatasetWrite):
        return service.dataset(request.state.authority, uid(pack), body)

    @app.post("/api/institution/learning/packs/{pack}/train")
    def train_model(request: Request, pack: str, body: TrainWrite):
        return service.training(request.state.authority, uid(pack), body)

    @app.post("/api/institution/learning/packs/{pack}/selection")
    def selection(request: Request, pack: str, body: Selection):
        return service.selection(request.state.authority, uid(pack), body)

    @app.post("/api/institution/learning/packs/{pack}/infer")
    def infer(request: Request, pack: str, body: Inference):
        return service.infer(request.state.authority, uid(pack), body)

    def listing(kind):
        @app.get("/api/institution/learning/packs/{pack}/" + kind)
        def items(request: Request, pack: str, offset: int = Query(0, ge=0, le=10000)):
            return service.listing(request.state.authority, kind, uid(pack), offset)

    for kind in [
        "versions",
        "grants",
        "samples",
        "datasets",
        "artifacts",
        "predictions",
        "events",
    ]:
        listing(kind)
