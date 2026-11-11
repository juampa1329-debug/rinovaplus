"""Local declared profile and bounded, read-only cross-source comparison."""

import sys

import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.modules.admissions.application.service import AdmissionsRepository, rows, search_pattern
from app.modules.catalog.domain.contracts import CatalogUnavailable
from app.modules.contacts.domain.models import IdentityLookup, InstitutionalProfile
from app.sql_workspace_shape import SHAPE_SQL

PROFILE_COLUMNS = (
    "GivenNames,FirstSurname,SecondSurname,DocumentTypeId,"
    "Document,Email,AspirationPeriodId"
)
PROFILE_KEYS = list(InstitutionalProfile.model_fields)
IDENTITY_SHAPE = SHAPE_SQL.replace("N'crm'", "N'crm_identity'").replace(
    "N'crm.shape'", "N'crm_identity.shape'"
)


def available(cursor, required=False):
    legacy = getattr(sys.modules.get(__name__), "available", None)
    if legacy is not None and legacy is not available:
        return legacy(cursor, required=required)
    row = cursor.execute("SELECT SCHEMA_ID(N'crm_identity')").fetchone()
    if row is None or row[0] is None:
        if required:
            raise HTTPException(503, "institutional_profile_unavailable")
        return False
    marker = cursor.execute(
        "SELECT CONVERT(nvarchar(80),value) FROM sys.extended_properties "
        "WHERE class=3 AND major_id=SCHEMA_ID(N'crm_identity') "
        "AND name=N'crm_identity.contract'"
    ).fetchone()
    shape = cursor.execute(IDENTITY_SHAPE).fetchone()
    if marker is None or marker[0] != "identity-v1" or shape is None or not shape[0]:
        raise CatalogUnavailable()
    return True


def decorate(cursor, clients):
    if not clients or not available(cursor):
        return clients
    placeholders = ",".join("?" for _ in clients)
    found = cursor.execute(
        "SELECT ContactId,"
        + PROFILE_COLUMNS
        + " FROM crm_identity.Profile WHERE ContactId IN ("
        + placeholders
        + ")",
        *[c["id"] for c in clients],
    ).fetchall()
    profiles = {
        str(row[0]).lower(): dict(zip(PROFILE_KEYS, row[1:], strict=True))
        for row in found
    }
    for client in clients:
        client["institutionalProfile"] = profiles.get(client["id"])
    return clients


def save_profile(cursor, contact):
    profile = contact.institutionalProfile
    if profile is None:
        return
    available(cursor, required=True)
    validate_catalogs(cursor, profile.documentTypeId, profile.aspirationPeriodId)
    exists = cursor.execute(
        "SELECT ContactId FROM crm_identity.Profile WHERE ContactId=?", contact.id
    ).fetchone()
    if exists:
        cursor.execute(
            "UPDATE crm_identity.Profile SET GivenNames=?,FirstSurname=?,"
            "SecondSurname=?,DocumentTypeId=?,Document=?,Email=?,AspirationPeriodId=?,"
            "UpdatedAt=SYSUTCDATETIME() WHERE ContactId=?",
            *profile.model_dump().values(),
            contact.id,
        )
    elif not profile.empty():
        cursor.execute(
            "INSERT crm_identity.Profile(ContactId,"
            + PROFILE_COLUMNS
            + ") VALUES(?,?,?,?,?,?,?,?)",
            contact.id,
            *profile.model_dump().values(),
        )


def validate_catalogs(cursor, document_type=None, period=None, program=None):
    legacy = getattr(
        sys.modules.get(__name__), "validate_catalogs", None
    )
    if legacy is not None and legacy is not validate_catalogs:
        return legacy(cursor, document_type, period, program)
    for value, sql in [
        (document_type, "SELECT TipoId FROM dbo.GETipoIdentidad WHERE TipoId=?"),
        (period, "SELECT Id_Periodo FROM dbo.GEPeriodo WHERE Id_Periodo=?"),
        (program, "SELECT Id_Programa FROM dbo.ACProgramas WHERE Id_Programa=?"),
    ]:
        if value is not None and cursor.execute(sql, value).fetchone() is None:
            raise HTTPException(422, "unknown_institutional_catalog_value")


def private_identifiers(cursor, conversation):
    legacy = getattr(
        sys.modules.get(__name__), "private_identifiers", None
    )
    if legacy is not None and legacy is not private_identifiers:
        return legacy(cursor, conversation)
    if not available(cursor):
        return []
    row = cursor.execute(
        "SELECT "
        + ",".join("p." + c for c in PROFILE_COLUMNS.split(","))
        + " FROM crm_identity.Profile p JOIN crm.Conversation c "
        "ON c.ContactId=p.ContactId WHERE c.ConversationId=?",
        conversation,
    ).fetchone()
    if row is None:
        return []
    names = " ".join(str(v or "") for v in row[:3]).strip()
    return [names, *names.split(), str(row[4] or ""), str(row[5] or "")]


