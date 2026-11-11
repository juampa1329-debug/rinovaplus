"""Fixed read-only catalog adapter; permission metadata precedes business SQL."""

from threading import BoundedSemaphore

import pyodbc
from pydantic import ValidationError

from app.config import Settings
from app.sql_target import connection_string, verify_identity
from app.modules.catalog.domain.contracts import (
    CatalogUnavailable,
    Modality,
    Period,
    Program,
    School,
)

pyodbc.pooling = False

PERIOD_SQL = """
SELECT Id_Periodo, Periodo, FechaInicio, FechaFinal, EstadoPeriodo
FROM dbo.GEPeriodo
ORDER BY Id_Periodo ASC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
"""
SCHOOL_SQL = """
SELECT Id_Escuela, NomEsla
FROM dbo.ACEscuela
ORDER BY Id_Escuela ASC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
"""
MODALITY_SQL = """
SELECT Id_Modalidad, Modalidad
FROM dbo.ACModalidad
ORDER BY Id_Modalidad ASC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
"""
PROGRAM_SQL = """
SELECT Id_Programa, NombrePrograma, Id_Escuela, Id_Modalidad
FROM dbo.ACProgramas
WHERE (CAST(? AS int) IS NULL OR Id_Escuela = ?)
  AND (CAST(? AS int) IS NULL OR Id_Modalidad = ?)
ORDER BY Id_Programa ASC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
"""
PRINCIPAL_SQL = """
SELECT IS_SRVROLEMEMBER('sysadmin'), IS_MEMBER('db_owner'),
       IS_MEMBER('db_datareader'), IS_MEMBER('db_datawriter'),
       HAS_PERMS_BY_NAME('dbo.GEPeriodo', 'OBJECT', 'SELECT'),
       HAS_PERMS_BY_NAME('dbo.ACEscuela', 'OBJECT', 'SELECT', 'Id_Escuela', 'COLUMN'),
       HAS_PERMS_BY_NAME('dbo.ACEscuela', 'OBJECT', 'SELECT', 'NomEsla', 'COLUMN'),
       HAS_PERMS_BY_NAME('dbo.ACModalidad', 'OBJECT', 'SELECT',
                         'Id_Modalidad', 'COLUMN'),
       HAS_PERMS_BY_NAME('dbo.ACModalidad', 'OBJECT', 'SELECT', 'Modalidad', 'COLUMN'),
       HAS_PERMS_BY_NAME('dbo.ACProgramas', 'OBJECT', 'SELECT',
                         'Id_Programa', 'COLUMN'),
       HAS_PERMS_BY_NAME('dbo.ACProgramas', 'OBJECT', 'SELECT',
                         'NombrePrograma', 'COLUMN'),
       HAS_PERMS_BY_NAME('dbo.ACProgramas', 'OBJECT', 'SELECT', 'Id_Escuela', 'COLUMN'),
       HAS_PERMS_BY_NAME('dbo.ACProgramas', 'OBJECT', 'SELECT',
                         'Id_Modalidad', 'COLUMN')
"""
PERMISSION_SQL = """
SELECT 'SERVER', permission_name, '' FROM sys.fn_my_permissions(NULL, 'SERVER')
UNION ALL
SELECT 'DATABASE', permission_name, '' FROM sys.fn_my_permissions(NULL, 'DATABASE')
UNION ALL
SELECT 'SCHEMA', p.permission_name, ISNULL(p.subentity_name, '')
FROM sys.schemas s
CROSS APPLY sys.fn_my_permissions(QUOTENAME(s.name), 'SCHEMA') p
UNION ALL
SELECT CASE WHEN o.object_id = OBJECT_ID('dbo.GEPeriodo')
            THEN 'PERIOD'
            WHEN o.object_id = OBJECT_ID('dbo.ACEscuela') THEN 'SCHOOL'
            WHEN o.object_id = OBJECT_ID('dbo.ACModalidad') THEN 'MODALITY'
            WHEN o.object_id = OBJECT_ID('dbo.ACProgramas') THEN 'PROGRAM'
            WHEN o.type = 'PK' AND o.parent_object_id IN (
                OBJECT_ID('dbo.GEPeriodo'), OBJECT_ID('dbo.ACEscuela'),
                OBJECT_ID('dbo.ACModalidad'), OBJECT_ID('dbo.ACProgramas')) THEN 'KEY'
            ELSE 'OTHER' END, p.permission_name,
       ISNULL(p.subentity_name, '') AS column_name
FROM sys.objects o
CROSS APPLY sys.fn_my_permissions(
    QUOTENAME(OBJECT_SCHEMA_NAME(o.object_id)) + '.' + QUOTENAME(o.name), 'OBJECT') p
WHERE o.is_ms_shipped = 0
"""
ALLOWED_PERMISSIONS = {
    "SERVER": {"CONNECT SQL", "VIEW ANY DATABASE"},
    "DATABASE": {
        "CONNECT",
        "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
        "VIEW ANY COLUMN MASTER KEY DEFINITION",
    },
    "SCHEMA": set(),
    "PERIOD": {"SELECT"},
    "KEY": {"SELECT"},
    "SCHOOL": {"SELECT"},
    "MODALITY": {"SELECT"},
    "PROGRAM": {"SELECT"},
    "OTHER": set(),
}
ALLOWED_COLUMNS = {
    "SERVER": {""},
    "DATABASE": {""},
    "SCHEMA": set(),
    "OTHER": set(),
    "PERIOD": {
        "",
        "Id_Periodo",
        "Periodo",
        "FechaInicio",
        "FechaFinal",
        "EstadoPeriodo",
    },
    "KEY": {""},
    "SCHOOL": {"Id_Escuela", "NomEsla"},
    "MODALITY": {"Id_Modalidad", "Modalidad"},
    "PROGRAM": {"Id_Programa", "NombrePrograma", "Id_Escuela", "Id_Modalidad"},
}


