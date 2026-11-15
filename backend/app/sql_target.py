"""Pure SQL Server 2019 target contract. Importing this module performs no IO."""

import re
from typing import TYPE_CHECKING

from app.branding import PRODUCT_NAME

if TYPE_CHECKING:
    from app.config import Settings

HOST = re.compile(
    r"(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*"
)
LOCAL_SERVER = r"localhost\SQLEXPRESS"
IDENTITY_SQL = """SELECT DB_NAME(),
    CONVERT(nvarchar(128), SERVERPROPERTY('InstanceName')),
    CONVERT(nvarchar(128), SERVERPROPERTY('MachineName')),
    CONVERT(nvarchar(128), SERVERPROPERTY('ServerName')),
    CONVERT(int, SERVERPROPERTY('ProductMajorVersion')),
    (SELECT compatibility_level FROM sys.databases WHERE database_id=DB_ID()),
    CONVERT(int, SERVERPROPERTY('EngineEdition')),
    CONVERT(nvarchar(128), SERVERPROPERTY('Edition')),
    ORIGINAL_LOGIN(), SUSER_SNAME(), USER_NAME()"""


def _name(value: str) -> bool:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 128
        and value == value.strip()
        and all(ord(char) >= 32 and ord(char) != 127 for char in value)
    )


def validate_settings(settings: "Settings") -> None:
    """Validate environment and direct Settings construction at the IO boundary."""
    if settings.mode not in (
        "local_demo",
        "local_readonly_catalog",
        "local_sql_copy",
        "local_foundation",
        "local_channels",
        "local_channels_ui",
    ):
        raise ValueError("Unsupported application mode")
    if settings.sql_environment not in (
        "local_copy",
        "institutional",
        "foundation_rehearsal",
        "channels_rehearsal",
        "channels_ui_rehearsal",
    ):
        raise ValueError("Unsupported SQL environment")
    if not _name(settings.sql_database):
        raise ValueError("Invalid SQL database name")
    if type(settings.sql_port) is not int or not 1 <= settings.sql_port <= 65535:
        raise ValueError("SQL TCP port must be an integer from 1 to 65535")
    if settings.sql_host and not HOST.fullmatch(settings.sql_host):
        raise ValueError("SQL TCP host must be a DNS name or IPv4 address")
    if settings.sql_certificate_hostname and not HOST.fullmatch(
        settings.sql_certificate_hostname
    ):
        raise ValueError("Invalid SQL certificate hostname")
    if bool(settings.sql_user) != bool(settings.sql_password):
        raise ValueError("SQL credentials must be supplied together")
    if settings.sql_host and not settings.sql_user:
        raise ValueError("SQL TCP requires a restricted SQL user and password")
    for value in (settings.sql_user, settings.sql_password):
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Invalid SQL credentials")
    for value in (
        settings.sql_expected_machine,
        settings.sql_expected_server,
        settings.sql_expected_instance,
        settings.sql_expected_login,
        settings.sql_expected_database_user,
    ):
        if value and not _name(value):
            raise ValueError("Invalid SQL identity expectation")
    if (
        settings.mode == "local_channels_ui"
        or settings.sql_environment == "channels_ui_rehearsal"
    ):
        from pathlib import Path

        from app.channels_ui_contract import principal

        if not (
            settings.mode == "local_channels_ui"
            and settings.sql_environment == "channels_ui_rehearsal"
            and settings.sql_server == LOCAL_SERVER
            and settings.sql_host in ("localhost", "127.0.0.1", "host.docker.internal")
            and settings.sql_certificate_hostname == "localhost"
            and settings.sql_expected_instance == "SQLEXPRESS"
            and settings.sql_user
            == settings.sql_expected_login
            == principal(settings.sql_database)
            and settings.sql_expected_database_user == settings.sql_user
            and settings.sql_expected_machine
            and settings.sql_expected_server
            and settings.channels_ticket_path
            and Path(settings.channels_ticket_path).is_absolute()
            and re.fullmatch(r"[0-9a-f]{64}", settings.channels_ticket_sha256)
            and not settings.channels_key_path
            and not settings.channels_key_sha256
        ):
            raise ValueError("Explicit isolated channels UI profile required")
        return
    if (
        settings.mode == "local_channels"
        or settings.sql_environment == "channels_rehearsal"
    ):
        from pathlib import Path

        from app.channels_contract import principal

        if not (
            settings.mode == "local_channels"
            and settings.sql_environment == "channels_rehearsal"
            and settings.sql_server == LOCAL_SERVER
            and settings.sql_host in ("localhost", "127.0.0.1", "host.docker.internal")
            and settings.sql_certificate_hostname == "localhost"
            and settings.sql_expected_instance == "SQLEXPRESS"
            and settings.sql_user
            == settings.sql_expected_login
            == principal(settings.sql_database)
            and settings.sql_expected_database_user == settings.sql_user
            and settings.sql_expected_machine
            and settings.sql_expected_server
            and settings.channels_ticket_path
            and Path(settings.channels_ticket_path).is_absolute()
            and settings.channels_key_path
            and Path(settings.channels_key_path).is_absolute()
            and re.fullmatch(r"[0-9a-f]{64}", settings.channels_ticket_sha256)
            and re.fullmatch(r"[0-9a-f]{64}", settings.channels_key_sha256)
        ):
            raise ValueError("Explicit isolated channels rehearsal profile required")
        return
    if (
        settings.mode == "local_foundation"
        or settings.sql_environment == "foundation_rehearsal"
    ):
        # This isolated local SQL2022 rehearsal does not relax the SQL2019 contract.
        from app.foundation import DATABASE, PRINCIPAL

        if not (
            settings.mode == "local_foundation"
            and settings.sql_environment == "foundation_rehearsal"
            and settings.sql_database == DATABASE
            and settings.sql_server == LOCAL_SERVER
            and settings.sql_host in ("localhost", "127.0.0.1", "host.docker.internal")
            and settings.sql_certificate_hostname == "localhost"
            and settings.sql_expected_instance == "SQLEXPRESS"
            and settings.sql_user == settings.sql_expected_login == PRINCIPAL
            and settings.sql_expected_database_user == PRINCIPAL
            and settings.sql_expected_machine
            and settings.sql_expected_server
            and settings.foundation_ticket_path
            and re.fullmatch(r"[0-9a-f]{64}", settings.foundation_ticket_sha256)
        ):
            raise ValueError("Explicit isolated foundation rehearsal profile required")
        return
    if settings.sql_environment == "institutional":
        if settings.mode == "local_sql_copy":
            raise ValueError("Institutional SQL cannot enable local-copy writes")
        if not all(
            (
                settings.sql_host,
                settings.sql_certificate_hostname,
                settings.sql_expected_machine,
                settings.sql_expected_server,
                settings.sql_expected_instance,
                settings.sql_expected_login,
                settings.sql_expected_database_user,
            )
        ):
            raise ValueError(
                "Institutional SQL requires explicit transport and identity"
            )
    elif (
        settings.sql_database != "DBSIIE"
        or settings.sql_expected_instance != "SQLEXPRESS"
        or settings.sql_server != LOCAL_SERVER
    ):
        raise ValueError(
            "Local SQL target must remain the approved DBSIIE/SQLEXPRESS copy"
        )
    if settings.mode == "local_sql_copy":
        if settings.sql_host not in ("localhost", "127.0.0.1", "host.docker.internal"):
            raise ValueError("Local SQL copy requires an explicit local TCP endpoint")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", settings.sql_expected_machine):
            raise ValueError("Local SQL copy requires the approved machine identity")
        if settings.sql_certificate_hostname != "localhost":
            raise ValueError("Local SQL copy requires the validated certificate name")