LOOKUP_SQL = """
DECLARE @mode varchar(10)=?,@source varchar(12)=?,@own uniqueidentifier=?,
 @docType int=?,@document nvarchar(16)=?,@email nvarchar(160)=?,
 @phone nvarchar(50)=?,@name nvarchar(602)=?,@period int=?,@program int=?,
 @offset int=?,@excluded nvarchar(max)=?;
WITH records AS (
 SELECT 'crm' AS source,CONVERT(varchar(36),c.ContactId) AS sourceId,
  CONVERT(varchar(36),c.ContactId) AS contactId,c.Name AS name,
  p.GivenNames AS givenNames,p.FirstSurname AS firstSurname,
  p.SecondSurname AS secondSurname,
  p.DocumentTypeId AS documentTypeId,p.Document AS document,c.Phone AS phone,
  CONVERT(nvarchar(50),NULL) AS alternatePhone,p.Email AS email,
  p.AspirationPeriodId AS periodId,pe.Periodo AS period,
  CONVERT(int,NULL) AS offerPeriodId,CONVERT(varchar(50),NULL) AS offerPeriod,
  c.ProgramId AS programId,c.Program AS program,c.City AS city,
  CONCAT(p.GivenNames,' ',p.FirstSurname,' ',p.SecondSurname) AS structuredName
 FROM crm.Contact c LEFT JOIN crm_identity.Profile p ON p.ContactId=c.ContactId
 LEFT JOIN dbo.GEPeriodo pe ON pe.Id_Periodo=p.AspirationPeriodId
 WHERE (@own IS NULL OR c.ContactId<>@own)
 AND c.ContactId NOT IN(SELECT CONVERT(uniqueidentifier,value) FROM OPENJSON(@excluded))
 UNION ALL
 SELECT 'applicant',CONVERT(varchar(36),a.Id_Aspirante),NULL,
  LTRIM(RTRIM(CONCAT(a.NombreAspirante,' ',a.PrimerApellido,' ',a.SegundoApellido))),
  a.NombreAspirante,a.PrimerApellido,a.SegundoApellido,a.TipoId,a.Id_DocAspirante,
  a.Celular,a.Telefono,a.Mail,a.Id_Periodo,pe.Periodo,o.Id_Periodo,op.Periodo,
  pr.Id_Programa,pr.NombrePrograma,CONVERT(nvarchar(100),NULL),
  CONCAT(a.NombreAspirante,' ',a.PrimerApellido,' ',a.SegundoApellido)
 FROM dbo.ACAspirante a LEFT JOIN dbo.GEPeriodo pe ON pe.Id_Periodo=a.Id_Periodo
 LEFT JOIN dbo.ACProgramaOfrecido o ON o.Id_PrgOfrecido=a.Id_PrgOfrecido
 LEFT JOIN dbo.GEPeriodo op ON op.Id_Periodo=o.Id_Periodo
 LEFT JOIN dbo.ACProgramas pr ON pr.Id_Programa=o.Id_Programa
 UNION ALL
 SELECT 'student',CONVERT(varchar(36),e.Id_Estudiante),NULL,
  LTRIM(RTRIM(CONCAT(e.Nombres,' ',e.PrimerApellido,' ',e.SegundoApellido))),
  e.Nombres,e.PrimerApellido,e.SegundoApellido,e.TipoId,e.Id_DocEstudiante,
  e.Celular,e.Telefono,e.Mail,o.Id_Periodo,pe.Periodo,o.Id_Periodo,pe.Periodo,
  pr.Id_Programa,pr.NombrePrograma,pob.Nmbre,
  CONCAT(e.Nombres,' ',e.PrimerApellido,' ',e.SegundoApellido)
 FROM dbo.GEEstudiante e LEFT JOIN dbo.ACProgramaOfrecido o
  ON o.Id_PrgOfrecido=e.Id_PrgOfrecido
 LEFT JOIN dbo.GEPeriodo pe ON pe.Id_Periodo=o.Id_Periodo
 LEFT JOIN dbo.ACProgramas pr ON pr.Id_Programa=o.Id_Programa
 LEFT JOIN dbo.GEPoblacion pob ON pob.Id_Poblacion=e.Id_Poblacion
), candidates AS (
 SELECT *,CASE WHEN @docType IS NOT NULL AND @document<>N'' AND documentTypeId=@docType
  AND LTRIM(RTRIM(document)) COLLATE Latin1_General_100_BIN2
   =@document COLLATE Latin1_General_100_BIN2 THEN 1 ELSE 0 END AS documentMatch,
  CASE WHEN @email<>N'' AND LOWER(LTRIM(RTRIM(email)))
   COLLATE Latin1_General_100_BIN2=LOWER(@email) COLLATE Latin1_General_100_BIN2
   THEN 1 ELSE 0 END AS emailMatch,
  CASE WHEN @phone<>N'' AND (LTRIM(RTRIM(phone)) COLLATE Latin1_General_100_BIN2
   =@phone COLLATE Latin1_General_100_BIN2
   OR LTRIM(RTRIM(alternatePhone)) COLLATE Latin1_General_100_BIN2
   =@phone COLLATE Latin1_General_100_BIN2) THEN 1 ELSE 0 END AS phoneMatch
 FROM records WHERE @source='all' OR source=@source
)
SELECT source,sourceId,contactId,name,givenNames,firstSurname,secondSurname,
 documentTypeId,document,phone,alternatePhone,email,periodId,period,offerPeriodId,
 offerPeriod,programId,program,city,documentMatch,emailMatch,phoneMatch
FROM candidates WHERE
 (@mode='identity' AND (documentMatch=1 OR emailMatch=1 OR phoneMatch=1)) OR
 (@mode='name' AND (name LIKE @name OR structuredName LIKE @name)
  AND (@period IS NULL OR periodId=@period)
  AND (@program IS NULL OR programId=@program))
ORDER BY documentMatch DESC,emailMatch DESC,phoneMatch DESC,
 CASE source WHEN 'crm' THEN 0 WHEN 'student' THEN 1 ELSE 2 END,sourceId
OFFSET @offset ROWS FETCH NEXT 26 ROWS ONLY;
"""


