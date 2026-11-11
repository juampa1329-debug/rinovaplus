"""Local SQL selection and read-only metadata, separate from CRM activation."""

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import BoundedSemaphore

import pyodbc
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import Field, SecretStr, field_validator

from app.schemas import LocalModel
from app.sql_profile import ProfileUnavailable, SqlProfileStore
from app.sql_target import HOST, _name, _quoted

DATABASES_SQL = """SELECT name FROM sys.databases
WHERE database_id > 4 AND state_desc=N'ONLINE' AND HAS_DBACCESS(name)=1 ORDER BY name"""
VISIBILITY_SQL = """SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION'),
IS_SRVROLEMEMBER('sysadmin')"""
IDENTITY_SQL = """SELECT DB_NAME(),
CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')),
CONVERT(nvarchar(128),SERVERPROPERTY('MachineName')),
CONVERT(nvarchar(128),SERVERPROPERTY('InstanceName')),
CONVERT(int,SERVERPROPERTY('ProductMajorVersion')),
CONVERT(nvarchar(128),SERVERPROPERTY('Edition')),
(SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID())"""
TABLES_SQL = """SELECT SCHEMA_NAME(schema_id) AS schema_name,name AS table_name
FROM sys.tables WHERE is_ms_shipped=0 ORDER BY schema_name,table_name"""
COLUMNS_SQL = """SELECT SCHEMA_NAME(t.schema_id),t.name,c.name,
TYPE_NAME(c.user_type_id),c.max_length,c.precision,c.scale,c.is_nullable,c.column_id
FROM sys.tables t JOIN sys.columns c ON c.object_id=t.object_id
WHERE t.is_ms_shipped=0 ORDER BY SCHEMA_NAME(t.schema_id),t.name,c.column_id"""
RELATIONS_SQL = """SELECT f.name,SCHEMA_NAME(t.schema_id),t.name,c.name,
SCHEMA_NAME(rt.schema_id),rt.name,rc.name,k.constraint_column_id,f.is_disabled,f.is_not_trusted
FROM sys.foreign_keys f
JOIN sys.foreign_key_columns k ON k.constraint_object_id=f.object_id
JOIN sys.tables t ON t.object_id=k.parent_object_id
JOIN sys.columns c ON c.object_id=t.object_id AND c.column_id=k.parent_column_id
JOIN sys.tables rt ON rt.object_id=k.referenced_object_id
JOIN sys.columns rc ON rc.object_id=rt.object_id AND rc.column_id=k.referenced_column_id
WHERE t.is_ms_shipped=0 ORDER BY f.name,k.constraint_column_id"""
ACADEMIC_TABLES = {
    "dbo.GEPeriodo",
    "dbo.ACEscuela",
    "dbo.ACModalidad",
    "dbo.ACProgramas",
    "dbo.GEEmpleado",
    "dbo.ACAspirante",
    "dbo.ACProgramaOfrecido",
    "dbo.GEEstudiante",
}
CRM_TABLES = {"crm.Contact", "crm.Conversation", "crm.Message", "crm.Operation"}


class ConnectionRequest(LocalModel):
    server: str = Field(min_length=1, max_length=253)
    port: int = Field(default=1433, ge=1, le=65535)
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(default=SecretStr(""), max_length=4096)
    certificate_hostname: str = Field(min_length=1, max_length=253)
    database: str = Field(default="", max_length=128)
    revision: int = Field(default=0, ge=0)

    @field_validator("server", "certificate_hostname")
    @classmethod
    def host(cls, value):
        if not HOST.fullmatch(value):
            raise ValueError("invalid_host")
        return value.lower()

    @field_validator("username", "database")
    @classmethod
    def name(cls, value):
        if value and not _name(value):
            raise ValueError("invalid_name")
        return value

    @field_validator("password")
    @classmethod
    def secret(cls, value):
        if any(ord(c) < 32 or ord(c) == 127 for c in value.get_secret_value()):
            raise ValueError("invalid_secret")
        return value


def unavailable(code: str, status: int = 503):
    raise HTTPException(status, detail=code)


