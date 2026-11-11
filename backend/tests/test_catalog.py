from datetime import date
from unittest.mock import Mock

import pyodbc
import pytest
from fastapi.testclient import TestClient

from app.modules.catalog.domain.contracts import CatalogUnavailable, Modality, Period, Program, School
from app.config import Settings
from app.main import create_app
from app.modules.catalog.infrastructure.sql_reader import (
    MODALITY_SQL,
    PERIOD_SQL,
    PERMISSION_SQL,
    PRINCIPAL_SQL,
    PROGRAM_SQL,
    SCHOOL_SQL,
    SqlCatalogReader,
)

TOKEN = "SyntheticTestAccessKey01234567890123456789"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CRM_APP_MODE", "local_readonly_catalog")
    monkeypatch.setenv("CRM_CATALOG_TOKEN", TOKEN)
    app = create_app()
    app.state.catalog_reader = Mock()
    app.state.catalog_reader.read_periods.return_value = []
    app.state.catalog_reader.read_schools.return_value = []
    app.state.catalog_reader.read_modalities.return_value = []
    app.state.catalog_reader.read_programs.return_value = []
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client, app.state.catalog_reader


def get(client, path="", **kwargs):
    return client.get(
        "/api/v1/catalog/periods" + path,
        headers={"Authorization": f"Bearer {TOKEN}"},
        **kwargs,
    )


def test_default_page_empty_and_health_stays_unready(client):
    http, reader = client
    response = get(http)
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": {"limit": 25, "offset": 0, "hasMore": False},
    }
    assert response.headers["cache-control"] == "no-store"
    reader.read_periods.assert_called_once_with(26, 0)
    assert http.get("/health/ready").status_code == 503
    assert http.get("/health/live").json()["mode"] == "local_readonly_catalog"


def test_dates_state_ids_and_limit_plus_one(client):
    http, reader = client
    reader.read_periods.return_value = [
        Period(
            id=-1,
            label="Synthetic period",
            startDate=date(2020, 1, 1),
            endDate=date(2020, 3, 1),
            sourceState=False,
        ),
        Period(
            id=0,
            label="Another",
            startDate=date(2021, 1, 1),
            endDate=date(2021, 3, 1),
            sourceState=True,
        ),
    ]
    response = get(http, "?limit=1&offset=25")
    assert response.status_code == 200
    assert response.json()["items"][0] == {
        "id": -1,
        "label": "Synthetic period",
        "startDate": "2020-01-01",
        "endDate": "2020-03-01",
        "sourceState": False,
    }
    assert response.json()["page"] == {"limit": 1, "offset": 25, "hasMore": True}
    reader.read_periods.assert_called_once_with(2, 25)


@pytest.mark.parametrize(
    "query",
    [
        "?limit=0",
        "?limit=101",
        "?offset=10001",
        "?offset=-1",
        "?limit=1.5",
        "?limit=1&limit=2",
        "?offset=0&offset=0",
        "?sort=id",
        "?limit=1;DROP",
        "?limit=",
        "?limit=%2B1",
    ],
)
def test_invalid_query_never_reads(client, query):
    http, reader = client
    response = get(http, query)
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REQUEST"
    reader.read_periods.assert_not_called()


