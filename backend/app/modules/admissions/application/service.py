"""Period-scoped SIIE admissions and explicit CRM-owned follow-up records."""

import hashlib
import json
from datetime import date
from typing import Annotated
from uuid import UUID, uuid4

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import Field, model_validator

from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.schemas import LocalModel
from app.sql_workspace import Identifier, SqlWorkspace
from app.sql_workspace_shape import SHAPE_SQL

ADMISSIONS_SHAPE_SQL = SHAPE_SQL.replace("N'crm'", "N'crm_admissions'").replace(
    "N'crm.shape'", "N'crm_admissions.shape'"
)
SqlId = Annotated[int, Field(ge=1, le=2147483647)]
PAGE_SIZE = 25


class FollowupWrite(LocalModel):
    operationId: Identifier
    expectedRevision: Annotated[int, Field(ge=0, le=2147483647)]
    body: Annotated[str, Field(min_length=1, max_length=2000)]
    stateId: SqlId
    dueDate: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None = None

    @model_validator(mode="after")
    def normalize(self):
        self.operationId = str(UUID(self.operationId))
        self.body = self.body.strip()
        if not self.body:
            raise ValueError("A follow-up note is required")
        if self.dueDate:
            date.fromisoformat(self.dueDate)
        return self


def document_key(value: str | None) -> str:
    """Trim surrounding ASCII spaces only; preserve punctuation and leading zeros."""
    return (value or "").strip(" ")


def search_pattern(value: str) -> str:
    return "%" + value.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]") + "%"


def rows(cursor):
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def page(items, offset, limit=PAGE_SIZE):
    return {
        "items": items[:limit],
        "offset": offset,
        "limit": limit,
        "hasMore": len(items) > limit,
    }


APPLICANT_SELECT = """
SELECT a.Id_Aspirante AS id,
 LTRIM(RTRIM(CONCAT(a.NombreAspirante,' ',a.PrimerApellido,
 ' ',a.SegundoApellido))) AS name,
 a.Id_Periodo AS periodId, ap.Periodo AS period,
 a.Id_PrgOfrecido AS offerId, o.Id_Periodo AS offerPeriodId,
 op.Periodo AS offerPeriod, p.Id_Programa AS programId, p.NombrePrograma AS program,
 j.DetalleJornada AS programSchedule,
 a.FechaRegistro AS registeredAt, a.Cnfrmdo AS sourceConfirmed
FROM dbo.ACAspirante a
LEFT JOIN dbo.GEPeriodo ap ON ap.Id_Periodo=a.Id_Periodo
LEFT JOIN dbo.ACProgramaOfrecido o ON o.Id_PrgOfrecido=a.Id_PrgOfrecido
LEFT JOIN dbo.GEPeriodo op ON op.Id_Periodo=o.Id_Periodo
LEFT JOIN dbo.ACProgramas p ON p.Id_Programa=o.Id_Programa
LEFT JOIN dbo.ACJornada j ON j.Id_Jornada=p.Id_Jornada
"""
MATCH_WHERE = """WHERE e.TipoId=? AND
 LTRIM(RTRIM(e.Id_DocEstudiante)) COLLATE Latin1_General_100_BIN2 =
 CAST(? AS varchar(16)) COLLATE Latin1_General_100_BIN2
 AND LEN(LTRIM(RTRIM(e.Id_DocEstudiante))) > 0"""


