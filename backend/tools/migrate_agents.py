"""Explicit local-only migration. Preflight never applies schema changes."""

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
    connection = pyodbc.connect(
        connection_string(settings), timeout=5, autocommit=False
    )
    try:
        connection.timeout = 30
        cursor = connection.cursor()
        cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000;")
        verify_target(cursor, settings)
        contract = cursor.execute(
            (
                "SELECT CONVERT(nvarchar(80),value) FROM sys.extended_properties "
                "WHERE class=3 AND major_id=SCHEMA_ID(N'crm_agents') AND "
                "name=N'crm_agents.contract'"
            )
        ).fetchval()
        exists = (
            cursor.execute("SELECT SCHEMA_ID(N'crm_agents')").fetchval() is not None
        )
        if options.preflight or contract == "admissions-agents-v1":
            if exists and contract != "admissions-agents-v1":
                raise SystemExit("agents_schema_unrecognized")
            if exists:
                for table, column in (
                    ("Profile", "ApprovedVersion"),
                    ("Stage", "ApprovedRevision"),
                    ("Context", "StageRevision"),
                    ("Assignment", "BaselineSequence"),
                    ("SourceScope", "ValidUntil"),
                    ("History", "PayloadHash"),
                    ("Usage", "TokensReserved"),
                ):
                    if (
                        cursor.execute(
                            "SELECT COL_LENGTH(?,?)", "crm_agents." + table, column
                        ).fetchval()
                        is None
                    ):
                        raise SystemExit("agents_schema_shape_unrecognized")
                for table, column in (
                    ("Profile", "Revision"),
                    ("SourceScope", "DocumentRevision"),
                ):
                    if (
                        cursor.execute(
                            "SELECT COL_LENGTH(?,?)", "crm_agents." + table, column
                        ).fetchval()
                        is None
                    ):
                        raise SystemExit("agents_schema_shape_unrecognized")
            print(
                "Verified local target; agents contract "
                + (
                    "already installed; no changes."
                    if exists
                    else "not installed; preflight only."
                )
            )
            connection.rollback()
            return
        if exists:
            raise SystemExit("agents_schema_unrecognized")
        cursor.execute(
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("migrations", "019_admissions_agents.sql")
            .read_text(encoding="utf-8")
        )
        while cursor.nextset():
            pass
        verify_target(cursor, settings)
        connection.commit()
        print(
            "Admissions-agents-v1 applied to verified local copy; no transport enabled."
        )
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
