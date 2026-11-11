"""C9 private UI profile loader. No provider key is loaded or generated."""

from pathlib import Path

from app.channels_ui_contract import principal, ticket
from app.config import Settings
from app.sql_profile import SqlProfileStore
from app.sql_target import validate_settings


def load_settings(directory: Path) -> Settings:
    if not directory.is_absolute():
        raise ValueError("Absolute channels UI profile directory required")
    value = SqlProfileStore(directory / "runtime").load()
    if value is None:
        raise ValueError("Prepared channels UI profile required")
    c, review = value["connection"], value["review"]
    if c["username"] != principal(c["database"]):
        raise ValueError("Channels UI profile target changed")
    result = Settings(
        mode="local_channels_ui",
        sql_environment="channels_ui_rehearsal",
        sql_host=c["server"],
        sql_port=c["port"],
        sql_database=c["database"],
        sql_user=c["username"],
        sql_password=c["password"],
        sql_certificate_hostname=c["certificate_hostname"],
        sql_expected_machine=review["machine"],
        sql_expected_server=review["server"],
        sql_expected_login=c["username"],
        sql_expected_database_user=c["username"],
        channels_ticket_path=str(directory / "runtime-ticket.json"),
        channels_ticket_sha256=review["ticket_sha256"],
    )
    validate_settings(result)
    ticket(result)
    return result