def verify_principal(cursor) -> None:
    flags = cursor.execute(PRINCIPAL_SQL).fetchone()
    if flags is None or tuple(flags) != (0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1):
        raise CatalogUnavailable()
    permissions = cursor.execute(PERMISSION_SQL).fetchall()
    if not permissions or any(
        permission not in ALLOWED_PERMISSIONS.get(scope, set())
        or column not in ALLOWED_COLUMNS.get(scope, set())
        for scope, permission, column in permissions
    ):
        raise CatalogUnavailable()


class SqlCatalogReader:
    def __init__(self, settings: Settings):
        self._capacity = BoundedSemaphore(1)
        self._settings = settings

    def read_periods(self, limit: int, offset: int) -> list[Period]:
        try:
            return [
                Period(
                    id=row[0],
                    label=row[1],
                    startDate=row[2],
                    endDate=row[3],
                    sourceState=row[4],
                )
                for row in self._read(PERIOD_SQL, limit, offset)
            ]
        except ValidationError as error:
            raise CatalogUnavailable() from error

    def read_schools(self, limit: int, offset: int) -> list[School]:
        try:
            return [
                School(id=row[0], label=row[1])
                for row in self._read(SCHOOL_SQL, limit, offset)
            ]
        except ValidationError as error:
            raise CatalogUnavailable() from error

    def read_modalities(self, limit: int, offset: int) -> list[Modality]:
        try:
            return [
                Modality(id=row[0], label=row[1])
                for row in self._read(MODALITY_SQL, limit, offset)
            ]
        except ValidationError as error:
            raise CatalogUnavailable() from error

    def read_programs(
        self, limit: int, offset: int, school_id: int | None, modality_id: int | None
    ) -> list[Program]:
        try:
            return [
                Program(id=row[0], label=row[1], schoolId=row[2], modalityId=row[3])
                for row in self._read(
                    PROGRAM_SQL,
                    limit,
                    offset,
                    (school_id, school_id, modality_id, modality_id),
                )
            ]
        except ValidationError as error:
            raise CatalogUnavailable() from error

    def _read(
        self, sql: str, limit: int, offset: int, filters: tuple = ()
    ) -> list[tuple]:
        if not self._capacity.acquire(blocking=False):
            raise CatalogUnavailable()
        connection = None
        cursor = None
        try:
            connection = pyodbc.connect(
                connection_string(self._settings, catalog=True),
                timeout=5,
                autocommit=True,
                readonly=True,
            )
            connection.timeout = 5
            cursor = connection.cursor()
            verify_principal(cursor)
            verify_identity(cursor, self._settings)
            rows = cursor.execute(sql, *filters, offset, limit).fetchmany(limit)
            return rows
        except (pyodbc.Error, ValueError) as error:
            raise CatalogUnavailable() from error
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                try:
                    if connection is not None:
                        connection.close()
                finally:
                    self._capacity.release()
