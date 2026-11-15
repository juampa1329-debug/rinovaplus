"""Capture a complete CRM-only snapshot and prepare an atomic, separate PostgreSQL copy."""

import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from app.institutional import operations_policy
from app.institutional.deployment import open_connection, transport_from_env
from tools.postgres_crm_schema import build
from tools.stage_postgres_crm import FORMAT, ArchiveError, validate, write_staging_sql


ROOT = Path(__file__).resolve().parents[1]
SQL_SOURCE = "DBSIIE_2025A"
DESTINATIONS = {"rinovaplus", "rinovaplus_rehearsal"}
METADATA = """SELECT c.name, TYPE_NAME(c.user_type_id), c.column_id, c.max_length,
       c.precision, c.scale, c.is_nullable, c.is_identity, c.is_computed, c.collation_name
       FROM sys.columns c JOIN sys.tables t ON t.object_id=c.object_id
       JOIN sys.schemas s ON s.schema_id=t.schema_id
       WHERE s.name=? AND t.name=? ORDER BY c.column_id"""
METADATA_FIELDS = (
    "name", "type_name", "ordinal", "max_length", "precision", "scale",
    "is_nullable", "is_identity", "is_computed", "collation_name",
)


@contextmanager
def checked_archive(path, expected_digest):
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != expected_digest:
            raise ArchiveError("archive_checksum_mismatch")
        source.seek(0)
        with ZipFile(source) as archive:
            manifest, schema = validate(archive)
            tables = {t["schema"] + "." + t["name"] for t in schema["tables"]}
            if tables != set(operations_policy.layout()["tables"].values()):
                raise ArchiveError("crm_scope_mismatch")
            yield archive, manifest, schema


def sql_identifier(name):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name):
        raise ArchiveError("unsupported_source_identifier")
    return f"[{name}]"


