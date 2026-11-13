
"""Print SQL for the DBA to inventory tables or review dedicated runtime grants."""

import argparse

from app.institutional.deployment import TEST_DATABASE
from app.institutional.operations_policy import columns, layout, rights
from app.institutional.spanish import RIGHTS
from app.parity_channels.policy import COLUMNS
from tools.foundation_snapshot import quote_name
from tools.rehearse_foundation import literal


def database_guard(database):
    if database.lower() != "dbsiie" and not TEST_DATABASE.fullmatch(database):
        raise ValueError("Use dbsiie or a named RinovaPlus rehearsal")
    return f"IF DB_NAME() <> {literal(database)} THROW 50001, 'Unexpected database', 1;"


def render_inventory(database):
    guard = database_guard(database)
    mapping = layout()
    expected = [
        (domain, *table.split(".", 1))
        for domain, tables in (
            ("CRM", mapping["tables"].values()), ("SIIE", mapping["academic_tables"])
        )
        for table in sorted(set(tables))
    ]
    values = ",\n    ".join(
        f"({literal(domain)}, {literal(schema)}, {literal(table)})"
        for domain, schema, table in expected
    )
    return f"""-- Read-only. Run while connected to the specified database.
{guard}
IF HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION') <> 1
    THROW 50002, 'Database VIEW DEFINITION is required for a complete inventory', 1;

WITH expected AS (
    SELECT v.domain, v.schema_name, v.table_name
    FROM (VALUES
    {values}
    ) v(domain, schema_name, table_name)
)
SELECT e.domain, e.schema_name, e.table_name,
       CASE WHEN t.object_id IS NULL THEN 'MISSING' ELSE 'PRESENT' END AS status
FROM expected e
LEFT JOIN sys.schemas s ON s.name COLLATE Latin1_General_100_BIN2 = e.schema_name
LEFT JOIN sys.tables t ON t.schema_id = s.schema_id AND t.is_ms_shipped = 0
    AND t.name COLLATE Latin1_General_100_BIN2 = e.table_name
ORDER BY status, e.domain, e.schema_name, e.table_name;"""


def render(database, login):
    guard = database_guard(database)
    if not login.strip() or len(login) > 128 or any(ord(c) < 32 for c in login):
        raise ValueError("Invalid SQL login name")
    name = quote_name(login)
    mapping = layout()
    lines = [
        "-- REVIEW ONLY. Run on a restored integration copy first.",
        "-- The login must already exist. Create it separately with a private password.",
        "-- Review explicit table grants and execute as the DBA. Starts with no implicit USE.",
        "SET XACT_ABORT ON;",
        guard,
        f"IF SUSER_ID({literal(login)}) IS NULL OR USER_ID({literal(login)}) IS NOT NULL",
        "    THROW 50002, 'Use an existing dedicated login with no database user yet', 1;",
    ]
    for table in sorted(set(mapping["tables"].values()) | set(mapping["academic_tables"])):
        lines.append(
            f"IF OBJECT_ID({literal(table)}, 'U') IS NULL "
            f"THROW 50003, {literal('Missing table: ' + table)}, 1;"
        )
    lines.extend([
        "BEGIN TRANSACTION;",
        f"CREATE USER {name} FOR LOGIN {name} WITH DEFAULT_SCHEMA=dbo;",
        f"GRANT CONNECT, VIEW DEFINITION TO {name};",
    ])
    for table, allowed in sorted(rights(RIGHTS).items()):
        physical = mapping['tables'].get(table, table)
        lines.append(f"GRANT {', '.join(allowed)} ON OBJECT::{physical} TO {name};")
    for table, allowed in sorted(columns(COLUMNS).items()):
        column_names = ", ".join(quote_name(item) for item in allowed)
        lines.append(f"GRANT SELECT ON OBJECT::{mapping['tables'][table]} ({column_names}) TO {name};")
    lines.extend([
        "-- Inspect grants before deciding whether to commit.",
        "ROLLBACK TRANSACTION;",
    ])
    return "\n".join(lines)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--database", required=True)
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inventory", action="store_true", help="print the read-only table inventory")
    mode.add_argument("--login", help="print rollback-only grants for this dedicated login")
    args = cli.parse_args()
    print(render_inventory(args.database) if args.inventory else render(args.database, args.login))


if __name__ == "__main__":
    main()
