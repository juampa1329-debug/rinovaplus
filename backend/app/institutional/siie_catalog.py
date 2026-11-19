"""Opt-in read-only SIIE commercial API. Preview only; never writes to SIIE."""

import os
import re
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import quote

import httpx2 as httpx
from fastapi import HTTPException
from pydantic import Field, ValidationError, model_validator

from app.institutional.models import Strict
from app.institutional.program_commercial import (
    CommercialProfile,
    ExtractedProgram,
    approved_url,
)


class SiieImport(Strict):
    offer_id: str = Field(default="", max_length=80, pattern=r"^[A-Za-z0-9_-]*$")
    program_id: str = Field(default="", pattern=r"^(?:[1-9][0-9]{0,9})?$")
    period_id: str = Field(default="", pattern=r"^(?:[1-9][0-9]{0,9})?$")
    cursor: str = Field(default="", max_length=128)
    local_program_id: int | None = Field(default=None, strict=True, ge=1, le=2147483647)

    @model_validator(mode="after")
    def target(self):
        if bool(self.offer_id) == bool(self.program_id):
            raise ValueError("siie_invalid_parameter")
        return self


class SiieOffer(Strict):
    schema_version: Literal["siie-crm-commercial-v1"]
    source_system: Literal["DBSIIE"]
    source_revision: str = Field(min_length=1, max_length=120)
    generated_at: datetime
    offer_id: str = Field(min_length=1, max_length=80)
    program_id: str = Field(min_length=1, max_length=80)
    period_id: str = Field(min_length=1, max_length=80)
    campus_id: str = Field(min_length=1, max_length=80)
    shift_id: str = Field(min_length=1, max_length=80)
    currency: Literal["COP"]
    name: str = Field(min_length=1, max_length=180)
    school: str = Field(min_length=1, max_length=100)
    schedule: str = Field(min_length=1, max_length=100)
    active: bool
    commercial: CommercialProfile


def configured():
    return all(
        os.getenv(k, "").strip()
        for k in (
            "SIIE_CATALOG_API_URL",
            "SIIE_CATALOG_API_TOKEN",
            "SIIE_CATALOG_API_HOSTS",
        )
    )


def preview(offer_id="", *, program_id="", period_id="", cursor="", transport=None):
    if os.getenv('SIIE_API_BASE_URL', '').strip():
        from app.institutional.siie_api import read
        from app.institutional.siie_local import draft_from_source
        if program_id:
            result = read('programs', {'period_id': period_id, 'cursor': cursor}, transport=transport)['data']
            item = next((v for v in result['items'] if str(v.get('program_id')) == program_id), None)
            if not item:
                raise HTTPException(409, 'siie_cursor_changed')
            source = draft_from_source({**item, 'source_revision': result['source_revision']}, kind='program', request={'program_id': program_id, 'period_id': period_id, 'cursor': cursor})
        else:
            result = read('offer', {'offer_id': offer_id}, transport=transport)['data']
            source = draft_from_source(result['offer'], request={'offer_id': offer_id})
        return {'draft': ExtractedProgram.model_validate(source['values']), 'source': source, 'review_required': True, 'saved': False, 'siie_written': False}
    if not configured():
        raise HTTPException(409, "siie_catalog_not_configured")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", offer_id):
        raise HTTPException(422, "siie_offer_invalid")
    hosts = {
        v.strip().lower()
        for v in os.environ["SIIE_CATALOG_API_HOSTS"].split(",")
        if v.strip()
    }
    try:
        base = approved_url(os.environ["SIIE_CATALOG_API_URL"], hosts).rstrip("/")
    except HTTPException:
        raise HTTPException(409, "siie_catalog_endpoint_invalid") from None
    target = base + "/v1/crm/offers/" + quote(offer_id, safe="")
    try:
        with httpx.Client(
            timeout=12, follow_redirects=False, trust_env=False, transport=transport
        ) as client:
            with client.stream(
                "GET",
                target,
                headers={
                    "Authorization": "Bearer "
                    + os.environ["SIIE_CATALOG_API_TOKEN"].strip(),
                    "Accept": "application/json",
                },
            ) as response:
                if response.status_code in {401, 403}:
                    raise HTTPException(502, "siie_catalog_access_rejected")
                if response.status_code == 404:
                    raise HTTPException(404, "siie_offer_not_found")
                if response.status_code != 200:
                    raise HTTPException(502, "siie_catalog_unavailable")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 524288:
                        raise HTTPException(502, "siie_catalog_invalid_response")
                value = SiieOffer.model_validate_json(bytes(raw))
        now = datetime.now(timezone.utc)
        if (
            not value.active
            or value.offer_id != offer_id
            or value.generated_at.tzinfo is None
            or abs((now - value.generated_at).total_seconds()) > 86400
        ):
            raise HTTPException(409, "siie_catalog_stale_or_mismatched")
        commercial = value.commercial.model_copy(
            update={
                "siie_offer_id": value.offer_id,
                "siie_source_revision": value.source_revision,
                "siie_program_id": value.program_id,
                "siie_period_id": value.period_id,
                "siie_campus_id": value.campus_id,
                "siie_shift_id": value.shift_id,
                "source_url": target,
                "source_checked_at": now.isoformat(),
            }
        )
        return {
            "draft": ExtractedProgram(
                name=value.name,
                school=value.school,
                schedule=value.schedule,
                commercial=commercial,
            ),
            "source": value.model_dump(mode="json", exclude={"commercial"}),
            "review_required": True,
            "saved": False,
            "siie_written": False,
        }
    except (ValidationError, ValueError):
        raise HTTPException(502, "siie_catalog_invalid_response") from None
    except httpx.HTTPError:
        raise HTTPException(502, "siie_catalog_unavailable") from None
