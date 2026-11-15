"""Emit reviewed PostgreSQL grants for the existing P11 application policy."""

import re

from app.institutional import operations_policy
from app.institutional.spanish import RIGHTS
from app.parity_channels.policy import COLUMNS


def grants(role, database):
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,47}", role) or database not in {"rinovaplus", "rinovaplus_rehearsal"}:
        raise ValueError("postgres_role_target_invalid")
    tables = operations_policy.layout()["tables"]
    rights = operations_policy.rights(RIGHTS)
    columns = operations_policy.columns(COLUMNS)
    yield f'GRANT CONNECT ON DATABASE "{database}" TO "{role}";'
    yield f'GRANT USAGE ON SCHEMA rinovaplus_crm,rinova_migration TO "{role}";'
    yield f'GRANT SELECT(archive_sha256) ON rinova_migration.source_snapshot TO "{role}";'
    for logical, physical in sorted(tables.items()):
        table = 'rinovaplus_crm."' + physical.split(".", 1)[1].lower() + '"'
        allowed = rights.get(logical, ())
        if allowed:
            yield f'GRANT {", ".join(allowed)} ON {table} TO "{role}";'
        if "SELECT" not in allowed and logical in columns:
            fields = ", ".join('"' + name.lower() + '"' for name in columns[logical])
            yield f'GRANT SELECT({fields}) ON {table} TO "{role}";'
    yield f'GRANT USAGE ON ALL SEQUENCES IN SCHEMA rinovaplus_crm TO "{role}";'
    yield f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA rinovaplus_crm TO "{role}";'


def main():
    catalog = operations_policy.layout()["tables"]
    print("\\set ON_ERROR_STOP on\nBEGIN;")
    print(
        "DO $$ BEGIN IF current_database() <> 'rinovaplus' OR "
        "current_setting('server_version_num')::integer < 160000 OR "
        "(SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname='rinovaplus_crm')"
        f" <> {len(catalog)} THEN RAISE EXCEPTION 'Unexpected RinovaPlus target'; END IF; END $$;"
    )
    print("CREATE ROLE rinovaplus_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;")
    print(*grants("rinovaplus_app", "rinovaplus"), sep="\n")
    print("COMMIT;")


if __name__ == "__main__":
    main()