class DatabaseConnections:
    def __init__(self, store: SqlProfileStore):
        self.store = store
        # One backend process, as configured in Docker; not a cross-process CAS.
        self.capacity = BoundedSemaphore(1)

    def saved(self):
        try:
            return self.store.load()
        except ProfileUnavailable:
            unavailable("sql_profile_storage_unavailable")

    def default(self):
        return {
            "server": os.environ.get("CRM_SQL_HOST") or "host.docker.internal",
            "port": int(os.environ.get("CRM_SQL_PORT") or 1433),
            "username": os.environ.get("CRM_SQL_USER", ""),
            "password": os.environ.get("CRM_SQL_PASSWORD", ""),
            "certificate_hostname": os.environ.get("CRM_SQL_CERTIFICATE_HOSTNAME")
            or "localhost",
            "database": "",
        }

    def status(self):
        saved = self.saved()
        source = saved["connection"] if saved else self.default()
        return {
            "revision": saved["revision"] if saved else 0,
            "connection": {
                k: source[k]
                for k in (
                    "server",
                    "port",
                    "username",
                    "certificate_hostname",
                    "database",
                )
            },
            "has_password": bool(source["password"]),
            "source": "saved" if saved else "environment",
            "review": saved.get("review") if saved else None,
            "scope": "metadata_only",
        }

    def credentials(self, request):
        if request.password.get_secret_value():
            return request.password.get_secret_value()
        saved = self.saved()
        candidates = ([saved["connection"]] if saved else []) + [self.default()]
        for candidate in candidates:
            if (
                all(
                    candidate[k] == getattr(request, k)
                    for k in ("server", "port", "username", "certificate_hostname")
                )
                and candidate["password"]
            ):
                return candidate["password"]
        unavailable("sql_credentials_required", 422)

    @contextmanager
    def session(self, request, database):
        if not self.capacity.acquire(blocking=False):
            unavailable("sql_connection_busy", 409)
        connection = cursor = None
        try:
            password = self.credentials(request)
            text = (
                "DRIVER={ODBC Driver 18 for SQL Server};"
                f"SERVER=tcp:{request.server},{request.port};DATABASE={_quoted(database)};"
                "Encrypt=Yes;TrustServerCertificate=No;"
                f"HostnameInCertificate={request.certificate_hostname};"
                f"UID={_quoted(request.username)};PWD={_quoted(password)};"
                "APP=CRM CBN database metadata;"
            )
            connection = pyodbc.connect(text, timeout=5, autocommit=True, readonly=True)
            connection.timeout = 10
            cursor = connection.cursor()
            yield cursor, password
        except pyodbc.Error as error:
            code = "sql_connection_failed"
            if error.args and error.args[0] == "28000":
                code = "sql_login_or_database_denied"
            unavailable(code)
        finally:
            try:
                if cursor is not None:
                    cursor.close()
            finally:
                try:
                    if connection is not None:
                        connection.close()
                finally:
                    self.capacity.release()

    @staticmethod
    def rows(cursor, query, limit):
        rows = cursor.execute(query).fetchmany(limit + 1)
        if len(rows) > limit:
            unavailable("sql_metadata_limit", 422)
        return [list(row) for row in rows]

    def discover(self, request):
        with self.session(request, "master") as (cursor, _):
            return {"databases": [r[0] for r in self.rows(cursor, DATABASES_SQL, 500)]}

    def inspect(self, request, *, save=False, schema=False):
        if not request.database:
            unavailable("sql_database_required", 422)
        with self.session(request, request.database) as (cursor, password):
            identity = cursor.execute(IDENTITY_SQL).fetchone()
            if (
                identity is None
                or len(identity) != 7
                or identity[0] != request.database
            ):
                unavailable("sql_identity_unavailable")
            if not all(identity[i] for i in (1, 2, 4, 5, 6)):
                unavailable("sql_identity_unavailable")
            tables = self.rows(cursor, TABLES_SQL, 10000)
            columns = self.rows(cursor, COLUMNS_SQL, 200000)
            relations = self.rows(cursor, RELATIONS_SQL, 100000)
            visibility = cursor.execute(VISIBILITY_SQL).fetchone()
            names = {".".join(r) for r in tables}
            review = {
                "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "database": identity[0],
                "server_name": identity[1],
                "machine_name": identity[2],
                "instance": identity[3],
                "engine_major": identity[4],
                "edition": identity[5],
                "compatibility_level": identity[6],
                "fingerprint": hashlib.sha256(
                    json.dumps(list(identity)).encode()
                ).hexdigest(),
                "table_count": len(tables),
                "column_count": len(columns),
                "relation_count": len({tuple(r[:3]) for r in relations}),
                "missing_academic_tables": sorted(ACADEMIC_TABLES - names),
                "missing_crm_tables": sorted(CRM_TABLES - names),
                "sql2019_engine": identity[4] == 15,
                "crm_activation": "not_activated",
                "metadata_visibility": "database"
                if visibility and 1 in visibility
                else "restricted",
                "schema_acceptance": "not_evaluated",
            }
            if save:
                current = self.saved()
                revision = current["revision"] if current else 0
                if request.revision != revision:
                    unavailable("sql_profile_changed", 409)
                profile = request.model_dump(exclude={"password", "revision"})
                profile["password"] = password
                try:
                    self.store.save(
                        {
                            "revision": revision + 1,
                            "connection": profile,
                            "review": review,
                        }
                    )
                except ProfileUnavailable:
                    unavailable("sql_profile_storage_unavailable")
            result = {"review": review}
            if save:
                result["revision"] = revision + 1
            if schema:
                result.update(tables=tables, columns=columns, relations=relations)
            return result


def install_database_connections(application: FastAPI):
    directory = application.state.ai_service.repository.path.parent / "database"
    service = DatabaseConnections(SqlProfileStore(Path(directory)))
    application.state.database_connections = service

    def private(value):
        return JSONResponse(value, headers={"Cache-Control": "no-store"})

    @application.get("/api/local/database")
    def status():
        return private(service.status())

    @application.post("/api/local/database/discover")
    def discover(request: ConnectionRequest):
        return private(service.discover(request))

    @application.post("/api/local/database/test")
    def test(request: ConnectionRequest):
        return private(service.inspect(request))

    @application.put("/api/local/database")
    def save(request: ConnectionRequest):
        return private(service.inspect(request, save=True))

    @application.post("/api/local/database/schema")
    def schema(request: ConnectionRequest):
        return private(service.inspect(request, schema=True))
