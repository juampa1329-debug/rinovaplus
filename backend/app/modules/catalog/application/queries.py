"""Bounded catalog query use cases."""

from app.modules.catalog.domain.contracts import (
    CatalogReader,
    ModalityPage,
    Page,
    PeriodPage,
    ProgramPage,
    SchoolPage,
)


def list_periods(reader: CatalogReader, limit: int, offset: int) -> PeriodPage:
    rows = reader.read_periods(limit + 1, offset)
    return PeriodPage(
        items=rows[:limit],
        page=Page(limit=limit, offset=offset, hasMore=len(rows) > limit),
    )


def list_schools(reader: CatalogReader, limit: int, offset: int) -> SchoolPage:
    rows = reader.read_schools(limit + 1, offset)
    return SchoolPage(
        items=rows[:limit],
        page=Page(limit=limit, offset=offset, hasMore=len(rows) > limit),
    )


def list_modalities(reader: CatalogReader, limit: int, offset: int) -> ModalityPage:
    rows = reader.read_modalities(limit + 1, offset)
    return ModalityPage(
        items=rows[:limit],
        page=Page(limit=limit, offset=offset, hasMore=len(rows) > limit),
    )


def list_programs(
    reader: CatalogReader,
    limit: int,
    offset: int,
    school_id: int | None,
    modality_id: int | None,
) -> ProgramPage:
    rows = reader.read_programs(limit + 1, offset, school_id, modality_id)
    return ProgramPage(
        items=rows[:limit],
        page=Page(limit=limit, offset=offset, hasMore=len(rows) > limit),
    )