@pytest.mark.parametrize(
    "authorization", [None, "Bearer wrong", "Basic x", "Bearer " + TOKEN + " extra"]
)
def test_authentication_precedes_sql_and_validation(client, authorization):
    http, reader = client
    response = http.get(
        "/api/v1/catalog/periods?sort=private",
        headers={} if authorization is None else {"Authorization": authorization},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert TOKEN not in response.text
    reader.read_periods.assert_not_called()


def test_duplicate_authorization_denied(client):
    http, reader = client
    response = http.get(
        "/api/v1/catalog/periods",
        headers=[
            ("Authorization", f"Bearer {TOKEN}"),
            ("Authorization", f"Bearer {TOKEN}"),
        ],
    )
    assert response.status_code == 401
    reader.read_periods.assert_not_called()


@pytest.mark.parametrize(
    "exception,status,code",
    [
        (CatalogUnavailable("secret SQL password"), 503, "CATALOG_UNAVAILABLE"),
        (RuntimeError("private server"), 500, "INTERNAL_ERROR"),
    ],
)
def test_errors_are_sanitized_and_have_new_correlations(
    client, exception, status, code
):
    http, reader = client
    reader.read_periods.side_effect = exception
    first, second = get(http), get(http)
    assert first.status_code == status
    assert first.json()["code"] == code
    assert set(first.json()) == {"code", "message", "correlationId"}
    assert first.json()["correlationId"] != second.json()["correlationId"]
    assert str(exception) not in first.text


def test_disabled_catalog_never_reads(monkeypatch):
    monkeypatch.setenv("CRM_APP_MODE", "local_demo")
    app = create_app()
    app.state.catalog_reader = Mock()
    with TestClient(app) as client:
        assert get(client).status_code == 503
    app.state.catalog_reader.read_periods.assert_not_called()


def test_host_and_cors_restricted(client):
    http, reader = client
    assert (
        http.get(
            "/api/v1/catalog/periods",
            headers={"Host": "evil.example", "Authorization": f"Bearer {TOKEN}"},
        ).status_code
        == 400
    )
    reader.read_periods.assert_not_called()
    for origin, allowed in [
        ("http://127.0.0.1:5173", True),
        ("https://evil.example", False),
    ]:
        response = http.options(
            "/api/v1/catalog/periods",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert (
            response.headers.get("access-control-allow-origin") == origin
        ) is allowed


@pytest.mark.parametrize(
    "name,value",
    [
        ("CRM_SQL_SERVER", "remote"),
        ("CRM_SQL_DATABASE", "Other"),
        ("CRM_CATALOG_TOKEN", "short"),
        ("CRM_CATALOG_ORIGINS", "https://example.com"),
        ("CRM_CATALOG_ORIGINS", "http://localhost:5173/path"),
        ("CRM_SQL_USER", "unpaired"),
    ],
)
def test_unsafe_configuration_rejected(monkeypatch, name, value):
    monkeypatch.setenv("CRM_APP_MODE", "local_readonly_catalog")
    monkeypatch.setenv("CRM_CATALOG_TOKEN", TOKEN)
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        Settings.from_environment()


def fake_sql(monkeypatch, flags=(0, 0, 0, 0, 1), permissions=None, rows=None):
    cursor = Mock()
    cursor.execute.return_value = cursor
    cursor.fetchone.return_value = (
        None if flags is None else tuple(flags) + (1,) * (13 - len(flags))
    )
    principal = cursor.fetchone.return_value

    def execute(sql, *args):
        from app.sql_target import IDENTITY_SQL

        cursor.fetchone.return_value = (
            ("DBSIIE", "SQLEXPRESS", "TESTMACHINE", r"TESTMACHINE\SQLEXPRESS",
             15, 150, 4, "Express Edition", "reader", "reader", "reader")
            if sql == IDENTITY_SQL else principal
        )
        return cursor

    cursor.execute.side_effect = execute
    cursor.fetchall.return_value = (
        permissions
        if permissions is not None
        else [
            ("SERVER", "CONNECT SQL"),
            ("DATABASE", "CONNECT"),
            ("DATABASE", "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION"),
            ("DATABASE", "VIEW ANY COLUMN MASTER KEY DEFINITION"),
            ("PERIOD", "SELECT"),
        ]
    )
    cursor.fetchall.return_value = [
        tuple(permission) + (("",) if len(permission) == 2 else ())
        for permission in cursor.fetchall.return_value
    ]
    cursor.fetchmany.return_value = (
        rows
        if rows is not None
        else [(1, "Synthetic", date(2020, 1, 1), date(2020, 12, 31), True)]
    )
    connection = Mock()
    connection.cursor.return_value = cursor
    connect = Mock(return_value=connection)
    monkeypatch.setattr("app.modules.catalog.infrastructure.sql_reader.pyodbc.connect", connect)
    return cursor, connection, connect


def test_sql_is_fixed_parameterized_tls_and_closes(monkeypatch):
    cursor, connection, connect = fake_sql(monkeypatch)
    result = SqlCatalogReader(Settings()).read_periods(26, 25)
    assert result[0].startDate == date(2020, 1, 1)
    assert cursor.execute.call_args_list[-1].args == (PERIOD_SQL, 25, 26)
    assert cursor.execute.call_args_list[0].args == (PRINCIPAL_SQL,)
    assert cursor.execute.call_args_list[1].args == (PERMISSION_SQL,)
    assert (
        "SELECT Id_Periodo, Periodo, FechaInicio, FechaFinal, EstadoPeriodo"
        in PERIOD_SQL
    )
    assert "COUNT" not in PERIOD_SQL
    assert "Encrypt=Yes;TrustServerCertificate=No;" in connect.call_args.args[0]
    assert connect.call_args.kwargs == {
        "timeout": 5,
        "autocommit": True,
        "readonly": True,
    }
    assert connection.timeout == 5
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "flags",
    [
        (1, 0, 0, 0, 1),
        (0, 1, 0, 0, 1),
        (0, 0, 1, 0, 1),
        (0, 0, 0, 1, 1),
        (0, 0, 0, 0, 0),
        (None, 0, 0, 0, 1),
    ],
)
def test_admin_broad_or_missing_privileges_deny_before_business_query(
    monkeypatch, flags
):
    cursor, connection, _ = fake_sql(monkeypatch, flags=flags)
    with pytest.raises(CatalogUnavailable):
        SqlCatalogReader(Settings()).read_periods(26, 0)
    assert cursor.execute.call_count == 1
    cursor.fetchmany.assert_not_called()
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "permission",
    [
        ("SERVER", "CONTROL SERVER"),
        ("DATABASE", "SELECT"),
        ("DATABASE", "IMPERSONATE ANY USER"),
        ("SCHEMA", "SELECT"),
        ("PERIOD", "UPDATE"),
        ("PERIOD", "ALTER"),
        ("OTHER", "SELECT"),
        ("OTHER", "EXECUTE"),
    ],
)
def test_excess_effective_permissions_deny(monkeypatch, permission):
    cursor, connection, _ = fake_sql(monkeypatch, permissions=[permission])
    with pytest.raises(CatalogUnavailable):
        SqlCatalogReader(Settings()).read_periods(26, 0)
    cursor.fetchmany.assert_not_called()
    assert cursor.execute.call_count == 2
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "inherited_permission,allowed",
    [
        (("PERIOD", "SELECT"), True),
        (("PERIOD", "ALTER"), False),
        (("OTHER", "SELECT"), False),
        (("OTHER", "EXECUTE"), False),
    ],
)
def test_inherited_catalog_permission_keeps_exact_read_boundary(
    monkeypatch, inherited_permission, allowed
):
    # SQL Server reports table/column SELECT plus inherited PK permissions.
    # Classification is checked separately against the real SQL metadata.
    permissions = [("DATABASE", "CONNECT")] + [("PERIOD", "SELECT")] * 6
    cursor, connection, _ = fake_sql(
        monkeypatch, permissions=permissions + [inherited_permission]
    )
    reader = SqlCatalogReader(Settings())
    if allowed:
        assert reader.read_periods(26, 0)[0].id == 1
        assert cursor.execute.call_args_list[-1].args == (PERIOD_SQL, 0, 26)
    else:
        with pytest.raises(CatalogUnavailable):
            reader.read_periods(26, 0)
        cursor.fetchmany.assert_not_called()
        assert cursor.execute.call_count == 2
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "row",
    [
        (None, "x", date(2020, 1, 1), date(2020, 2, 1), True),
        (1, None, date(2020, 1, 1), date(2020, 2, 1), True),
        (1, "x", None, date(2020, 2, 1), True),
        (1, "x", date(2020, 1, 1), date(2020, 2, 1), 1),
        (2147483648, "x", date(2020, 1, 1), date(2020, 2, 1), True),
    ],
)
def test_source_schema_drift_fails_closed(monkeypatch, row):
    _, connection, _ = fake_sql(monkeypatch, rows=[row])
    with pytest.raises(CatalogUnavailable):
        SqlCatalogReader(Settings()).read_periods(26, 0)
    connection.close.assert_called_once()


