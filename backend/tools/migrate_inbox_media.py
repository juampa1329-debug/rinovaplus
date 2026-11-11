"""Apply only additive media migration 016 to the authorized local copy."""

from pathlib import Path

import pyodbc

from app.config import Settings
from app.environment import load_environment
from app.sql_workspace import connection_string, verify_target


def main():
    load_environment()
    settings = Settings.from_environment()
    if settings.mode != "local_sql_copy":
        raise SystemExit("local_sql_copy_required")
    connection = pyodbc.connect(
        connection_string(settings), timeout=5, autocommit=False
    )
    try:
        connection.timeout = 15
        cursor = connection.cursor()
        cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;")
        verify_target(cursor, settings)
        cursor.execute(
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("migrations", "016_inbox_media.sql")
            .read_text(encoding="utf-8")
        )
        while cursor.nextset():
            pass
        verify_target(cursor, settings)
        connection.commit()
        print(
            "Inbox-media-v1 applied to verified local DBSIIE; legacy/core shape preserved."
        )
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
