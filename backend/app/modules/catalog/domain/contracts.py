"""Academic catalog contracts, independent of HTTP and SQL adapters."""

from datetime import date
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field


class Period(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: Annotated[int, Field(ge=-2147483648, le=2147483647)]
    label: str
    startDate: date
    endDate: date
    sourceState: bool


class School(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: Annotated[int, Field(ge=-2147483648, le=2147483647)]
    label: str


class Modality(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: Annotated[int, Field(ge=-2147483648, le=2147483647)]
    label: str


class Program(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    id: Annotated[int, Field(ge=-2147483648, le=2147483647)]
    label: str | None
    schoolId: Annotated[int, Field(ge=-2147483648, le=2147483647)]
    modalityId: Annotated[int, Field(ge=-2147483648, le=2147483647)]


class Page(BaseModel):
    limit: int
    offset: int
    hasMore: bool


class PeriodPage(BaseModel):
    items: list[Period]
    page: Page


class SchoolPage(BaseModel):
    items: list[School]
    page: Page


class ModalityPage(BaseModel):
    items: list[Modality]
    page: Page


class ProgramPage(BaseModel):
    items: list[Program]
    page: Page


class CatalogUnavailable(Exception):
    """Expected SQL, permission, capacity or source-contract failure."""


class CatalogReader(Protocol):
    def read_periods(self, limit: int, offset: int) -> list[Period]: ...
    def read_schools(self, limit: int, offset: int) -> list[School]: ...
    def read_modalities(self, limit: int, offset: int) -> list[Modality]: ...
    def read_programs(
        self, limit: int, offset: int, school_id: int | None, modality_id: int | None
    ) -> list[Program]: ...