def test_timeout_releases_capacity_and_closes(monkeypatch):
    cursor, connection, _ = fake_sql(monkeypatch)
    cursor.execute.side_effect = pyodbc.OperationalError("private SQL")
    reader = SqlCatalogReader(Settings())
    with pytest.raises(CatalogUnavailable):
        reader.read_periods(26, 0)
    connection.close.assert_called_once()
    assert reader._capacity.acquire(blocking=False)
    reader._capacity.release()


def test_busy_does_not_connect(monkeypatch):
    _, _, connect = fake_sql(monkeypatch)
    reader = SqlCatalogReader(Settings())
    reader._capacity.acquire()
    try:
        with pytest.raises(CatalogUnavailable):
            reader.read_periods(26, 0)
        connect.assert_not_called()
    finally:
        reader._capacity.release()


@pytest.mark.parametrize(
    "resource,method,dto",
    [("schools", "read_schools", School), ("modalities", "read_modalities", Modality)],
)
def test_named_catalog_projection_and_pagination(client, resource, method, dto):
    http, reader = client
    selected_reader = getattr(reader, method)
    selected_reader.return_value = [
        dto(id=-1, label="Same synthetic label"),
        dto(id=3, label="Same synthetic label"),
    ]
    response = http.get(
        f"/api/v1/catalog/{resource}?limit=1&offset=25",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "items": [{"id": -1, "label": "Same synthetic label"}],
        "page": {"limit": 1, "offset": 25, "hasMore": True},
    }
    assert response.headers["cache-control"] == "no-store"
    selected_reader.assert_called_once_with(2, 25)
    reader.read_periods.assert_not_called()