def _quoted(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def connection_string(settings: "Settings", *, catalog: bool = False) -> str:
    validate_settings(settings)
    if settings.sql_environment == "institutional" and not catalog:
        raise ValueError("Institutional SQL workspace is not enabled in P1.2")
    if catalog and settings.mode in (
        "local_foundation",
        "local_channels",
        "local_channels_ui",
    ):
        raise ValueError("Academic catalog is not enabled in the foundation rehearsal")
    if not catalog and settings.mode not in (
        "local_sql_copy",
        "local_foundation",
        "local_channels",
        "local_channels_ui",
    ):
        raise ValueError("SQL workspace requires explicit local-copy mode")
    server = (
        f"tcp:{settings.sql_host},{settings.sql_port}"
        if settings.sql_host
        else LOCAL_SERVER
    )
    certificate = (
        f"HostnameInCertificate={settings.sql_certificate_hostname};"
        if settings.sql_certificate_hostname
        else ""
    )
    authentication = (
        f"UID={_quoted(settings.sql_user)};PWD={_quoted(settings.sql_password)};"
        if settings.sql_user
        else "Trusted_Connection=Yes;"
    )
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};DATABASE={_quoted(settings.sql_database)};"
        "Encrypt=Yes;TrustServerCertificate=No;"
        f"{certificate}{authentication}"
        f"APP={PRODUCT_NAME} {'local catalog' if catalog else 'local copy'};"
    )


def verify_identity(cursor, settings: "Settings") -> None:
    """Fail closed on absent/incorrect metadata before any business statement."""
    validate_settings(settings)
    row = cursor.execute(IDENTITY_SQL).fetchone()
    if row is None or len(row) != 11:
        raise ValueError("SQL target identity could not be verified")
    (
        database,
        instance,
        machine,
        server,
        major,
        compat,
        engine,
        edition,
        login,
        effective,
        user,
    ) = row
    expected_instance = (
        None
        if settings.sql_expected_instance == "DEFAULT"
        else settings.sql_expected_instance
    )
    if (
        database != settings.sql_database
        or instance != expected_instance
        or not all(
            _name(value) for value in (machine, server, edition, login, effective, user)
        )
        or major != 15
        or type(compat) is not int
        or compat not in (130, 140, 150)
        or engine not in (2, 3, 4)
        or (settings.sql_expected_machine and machine != settings.sql_expected_machine)
        or (settings.sql_expected_server and server != settings.sql_expected_server)
        or (
            settings.sql_expected_login
            and (
                login != settings.sql_expected_login
                or effective != settings.sql_expected_login
            )
        )
        or (
            settings.sql_expected_database_user
            and user != settings.sql_expected_database_user
        )
    ):
        raise ValueError("SQL target identity does not match the approved contract")
