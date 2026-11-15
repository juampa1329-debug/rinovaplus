"""Validate a private SQL Server archive and emit a PostgreSQL staging transaction."""

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from zipfile import BadZipFile, ZipFile


FORMAT = "rinovaplus-sqlserver-export-v1"
DATA_ENTRY = re.compile(r"data/[0-9]{3}\.jsonl\Z")


class ArchiveError(ValueError):
    pass


def validate(archive):
    entries = archive.namelist()
    if len(entries) != len(set(entries)):
        raise ArchiveError("duplicate_entries")
    manifest = json.loads(archive.read("manifest.json"))
    schema = json.loads(archive.read("schema.json"))
    if manifest["format"] != FORMAT or not manifest["tables"]:
        raise ArchiveError("unknown_archive_format")
    tables = {f"{t['schema']}.{t['name']}" for t in schema["tables"]}
    if tables != set(manifest["tables"]):
        raise ArchiveError("catalog_mismatch")
    widths = dict.fromkeys(tables, 0)
    for column in schema["columns"]:
        widths[f"{column['schema']}.{column['table']}"] += 1
    if 0 in widths.values():
        raise ArchiveError("catalog_columns_missing")

    used = {"manifest.json", "schema.json"}
    for name, table in manifest["tables"].items():
        if table["status"] == "restricted":
            if "path" in table:
                raise ArchiveError("restricted_table_has_data")
            continue
        if table["status"] != "exported":
            raise ArchiveError("unknown_table_status")
        path = table["path"]
        if not DATA_ENTRY.fullmatch(path) or path in used:
            raise ArchiveError("invalid_data_entry")
        used.add(path)
        digest = hashlib.sha256()
        count = 0
        with archive.open(path) as rows:
            for line in rows:
                values = json.loads(line)
                if not isinstance(values, list) or len(values) != widths[name]:
                    raise ArchiveError("wrong_row_width")
                digest.update(line)
                count += 1
        if count != table["rows"] or digest.hexdigest() != table["sha256"]:
            raise ArchiveError("data_checksum_mismatch")
    if used != set(entries):
        raise ArchiveError("unexpected_archive_entries")
    return manifest, schema


def write_staging_sql(archive, manifest, schema, sha256, out):
    out.write("""BEGIN;
DO $$ BEGIN
  IF current_database() NOT IN ('rinovaplus', 'rinovaplus_rehearsal')
     OR current_setting('server_version_num')::integer < 160000 THEN
    RAISE EXCEPTION 'Unexpected PostgreSQL staging target';
  END IF;
END $$;
CREATE SCHEMA rinova_migration;
REVOKE ALL ON SCHEMA rinova_migration FROM PUBLIC;
CREATE TABLE rinova_migration.source_snapshot (
  archive_sha256 text PRIMARY KEY, manifest json NOT NULL, source_schema json NOT NULL
);
CREATE TABLE rinova_migration.source_row (
  source_table text NOT NULL, row_number bigint NOT NULL, source_values json NOT NULL,
  PRIMARY KEY (source_table, row_number)
);
COPY rinova_migration.source_snapshot FROM STDIN WITH (FORMAT csv);
""")
    writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow((sha256, json.dumps(manifest), json.dumps(schema)))
    out.write("\\.\nCOPY rinova_migration.source_row FROM STDIN WITH (FORMAT csv);\n")
    for name, table in manifest["tables"].items():
        if table["status"] == "exported":
            with archive.open(table["path"]) as rows:
                for index, row in enumerate(rows, start=1):
                    writer.writerow((name, index, row.decode("utf-8").rstrip("\n")))
    out.write("\\.\nCOMMIT;\n")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("archive", type=Path)
    cli.add_argument("--sha256", required=True)
    args = cli.parse_args()
    if sys.stdout.isatty():
        cli.error("Pipe this output directly to a private PostgreSQL loader")
    try:
        with args.archive.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
            if digest != args.sha256.lower():
                raise ArchiveError("archive_checksum_mismatch")
            source.seek(0)
            with ZipFile(source) as archive:
                manifest, schema = validate(archive)
                write_staging_sql(archive, manifest, schema, digest, sys.stdout)
    except (ArchiveError, BadZipFile, OSError, KeyError, TypeError, ValueError) as error:
        print("crm_archive_rejected", type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