@pytest.mark.parametrize(
    "resource,method", [("schools", "read_schools"), ("modalities", "read_modalities")]
)
@pytest.mark.parametrize(
    "query,status",
    [
        ("", 401),
        ("?limit=0", 422),
        ("?offset=10001", 422),
        ("?limit=25&limit=25", 422),
        ("?schoolId=1", 422),
        ("?limit=1;DROP", 422),
    ],
)
def test_named_catalog_auth_and_query_before_sql(
    client, resource, method, query, status
):
    http, reader = client
    headers = {} if status == 401 else {"Authorization": f"Bearer {TOKEN}"}
    response = http.get(f"/api/v1/catalog/{resource}{query}", headers=headers)
    assert response.status_code == status
    getattr(reader, method).assert_not_called()


@pytest.mark.parametrize(
    "resource,method", [("schools", "read_schools"), ("modalities", "read_modalities")]
)
@pytest.mark.parametrize(
    "exception,status",
    [(CatalogUnavailable("private SQL"), 503), (RuntimeError("private failure"), 500)],
)
def test_named_catalog_sanitizes_errors(client, resource, method, exception, status):
    http, reader = client
    getattr(reader, method).side_effect = exception
    response = http.get(
        f"/api/v1/catalog/{resource}", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert response.status_code == status
    assert str(exception) not in response.text
    assert set(response.json()) == {"code", "message", "correlationId"}


@pytest.mark.parametrize(
    "method,sql", [("read_schools", SCHOOL_SQL), ("read_modalities", MODALITY_SQL)]
)
def test_named_sql_uses_exact_projection_parameters_and_closes(
    monkeypatch, method, sql
):
    cursor, connection, connect = fake_sql(monkeypatch, rows=[(-1, "Synthetic label")])
    result = getattr(SqlCatalogReader(Settings()), method)(26, 25)
    assert result[0].model_dump() == {"id": -1, "label": "Synthetic label"}
    assert cursor.execute.call_args_list[-1].args == (sql, 25, 26)
    assert "Encrypt=Yes;TrustServerCertificate=No;" in connect.call_args.args[0]
    assert connection.timeout == 5
    cursor.close.assert_called_once()
    connection.close.assert_called_once()


@pytest.mark.parametrize("method", ["read_schools", "read_modalities"])
@pytest.mark.parametrize(
    "row", [(None, "Synthetic"), (1, None), (float("inf"), "Synthetic")]
)
def test_named_source_null_or_type_drift_is_unavailable(monkeypatch, method, row):
    _, connection, _ = fake_sql(monkeypatch, rows=[row])
    with pytest.raises(CatalogUnavailable):
        getattr(SqlCatalogReader(Settings()), method)(26, 0)
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "permission",
    [
        ("SCHOOL", "SELECT", ""),
        ("SCHOOL", "SELECT", "Correo"),
        ("SCHOOL", "SELECT", "UrlEscuela"),
        ("SCHOOL", "SELECT", "Id_CstvoEmpld"),
        ("MODALITY", "SELECT", ""),
        ("MODALITY", "SELECT", "DescripcionMod"),
        ("KEY", "UPDATE", ""),
        ("KEY", "SELECT", "unexpected"),
        ("OTHER", "SELECT", ""),
        ("OTHER", "EXECUTE", ""),
    ],
)
def test_column_guard_rejects_full_tables_extra_columns_and_other_keys(
    monkeypatch, permission
):
    cursor, connection, _ = fake_sql(monkeypatch, permissions=[permission])
    with pytest.raises(CatalogUnavailable):
        SqlCatalogReader(Settings()).read_schools(26, 0)
    cursor.fetchmany.assert_not_called()
    assert cursor.execute.call_count == 2
    connection.close.assert_called_once()