class InstitutionalIdentity:
    def __init__(self, workspace):
        self.workspace = workspace

    def catalog(self):
        periods = AdmissionsRepository(self.workspace).periods()
        with self.workspace.transaction() as cursor:
            return {
                "documentTypes": rows(
                    cursor.execute(
                        "SELECT TipoId AS id,NmbreTpoIdntdad AS label,Abrvtra AS code "
                        "FROM dbo.GETipoIdentidad ORDER BY TipoId"
                    )
                ),
                "periods": periods,
            }

    def lookup(self, body):
        result = {
            "items": [],
            "offset": body.offset,
            "limit": 25,
            "hasMore": False,
            "mode": body.mode,
            "criteriaRequired": not body.available(),
            "identityScope": "all_periods_and_programs"
            if body.mode == "identity"
            else "selected_period_and_program",
        }
        if not body.available():
            return result
        with self.workspace.transaction() as cursor:
            available(cursor, required=True)
            import json

            from app.modules.contacts.application.merge import membership, relations

            links = relations(cursor)
            excluded = (
                membership(cursor, body.ownContactId)["memberContactIds"]
                if body.ownContactId and links
                else []
            )
            validate_catalogs(
                cursor, body.documentTypeId, body.periodId, body.programId
            )
            found = rows(
                cursor.execute(
                    LOOKUP_SQL,
                    body.mode,
                    body.source,
                    body.ownContactId,
                    body.documentTypeId,
                    body.document,
                    body.usable_email(),
                    body.phone if sum(c.isdigit() for c in body.phone) >= 5 else "",
                    search_pattern(body.name),
                    body.periodId,
                    body.programId,
                    body.offset,
                    json.dumps(excluded),
                )
            )
        for item in found:
            item["sourceId"] = str(item["sourceId"]).lower()
            if item.get("contactId"):
                item["contactId"] = str(item["contactId"]).lower()
                item["canonicalContactId"] = next(
                    (
                        link["targetContactId"]
                        for link in links
                        if link["sourceContactId"] == item["contactId"]
                    ),
                    item["contactId"],
                )
            item["reasons"] = (
                (["same_document_type_and_number"] if item.pop("documentMatch") else [])
                + (["same_email"] if item.pop("emailMatch") else [])
                + (["same_phone"] if item.pop("phoneMatch") else [])
            )
            if body.mode == "name":
                item["reasons"].append("name_search")
        return {**result, "items": found[:25], "hasMore": len(found) > 25}


def install_institutional_identity(app: FastAPI):
    app.state.institutional_identity = InstitutionalIdentity(app.state.sql_workspace)
    router = APIRouter(
        prefix="/api/local/crm/identity", tags=["local-institutional-identity"]
    )

    def call(request, method, *args):
        if request.app.state.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_disabled")
        try:
            return JSONResponse(
                getattr(request.app.state.institutional_identity, method)(*args),
                headers={"Cache-Control": "no-store"},
            )
        except (pyodbc.Error, CatalogUnavailable):
            raise HTTPException(503, "identity_lookup_unavailable") from None

    @router.get("/catalog")
    def catalog(request: Request):
        return call(request, "catalog")

    @router.post("/candidates")
    def lookup(request: Request, body: IdentityLookup):
        return call(request, "lookup", body)

    app.include_router(router)
