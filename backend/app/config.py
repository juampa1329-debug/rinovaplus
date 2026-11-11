"""Explicit local modes and opt-in SQL TCP transport without a TLS escape hatch."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from app.sql_target import LOCAL_SERVER, validate_settings


@dataclass(frozen=True)
class Settings:
    mode: str = "local_demo"
    catalog_token: str = field(default="", repr=False)
    meta_verify_token_sha256: str = field(default="", repr=False)
    sql_user: str = field(default="", repr=False)
    sql_password: str = field(default="", repr=False)
    sql_host: str = ""
    sql_port: int = 1433
    sql_environment: str = "local_copy"
    sql_database: str = "DBSIIE"
    sql_server: str = LOCAL_SERVER
    sql_expected_machine: str = ""
    sql_expected_server: str = ""
    sql_expected_instance: str = "SQLEXPRESS"
    sql_expected_login: str = field(default="", repr=False)
    sql_expected_database_user: str = field(default="", repr=False)
    sql_certificate_hostname: str = ""
    foundation_ticket_path: str = field(default="", repr=False)
    foundation_ticket_sha256: str = ""
    channels_ticket_path: str = field(default="", repr=False)
    channels_ticket_sha256: str = ""
    channels_key_path: str = field(default="", repr=False)
    channels_key_sha256: str = field(default="", repr=False)
    catalog_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )

    @classmethod
    def from_environment(cls) -> "Settings":
        mode = os.environ.get("CRM_APP_MODE", "local_demo")
        profile_directory = os.environ.get("CRM_FOUNDATION_PROFILE_DIR", "")
        channels_directory = os.environ.get("CRM_CHANNELS_PROFILE_DIR", "")
        ui_directory = os.environ.get("CRM_CHANNELS_UI_PROFILE_DIR", "")
        if ui_directory or mode == "local_channels_ui":
            if (
                mode != "local_channels_ui"
                or not ui_directory
                or profile_directory
                or channels_directory
            ):
                raise ValueError("Independent channels UI profile required")
            from app.channels_ui_profile import load_settings as load_channels_ui

            return load_channels_ui(Path(ui_directory))
        if channels_directory or mode == "local_channels":
            if mode != "local_channels" or not channels_directory or profile_directory:
                raise ValueError("Independent channels rehearsal profile required")
            from app.channels_profile import load_settings as load_channels

            return load_channels(Path(channels_directory))
        if profile_directory:
            if mode != "local_foundation":
                raise ValueError("Foundation profile requires explicit foundation mode")
            from app.foundation_profile import load_settings

            return load_settings(Path(profile_directory))
        if mode not in (
            "local_demo",
            "local_readonly_catalog",
            "local_sql_copy",
            "local_foundation",
        ):
            raise ValueError(
                "Only CRM_APP_MODE=local_demo, local_readonly_catalog, "
                "local_sql_copy or local_foundation is supported"
            )
        token = os.environ.get("CRM_CATALOG_TOKEN", "")
        user = os.environ.get("CRM_SQL_USER", "")
        password = os.environ.get("CRM_SQL_PASSWORD", "")
        host = os.environ.get("CRM_SQL_HOST", "")
        port = os.environ.get("CRM_SQL_PORT", "")
        machine = os.environ.get("CRM_SQL_EXPECTED_MACHINE", "")
        certificate_hostname = os.environ.get("CRM_SQL_CERTIFICATE_HOSTNAME", "")
        environment = os.environ.get("CRM_SQL_ENVIRONMENT", "local_copy")
        if port and not host:
            raise ValueError("SQL TCP port requires an explicit host")
        if port and (
            not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535
        ):
            raise ValueError("SQL TCP port must be an integer from 1 to 65535")
        if (
            environment in ("institutional", "foundation_rehearsal")
            or mode == "local_sql_copy"
        ) and not port:
            raise ValueError("SQL target requires an explicit TCP port")
        if environment == "institutional" and not os.environ.get("CRM_SQL_DATABASE"):
            raise ValueError("Institutional SQL requires an explicit database")
        origins = tuple(
            os.environ.get(
                "CRM_CATALOG_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
            ).split(",")
        )
        if mode in ("local_readonly_catalog", "local_sql_copy", "local_foundation"):
            if mode == "local_readonly_catalog" and (
                len(token) < 32 or not token.isascii() or not token.isalnum()
            ):
                raise ValueError(
                    "Local catalog requires a random alphanumeric token "
                    "of at least 32 characters"
                )
            for origin in origins:
                parsed = urlsplit(origin)
                if (
                    parsed.scheme != "http"
                    or parsed.hostname not in ("localhost", "127.0.0.1")
                    or parsed.username
                    or parsed.password
                    or parsed.path
                    or parsed.query
                    or parsed.fragment
                    or not parsed.port
                ):
                    raise ValueError(
                        "Catalog origins must be explicit HTTP loopback origins"
                    )
        settings = cls(
            mode=mode,
            catalog_token=token,
            meta_verify_token_sha256=os.environ.get("CRM_META_VERIFY_TOKEN_SHA256", ""),
            sql_user=user,
            sql_password=password,
            sql_host=host,
            sql_port=int(port) if port else 1433,
            sql_environment=environment,
            sql_database=os.environ.get("CRM_SQL_DATABASE") or "DBSIIE",
            sql_server=os.environ.get("CRM_SQL_SERVER", LOCAL_SERVER),
            sql_expected_machine=machine,
            sql_expected_server=os.environ.get("CRM_SQL_EXPECTED_SERVER", ""),
            sql_expected_instance=os.environ.get("CRM_SQL_EXPECTED_INSTANCE")
            or ("" if environment == "institutional" else "SQLEXPRESS"),
            sql_expected_login=os.environ.get("CRM_SQL_EXPECTED_LOGIN", ""),
            sql_expected_database_user=os.environ.get(
                "CRM_SQL_EXPECTED_DATABASE_USER", ""
            ),
            sql_certificate_hostname=certificate_hostname,
            foundation_ticket_path=os.environ.get("CRM_FOUNDATION_TICKET_PATH", ""),
            foundation_ticket_sha256=os.environ.get("CRM_FOUNDATION_TICKET_SHA256", ""),
            catalog_origins=origins,
        )
        validate_settings(settings)
        return settings