def test_column_guard_accepts_only_authorized_columns_and_own_key_metadata(monkeypatch):
    cursor, _, _ = fake_sql(
        monkeypatch,
        permissions=[
            ("PERIOD", "SELECT", ""),
            ("SCHOOL", "SELECT", "Id_Escuela"),
            ("SCHOOL", "SELECT", "NomEsla"),
            ("MODALITY", "SELECT", "Id_Modalidad"),
            ("MODALITY", "SELECT", "Modalidad"),
            ("KEY", "SELECT", ""),
        ],
        rows=[(1, "Synthetic")],
    )
    assert SqlCatalogReader(Settings()).read_schools(26, 0)[0].id == 1
    assert cursor.execute.call_args_list[-1].args == (SCHOOL_SQL, 0, 26)


@pytest.mark.parametrize("missing_column", [5, 6, 7, 8])
def test_missing_required_column_fails_before_permission_scan(
    monkeypatch, missing_column
):
    flags = [0, 0, 0, 0, 1, 1, 1, 1, 1]
    flags[missing_column] = 0
    cursor, _, _ = fake_sql(monkeypatch, flags=flags)
    with pytest.raises(CatalogUnavailable):
        SqlCatalogReader(Settings()).read_modalities(26, 0)
    assert cursor.execute.call_count == 1
    cursor.fetchmany.assert_not_called()


def test_catalogs_share_one_capacity_slot(monkeypatch):
    _, _, connect = fake_sql(monkeypatch)
    reader = SqlCatalogReader(Settings())
    reader._capacity.acquire()
    try:
        for method in (
            reader.read_periods,
            reader.read_schools,
            reader.read_modalities,
        ):
            with pytest.raises(CatalogUnavailable):
                method(26, 0)
        connect.assert_not_called()
    finally:
        reader._capacity.release()


