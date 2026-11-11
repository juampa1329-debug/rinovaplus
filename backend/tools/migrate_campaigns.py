"""Explicit local-only marketing migration; no transport activation."""

import argparse
from pathlib import Path

import pyodbc

from app.config import Settings
from app.environment import load_environment
from app.sql_workspace import connection_string, verify_target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    options = parser.parse_args()
    load_environment()
    settings = Settings.from_environment()
    if settings.mode != "local_sql_copy":
        raise SystemExit("local_sql_copy_required")
    connection = pyodbc.connect(connection_string(settings), timeout=5, autocommit=False)
    try:
        connection.timeout = 20
        cursor = connection.cursor()
        cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;")
        verify_target(cursor, settings)
        exists = cursor.execute("SELECT SCHEMA_ID(N'crm_marketing')").fetchval() is not None
        if options.preflight:
            print("Verified local target; marketing schema " + ("already exists." if exists else "not installed."))
            connection.rollback()
            return
        if exists:
            raise SystemExit("marketing_schema_already_exists_inspect_before_change")
        # pyodbc autocommit=False starts the caller-owned transaction with the SELECT above.
        cursor.execute(Path(__file__).resolve().parents[1].joinpath("migrations", "018_campaigns.sql").read_text(encoding="utf-8"))
        while cursor.nextset():
            pass
        verify_target(cursor, settings)
        connection.commit()
        print("Campaigns-v1 applied to verified local copy; marketing transport disabled.")
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
