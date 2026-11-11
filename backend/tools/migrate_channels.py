"""Apply only the explicit additive channels migration to the verified local copy."""

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
        cursor = connection.cursor()
        connection.timeout = 15
        cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;")
        verify_target(cursor, settings)
        for filename in ("011_channels.sql", "012_channels_identity_collation.sql"):
            cursor.execute(
                Path(__file__)
                .resolve()
                .parents[1]
                .joinpath("migrations", filename)
                .read_text(encoding="utf-8")
            )
            while cursor.nextset():
                pass
        connection.commit()
        print(
            "CRM-channels-v1 applied to verified local DBSIIE; core schema unchanged."
        )
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