@pytest.mark.parametrize(
    "query,school,modality",
    [
        ("", None, None),
        ("?schoolId=-1", -1, None),
        ("?modalityId=0", None, 0),
        ("?schoolId=2147483647&modalityId=-2147483648", 2147483647, -2147483648),
    ],
)
def test_programs_optional_filters_and_nullable_name(client, query, school, modality):
    http, reader = client
    reader.read_programs.return_value = [
        Program(id=-5, label=None, schoolId=-1, modalityId=0)
    ]
    response = http.get(
        "/api/v1/catalog/programs" + query, headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["items"] == [
        {"id": -5, "label": None, "schoolId": -1, "modalityId": 0}
    ]
    reader.read_programs.assert_called_once_with(26, 0, school, modality)
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "query",
    [
        "schoolId=",
        "schoolId=null",
        "schoolId=true",
        "schoolId=1.0",
        "schoolId=1e2",
        "schoolId=%2B1",
        "schoolId=--1",
        "schoolId=%D9%A1",
        "schoolId=1;DROP",
        "schoolId=2147483648",
        "modalityId=-2147483649",
        "modalityId=1&modalityId=2",
        "otherId=2",
    ],
)
def test_program_bad_filters_never_reach_sql(client, query):
    http, reader = client
    response = http.get(
        "/api/v1/catalog/programs?" + query,
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 422
    reader.read_programs.assert_not_called()


@pytest.mark.parametrize("resource", ["periods", "schools", "modalities"])
def test_program_filters_stay_forbidden_on_other_resources(client, resource):
    http, reader = client
    response = http.get(
        f"/api/v1/catalog/{resource}?schoolId=1",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 422
    assert reader.mock_calls == []


def test_program_auth_precedes_filter_validation(client):
    http, reader = client
    response = http.get("/api/v1/catalog/programs?schoolId=private-invalid")
    assert response.status_code == 401
    reader.read_programs.assert_not_called()


def test_program_nonexistent_filter_returns_empty_without_additional_reads(client):
    http, reader = client
    response = http.get(
        "/api/v1/catalog/programs?schoolId=-1234",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert reader.mock_calls == [("read_programs", (26, 0, -1234, None), {})]


@pytest.mark.parametrize(
    "school,modality", [(None, None), (1, None), (None, -2), (1, -2)]
)
def test_program_static_projection_and_nullable_bound_parameters(
    monkeypatch, school, modality
):
    cursor, connection, _ = fake_sql(monkeypatch, rows=[(-1, None, 1, -2)])
    result = SqlCatalogReader(Settings()).read_programs(26, 25, school, modality)
    assert result[0].model_dump() == {
        "id": -1,
        "label": None,
        "schoolId": 1,
        "modalityId": -2,
    }
    assert cursor.execute.call_args_list[-1].args == (
        PROGRAM_SQL,
        school,
        school,
        modality,
        modality,
        25,
        26,
    )
    assert cursor.execute.call_count == 4
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "column", ["", "CodigoPrograma", "Id_Jornada", "Semestres", "FechaInicio"]
)
def test_program_guard_rejects_full_table_and_extra_columns(monkeypatch, column):
    cursor, _, _ = fake_sql(monkeypatch, permissions=[("PROGRAM", "SELECT", column)])
    with pytest.raises(CatalogUnavailable):
        SqlCatalogReader(Settings()).read_programs(26, 0, None, None)
    cursor.fetchmany.assert_not_called()


@pytest.mark.parametrize("missing", [9, 10, 11, 12])
def test_program_required_columns_fail_closed(monkeypatch, missing):
    flags = [0, 0, 0, 0] + [1] * 9
    flags[missing] = 0
    cursor, _, _ = fake_sql(monkeypatch, flags=flags)
    with pytest.raises(CatalogUnavailable):
        SqlCatalogReader(Settings()).read_programs(26, 0, None, None)
    assert cursor.execute.call_count == 1


def test_program_column_allowlist_and_projection(monkeypatch):
    permissions = [
        ("PROGRAM", "SELECT", column)
        for column in ("Id_Programa", "NombrePrograma", "Id_Escuela", "Id_Modalidad")
    ]
    _, _, _ = fake_sql(
        monkeypatch,
        permissions=permissions + [("KEY", "SELECT", "")],
        rows=[(1, "", 2, 3)],
    )
    assert SqlCatalogReader(Settings()).read_programs(26, 0, 2, 3)[0].label == ""
