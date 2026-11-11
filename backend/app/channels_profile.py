"""Load the independent C8 encrypted profile; no SQL on import or load."""

from pathlib import Path

from app.channels_contract import principal, ticket
from app.config import Settings
from app.sql_profile import SqlProfileStore
from app.sql_target import validate_settings


def load_settings(directory: Path) -> Settings:
    if not directory.is_absolute():
        raise ValueError("Absolute private channels profile directory required")
    profile = SqlProfileStore(directory / "runtime").load()
    if profile is None:
        raise ValueError("Prepared channels profile required")
    c, review = profile["connection"], profile["review"]
    if c["username"] != principal(c["database"]):
        raise ValueError("Channels profile target changed")
    result = Settings(
        mode="local_channels",
        sql_environment="channels_rehearsal",
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
        channels_key_path=str(directory / "channels-aes256.key"),
        channels_key_sha256=review["credential_key_sha256"],
    )
    validate_settings(result)
    ticket(result)
    return result
