"""Local operator authentication and explicit catalog query allowlist."""

from collections.abc import Callable
from secrets import compare_digest
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.modules.catalog.application.queries import (
    list_modalities,
    list_periods,
    list_programs,
    list_schools,
)
from app.modules.catalog.domain.contracts import (
    CatalogUnavailable,
    ModalityPage,
    PeriodPage,
    ProgramPage,
    SchoolPage,
)

router = APIRouter()


def failure(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "correlationId": str(uuid4())},
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/api/v1/catalog/periods", response_model=PeriodPage, operation_id="catalog_periods"
)
def periods(request: Request):
    return catalog_response(request, list_periods)


@router.get(
    "/api/v1/catalog/schools", response_model=SchoolPage, operation_id="catalog_schools"
)
def schools(request: Request):
    return catalog_response(request, list_schools)


@router.get(
    "/api/v1/catalog/modalities",
    response_model=ModalityPage,
    operation_id="catalog_modalities",
)
def modalities(request: Request):
    return catalog_response(request, list_modalities)


@router.get(
    "/api/v1/catalog/programs",
    response_model=ProgramPage,
    operation_id="catalog_programs",
)
def programs(request: Request):
    return catalog_response(request, list_programs, program_filters=True)


def signed_id(value: str | None) -> int | None:
    if value is None:
        return None
    digits = value.removeprefix("-")
    if not digits or not digits.isascii() or not digits.isdecimal():
        raise ValueError()
    number = int(value)
    if not -2147483648 <= number <= 2147483647:
        raise ValueError()
    return number


def catalog_response(
    request: Request,
    use_case: Callable[..., PeriodPage | SchoolPage | ModalityPage | ProgramPage],
    program_filters: bool = False,
):
    settings = request.app.state.settings
    if settings.mode not in ("local_readonly_catalog", "local_sql_copy"):
        return failure(503, "CATALOG_UNAVAILABLE", "Catalog is unavailable")
    headers = request.headers.getlist("authorization")
    expected = f"Bearer {settings.catalog_token}"
    if settings.mode == "local_readonly_catalog" and (
        len(headers) != 1 or not compare_digest(headers[0].encode(), expected.encode())
    ):
        response = failure(401, "AUTHENTICATION_REQUIRED", "Authentication required")
        response.headers["WWW-Authenticate"] = "Bearer"
        return response
    pairs = request.query_params.multi_items()
    allowed = (
        ("limit", "offset", "schoolId", "modalityId")
        if program_filters
        else ("limit", "offset")
    )
    if len({key for key, _ in pairs}) != len(pairs) or any(
        key not in allowed for key, _ in pairs
    ):
        return failure(422, "INVALID_REQUEST", "Invalid catalog request")
    try:
        values = dict(pairs)
        if any(
            not value.isascii() or not value.isdecimal()
            for key, value in values.items()
            if key in ("limit", "offset")
        ):
            raise ValueError()
        limit = int(values.get("limit", "25"))
        offset = int(values.get("offset", "0"))
        if not 1 <= limit <= 100 or not 0 <= offset <= 10000:
            raise ValueError()
        school_id = signed_id(values.get("schoolId"))
        modality_id = signed_id(values.get("modalityId"))
    except ValueError:
        return failure(422, "INVALID_REQUEST", "Invalid catalog request")
    try:
        result = (
            use_case(
                request.app.state.catalog_reader, limit, offset, school_id, modality_id
            )
            if program_filters
            else use_case(request.app.state.catalog_reader, limit, offset)
        )
        return JSONResponse(
            result.model_dump(mode="json"), headers={"Cache-Control": "no-store"}
        )
    except CatalogUnavailable:
        return failure(503, "CATALOG_UNAVAILABLE", "Catalog is unavailable")
    except Exception:
        return failure(500, "INTERNAL_ERROR", "Request could not be completed")
