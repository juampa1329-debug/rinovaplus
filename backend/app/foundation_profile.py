"""Load only the separately prepared encrypted foundation profile; no SQL or DDL."""

from pathlib import Path

from app import foundation
from app.config import Settings
from app.sql_profile import SqlProfileStore
from app.sql_target import validate_settings


def load_settings(directory: Path) -> Settings:
    if not directory.is_absolute():
        raise ValueError("Absolute private foundation profile directory required")
    profile = SqlProfileStore(directory / "runtime").load()
    if profile is None:
        raise ValueError("Prepared foundation profile required")
    c, review = profile["connection"], profile["review"]
    if c["database"] != foundation.DATABASE or c["username"] != foundation.PRINCIPAL:
        raise ValueError("Foundation profile target changed")
    settings = Settings(
        mode="local_foundation",
        sql_environment="foundation_rehearsal",
        sql_host=c["server"],
        sql_port=c["port"],
        sql_database=c["database"],
        sql_user=c["username"],
        sql_password=c["password"],
        sql_certificate_hostname=c["certificate_hostname"],
        sql_expected_machine=review["machine"],
        sql_expected_server=review["server"],
        sql_expected_login=foundation.PRINCIPAL,
        sql_expected_database_user=foundation.PRINCIPAL,
        foundation_ticket_path=str(directory / "runtime-ticket.json"),
        foundation_ticket_sha256=review["ticket_sha256"],
    )
    validate_settings(settings)
    foundation.ticket(settings)
    return settings
