"""Opt-in read-only SIIE commercial API. Preview only; never writes to SIIE."""

from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from pydantic import Field, model_validator

from app.institutional.models import Strict
from app.institutional.program_commercial import (
    CommercialProfile,
    ExtractedProgram,
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
    from app.institutional.siie_api import configured as ready
    return ready("catalog")


def preview(offer_id="", *, program_id="", period_id="", cursor="", transport=None):
    if configured():
        from app.institutional.siie_api import read
        from app.institutional.siie_local import draft_from_source
        if program_id:
            response = read('programs', {'period_id': period_id, 'cursor': cursor}, transport=transport)
            result = response['data']
            item = next((v for v in result['items'] if str(v.get('program_id')) == program_id), None)
            if not item:
                raise HTTPException(409, 'siie_cursor_changed')
            source = draft_from_source({**item, 'source_revision': result['source_revision']}, kind='program', request={'program_id': program_id, 'period_id': period_id, 'cursor': cursor}, environment=response['environment'])
        else:
            response = read('offer', {'offer_id': offer_id}, transport=transport)
            result = response['data']
            source = draft_from_source(result['offer'], request={'offer_id': offer_id}, environment=response['environment'])
        return {'environment':response['environment'],'draft': ExtractedProgram.model_validate(source['values']), 'source': source, 'review_required': True, 'saved': False, 'siie_written': False}
    raise HTTPException(409, "siie_catalog_not_configured")