class AdmissionsRepository:
    def __init__(self, workspace: SqlWorkspace):
        self.workspace = workspace

    @staticmethod
    def verify_followups(cursor):
        value = cursor.execute("""SELECT CONVERT(nvarchar(128),value)
          FROM sys.extended_properties WHERE class=3
          AND major_id=SCHEMA_ID(N'crm_admissions')
          AND name=N'crm_admissions.contract'""").fetchone()
        if not value or value[0] != "admissions-v1":
            raise HTTPException(503, "admissions_storage_unavailable")
        shape = cursor.execute(ADMISSIONS_SHAPE_SQL).fetchone()
        if not shape or not shape[0]:
            raise HTTPException(503, "admissions_storage_unavailable")

    @staticmethod
    def require_applicant(cursor, applicant_id, period_id):
        result = cursor.execute(
            """SELECT Id_Aspirante FROM dbo.ACAspirante
            WHERE Id_Aspirante=? AND Id_Periodo=?""",
            applicant_id,
            period_id,
        ).fetchone()
        if result is None:
            raise HTTPException(404, "applicant_not_in_period")

    def periods(self):
        with self.workspace.transaction() as cursor:
            items = rows(
                cursor.execute("""SELECT TOP (201) Id_Periodo AS id,
                Periodo AS label, EstadoPeriodo AS active FROM dbo.GEPeriodo
                ORDER BY Id_Periodo DESC""")
            )
            if len(items) > 200:
                raise HTTPException(503, "period_catalog_limit")
            active = [item["id"] for item in items if item["active"] == 1]
            return {
                "items": items,
                "activePeriodId": active[0] if len(active) == 1 else None,
                "selectionRequired": len(active) != 1,
            }

    def states(self):
        with self.workspace.transaction() as cursor:
            return {
                "items": rows(
                    cursor.execute("""SELECT TOP (101)
              Id_EstadoSeguimiento AS id, Estado AS label
              FROM dbo.ACEstadoSeguimiento ORDER BY Id_EstadoSeguimiento""")
                )
            }

    def filters(self, period_id):
        with self.workspace.transaction() as cursor:
            if not cursor.execute(
                "SELECT Id_Periodo FROM dbo.GEPeriodo WHERE Id_Periodo=?", period_id
            ).fetchone():
                raise HTTPException(404, "period_not_found")
            items = rows(
                cursor.execute(
                    """SELECT DISTINCT
                p.Id_Programa AS programId,p.NombrePrograma AS program,
                j.Id_Jornada AS scheduleId,j.DetalleJornada AS schedule
                FROM dbo.ACAspirante a
                JOIN dbo.ACProgramaOfrecido o ON o.Id_PrgOfrecido=a.Id_PrgOfrecido
                JOIN dbo.ACProgramas p ON p.Id_Programa=o.Id_Programa
                LEFT JOIN dbo.ACJornada j ON j.Id_Jornada=p.Id_Jornada
                WHERE a.Id_Periodo=? ORDER BY p.Id_Programa,j.Id_Jornada""",
                    period_id,
                )
            )
            return {"periodId": period_id, "items": items}

    def applicants(self, period_id, query, offset, program_id=None, schedule_id=None):
        with self.workspace.transaction() as cursor:
            if not cursor.execute(
                "SELECT Id_Periodo FROM dbo.GEPeriodo WHERE Id_Periodo=?", period_id
            ).fetchone():
                raise HTTPException(404, "period_not_found")
            pattern = search_pattern(query.strip())
            result = rows(
                cursor.execute(
                    APPLICANT_SELECT
                    + """
              WHERE a.Id_Periodo=? AND (?='' OR
              CONCAT(a.NombreAspirante,' ',a.PrimerApellido,
              ' ',a.SegundoApellido) LIKE ?
              OR a.Id_DocAspirante LIKE ?)
              AND (? IS NULL OR p.Id_Programa=?)
              AND (? IS NULL OR p.Id_Jornada=?)
              ORDER BY a.FechaRegistro DESC,a.Id_Aspirante DESC
              OFFSET ? ROWS FETCH NEXT ? ROWS ONLY""",
                    period_id,
                    query.strip(),
                    pattern,
                    pattern,
                    program_id,
                    program_id,
                    schedule_id,
                    schedule_id,
                    offset,
                    PAGE_SIZE + 1,
                )
            )
            return {**page(result, offset), "periodId": period_id}

    def detail(self, applicant_id, period_id, match_offset=0, history_offset=0):
        with self.workspace.transaction() as cursor:
            applicants = rows(
                cursor.execute(
                    APPLICANT_SELECT + " WHERE a.Id_Aspirante=? AND a.Id_Periodo=?",
                    applicant_id,
                    period_id,
                )
            )
            if not applicants:
                raise HTTPException(404, "applicant_not_in_period")
            applicant = applicants[0]
            identity = rows(
                cursor.execute(
                    """SELECT a.TipoId AS documentTypeId,
              Id_DocAspirante AS document, Celular AS mobile, Telefono AS phone,
              Mail AS email, CAST(CASE WHEN t.TipoId IS NULL
              THEN 0 ELSE 1 END AS bit) AS identityTypeKnown
              FROM dbo.ACAspirante a
              LEFT JOIN dbo.GETipoIdentidad t ON t.TipoId=a.TipoId
              WHERE Id_Aspirante=?""",
                    applicant_id,
                )
            )[0]
            applicant.update(identity)
            key = document_key(identity["document"])
            matches = []
            matching_available = bool(key) and bool(identity["identityTypeKnown"])
            if matching_available:
                matches = rows(
                    cursor.execute(
                        """SELECT e.Id_Estudiante AS id,
                  LTRIM(RTRIM(CONCAT(e.Nombres,' ',e.PrimerApellido,
                  ' ',e.SegundoApellido))) AS name,
                  e.Id_PrgOfrecido AS offerId, o.Id_Periodo AS periodId,
                  pe.Periodo AS period, p.NombrePrograma AS program
                  FROM dbo.GEEstudiante e
                  LEFT JOIN dbo.ACProgramaOfrecido o
                  ON o.Id_PrgOfrecido=e.Id_PrgOfrecido
                  LEFT JOIN dbo.GEPeriodo pe ON pe.Id_Periodo=o.Id_Periodo
                  LEFT JOIN dbo.ACProgramas p ON p.Id_Programa=o.Id_Programa
                  """
                        + MATCH_WHERE
                        + """ ORDER BY e.Id_Estudiante
                  OFFSET ? ROWS FETCH NEXT 11 ROWS ONLY""",
                        identity["documentTypeId"],
                        key,
                        match_offset,
                    )
                )
            schedules = (
                rows(
                    cursor.execute(
                        """SELECT d.Id_DetalleJornada AS id,
              j.Id_Jornada AS scheduleId,j.DetalleJornada AS label
              FROM dbo.ACDetalleJornada d
              JOIN dbo.ACJornada j ON j.Id_Jornada=d.Id_Jornada
              WHERE d.Id_PrgOfrecido=? ORDER BY d.Id_DetalleJornada""",
                        applicant["offerId"],
                    )
                )
                if applicant["offerId"]
                else []
            )
            history = rows(
                cursor.execute(
                    """SELECT Id_Seguimiento AS id,
              LEFT(Observacion,4000) AS body,
              CAST(CASE WHEN LEN(Observacion)>4000 THEN 1 ELSE 0
              END AS bit) AS truncated,
              FechaSeguimiento AS date, FechaProxSeguimiento AS dueDate,
              s.Estado AS stateId, e.Estado AS state
              FROM dbo.ACSeguimiento s LEFT JOIN dbo.ACEstadoSeguimiento e
              ON e.Id_EstadoSeguimiento=s.Estado WHERE s.Id_Aspirante=?
              ORDER BY FechaSeguimiento DESC,Id_Seguimiento DESC
              OFFSET ? ROWS FETCH NEXT 11 ROWS ONLY""",
                    applicant_id,
                    history_offset,
                )
            )
            return {
                "applicant": applicant,
                "schedules": schedules,
                "matchingAvailable": matching_available,
                "matches": page(matches, match_offset, 10),
                "history": page(history, history_offset, 10),
            }

    def followups(self, applicant_id, period_id, offset=0):
        with self.workspace.transaction() as cursor:
            self.require_applicant(cursor, applicant_id, period_id)
            self.verify_followups(cursor)
            return self.read_followups(cursor, applicant_id, offset)

    @staticmethod
    def read_followups(cursor, applicant_id, offset=0):
        result = rows(
            cursor.execute(
                """SELECT CONVERT(varchar(36),f.FollowupId) AS id,
          f.Body AS body,f.StateId AS stateId,s.Estado AS state,f.DueDate AS dueDate,
          f.Revision AS revision,f.CreatedAt AS createdAt,f.UpdatedAt AS updatedAt
          FROM crm_admissions.Followup f
          JOIN crm_admissions.AdmissionCase c ON c.CaseId=f.CaseId
          LEFT JOIN dbo.ACEstadoSeguimiento s ON s.Id_EstadoSeguimiento=f.StateId
          WHERE c.AspirantId=? ORDER BY f.CreatedAt DESC,f.FollowupId
          OFFSET ? ROWS FETCH NEXT 26 ROWS ONLY""",
                applicant_id,
                offset,
            )
        )
        return page(result, offset)

    def save_followup(
        self, applicant_id, period_id, followup_id, body: FollowupWrite, create
    ):
        followup_id = str(UUID(followup_id))
        action = "create" if create else "edit"
        digest = hashlib.sha256(
            json.dumps(
                [
                    action,
                    applicant_id,
                    period_id,
                    followup_id,
                    body.model_dump(exclude={"operationId", "expectedRevision"}),
                ],
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).digest()
        with self.workspace.transaction(write=True) as cursor:
            self.require_applicant(cursor, applicant_id, period_id)
            self.verify_followups(cursor)
            previous = cursor.execute(
                "SELECT PayloadHash FROM crm_admissions.Operation WHERE OperationId=?",
                body.operationId,
            ).fetchone()
            if previous:
                if bytes(previous[0]) != digest:
                    raise HTTPException(409, "operation_changed")
                return self.read_followups(cursor, applicant_id)
            if not cursor.execute(
                "SELECT Id_EstadoSeguimiento FROM dbo.ACEstadoSeguimiento "
                "WHERE Id_EstadoSeguimiento=?",
                body.stateId,
            ).fetchone():
                raise HTTPException(422, "invalid_followup_state")
            case = cursor.execute(
                "SELECT CaseId FROM crm_admissions.AdmissionCase WHERE AspirantId=?",
                applicant_id,
            ).fetchone()
            if create:
                if body.expectedRevision != 0:
                    raise HTTPException(409, "followup_changed")
                if cursor.execute(
                    "SELECT FollowupId FROM crm_admissions.Followup WHERE FollowupId=?",
                    followup_id,
                ).fetchone():
                    raise HTTPException(409, "followup_exists")
                case_id = str(case[0]) if case else str(uuid4())
                if not case:
                    cursor.execute(
                        "INSERT crm_admissions.AdmissionCase "
                        "(CaseId,AspirantId) VALUES (?,?)",
                        case_id,
                        applicant_id,
                    )
                cursor.execute(
                    """INSERT crm_admissions.Followup
                  (FollowupId,CaseId,Body,StateId,DueDate,Revision)
                  VALUES (?,?,?,?,?,1)""",
                    followup_id,
                    case_id,
                    body.body,
                    body.stateId,
                    body.dueDate,
                )
            else:
                existing = cursor.execute(
                    """SELECT f.Revision FROM crm_admissions.Followup f
                  JOIN crm_admissions.AdmissionCase c ON c.CaseId=f.CaseId
                  WHERE f.FollowupId=? AND c.AspirantId=?""",
                    followup_id,
                    applicant_id,
                ).fetchone()
                if existing is None:
                    raise HTTPException(404, "followup_not_found")
                if existing[0] != body.expectedRevision:
                    raise HTTPException(409, "followup_changed")
                cursor.execute(
                    """UPDATE crm_admissions.Followup SET Body=?,StateId=?,DueDate=?,
                  Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE FollowupId=?""",
                    body.body,
                    body.stateId,
                    body.dueDate,
                    followup_id,
                )
            cursor.execute(
                """INSERT crm_admissions.Operation
              (OperationId,FollowupId,Action,PayloadHash) VALUES (?,?,?,?)""",
                body.operationId,
                followup_id,
                action,
                digest,
            )
            return self.read_followups(cursor, applicant_id)


def install_admissions(application: FastAPI):
    application.state.admissions = AdmissionsRepository(application.state.sql_workspace)
    router = APIRouter(prefix="/api/local/admissions", tags=["local-admissions"])

    def call(request, method, *args):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            result = getattr(request.app.state.admissions, method)(*args)
            return JSONResponse(
                jsonable_encoder(result), headers={"Cache-Control": "no-store"}
            )
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "admissions_unavailable") from None

    @router.get("/periods")
    def periods(request: Request):
        return call(request, "periods")

    @router.get("/followup-states")
    def states(request: Request):
        return call(request, "states")

    @router.get("/applicants")
    def applicants(
        request: Request,
        periodId: SqlId,
        q: str = Query("", max_length=100),
        offset: int = Query(0, ge=0, le=1000000),
        programId: SqlId | None = None,
        scheduleId: SqlId | None = None,
    ):
        return call(request, "applicants", periodId, q, offset, programId, scheduleId)

    @router.get("/filters")
    def filters(request: Request, periodId: SqlId):
        return call(request, "filters", periodId)

    @router.get("/applicants/{applicant_id}")
    def detail(
        request: Request,
        applicant_id: SqlId,
        periodId: SqlId,
        matchOffset: int = Query(0, ge=0, le=1000000),
        historyOffset: int = Query(0, ge=0, le=1000000),
    ):
        return call(
            request, "detail", applicant_id, periodId, matchOffset, historyOffset
        )

    @router.get("/applicants/{applicant_id}/followups")
    def followups(
        request: Request,
        applicant_id: SqlId,
        periodId: SqlId,
        offset: int = Query(0, ge=0, le=1000000),
    ):
        return call(request, "followups", applicant_id, periodId, offset)

    @router.post("/applicants/{applicant_id}/followups/{followup_id}")
    def create(
        request: Request,
        applicant_id: SqlId,
        followup_id: Identifier,
        periodId: SqlId,
        body: FollowupWrite,
    ):
        return call(
            request, "save_followup", applicant_id, periodId, followup_id, body, True
        )

    @router.put("/applicants/{applicant_id}/followups/{followup_id}")
    def edit(
        request: Request,
        applicant_id: SqlId,
        followup_id: Identifier,
        periodId: SqlId,
        body: FollowupWrite,
    ):
        return call(
            request, "save_followup", applicant_id, periodId, followup_id, body, False
        )

    application.include_router(router)