def encode(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"hex": bytes(value).hex()}
    if isinstance(value, Decimal):
        return str(value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ArchiveError("unexpected_source_value_type")


def capture(connection, schema, archive):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT DB_NAME(), CONVERT(int,SERVERPROPERTY('ProductMajorVersion')),"
        " compatibility_level FROM sys.databases WHERE database_id=DB_ID()"
    )
    if tuple(cursor.fetchone()) != (SQL_SOURCE, 15, 150):
        raise ArchiveError("source_identity_mismatch")
    cursor.execute(
        "SET LOCK_TIMEOUT 1000; SET DEADLOCK_PRIORITY LOW;"
        " SET TRANSACTION ISOLATION LEVEL SERIALIZABLE; BEGIN TRANSACTION;"
    )
    captured = datetime.now(timezone.utc).isoformat()
    manifest = {"format": FORMAT, "database": SQL_SOURCE, "captured_at": captured, "tables": {}}
    try:
        for i, table in enumerate(sorted(schema["tables"], key=lambda t: (t["schema"], t["name"]))):
            namespace, name = table["schema"], table["name"]
            key = f"{namespace}.{name}"
            columns = sorted(
                (c for c in schema["columns"] if (c["schema"], c["table"]) == (namespace, name)),
                key=lambda c: c["ordinal"],
            )
            expected = [tuple(c[field] for field in METADATA_FIELDS) for c in columns]
            if not expected or [tuple(row) for row in cursor.execute(METADATA, namespace, name)] != expected:
                raise ArchiveError("source_columns_drift:" + key)
            primary = next((index for index in schema["indexes"] if
                            (index["schema"], index["table"]) == (namespace, name) and index["is_primary_key"]), None)
            if not primary:
                raise ArchiveError("primary_key_required:" + key)
            order = ", ".join(sql_identifier(item["name"]) for item in
                              sorted(primary["columns"], key=lambda c: c["key_ordinal"]) if item["key_ordinal"])
            fields = []
            for column in columns:
                quoted = sql_identifier(column["name"])
                # Keep SQL Server's seventh fractional digit in the archive.
                if column["type_name"] in {"date", "datetime2"}:
                    quoted = f"CONVERT(varchar(33),{quoted},126)"
                fields.append(quoted)
            table_name = f"{sql_identifier(namespace)}.{sql_identifier(name)}"
            cursor.execute("SELECT " + ", ".join(fields) + f" FROM {table_name} ORDER BY {order}")
            path, digest, count = f"data/{i:03d}.jsonl", hashlib.sha256(), 0
            with archive.open(path, "w") as entries:
                for row in cursor:
                    line = (json.dumps([encode(v) for v in row], ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                    entries.write(line)
                    digest.update(line)
                    count += 1
            manifest["tables"][key] = {
                "status": "exported", "path": path, "rows": count, "sha256": digest.hexdigest(),
            }
        archive.writestr("schema.json", json.dumps(schema))
        archive.writestr("manifest.json", json.dumps(manifest))
    finally:
        cursor.execute("IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION")
    return manifest


def emit_candidate(archive, manifest, schema, digest, database, out):
    if database not in DESTINATIONS:
        raise ArchiveError("unapproved_destination")
    if manifest.get("database") != SQL_SOURCE or not manifest.get("captured_at") or any(
        t["status"] != "exported" for t in manifest["tables"].values()
    ):
        raise ArchiveError("complete_fresh_snapshot_required")
    routines = (ROOT / "migrations/postgresql/001_copy_queries_and_queues.sql").read_text(encoding="utf-8")
    header, _, body = routines.partition("\n")
    if header != "BEGIN;" or not body.rstrip().endswith("COMMIT;"):
        raise ArchiveError("unexpected_queue_migration_batch")
    body = body.rstrip().removesuffix("COMMIT;")
    schema_sql = build(schema, digest, transaction=False)
    out.write(
        "\\set ON_ERROR_STOP on\nBEGIN;\n"
        f"DO $$ BEGIN IF current_database() <> '{database}' OR "
        "to_regnamespace('rinovaplus_crm') IS NOT NULL OR to_regnamespace('rinova_migration') IS NOT NULL "
        "THEN RAISE EXCEPTION 'Use the named empty CRM candidate database'; END IF; END $$;\n"
    )
    write_staging_sql(archive, manifest, schema, digest, out, transaction=False)
    out.write(schema_sql)
    out.write(body)
    out.write("\nCOMMIT;\n")


def main():
    import pyodbc

    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="action", required=True)
    export = sub.add_parser("capture")
    export.add_argument("--baseline", type=Path, required=True)
    export.add_argument("--baseline-sha256", required=True)
    export.add_argument("--output", type=Path, required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--archive", type=Path, required=True)
    prepare.add_argument("--sha256", required=True)
    prepare.add_argument("--database", choices=sorted(DESTINATIONS), required=True)
    args = cli.parse_args()
    try:
        if args.action == "prepare":
            if sys.stdout.isatty():
                cli.error("Pipe SQL to the private candidate database")
            with checked_archive(args.archive, args.sha256) as (archive, manifest, schema):
                emit_candidate(archive, manifest, schema, args.sha256, args.database, sys.stdout)
            return 0
        config = transport_from_env(os.environ)
        if config is None or config.database != SQL_SOURCE:
            raise ArchiveError("source_environment_mismatch")
        with checked_archive(args.baseline, args.baseline_sha256) as (_, _, schema):
            with closing(open_connection(config, probe=True)) as conn:
                conn.timeout = 20
                fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    with os.fdopen(fd, "wb") as target, ZipFile(target, "w", ZIP_DEFLATED) as archive:
                        manifest = capture(conn, schema, archive)
                except Exception:
                    args.output.unlink()
                    raise
        with args.output.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        print(json.dumps({
            "archive_sha256": digest, "tables": len(manifest["tables"]),
            "rows": sum(t["rows"] for t in manifest["tables"].values()),
        }))
        return 0
    except (ArchiveError, BadZipFile, pyodbc.Error, ValueError, OSError, KeyError) as error:
        reason = str(error) if isinstance(error, ArchiveError) else type(error).__name__
        print("crm_cutover_rejected " + reason, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
