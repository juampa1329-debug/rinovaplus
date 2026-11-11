"""Explicit read-only before/after evidence for the restored UI acceptance."""

import argparse
import json
from pathlib import Path

from app import foundation
from app.foundation_app import create_foundation_app
from app.foundation_profile import load_settings
from tools.foundation_snapshot import metadata, sha
from tools.rehearse_foundation import SOURCE, admin, capture, load, save
from tools.rehearse_repositories import administrative_signature


def require(condition):
    if not condition:
        raise RuntimeError("UI rehearsal preservation mismatch")


def signatures(context, runtime_directory):
    with admin(SOURCE, context, readonly=True) as connection:
        source = capture(connection)
        require(
            connection.cursor()
            .execute(
                "SELECT COUNT(*) FROM sys.schemas "
                "WHERE name IN ('crm','crm_config','crm_meta')"
            )
            .fetchval()
            == 0
        )
    with admin(foundation.DATABASE, context, readonly=True) as connection:
        academic = administrative_signature(connection)
        _, expected = foundation.assets()
        journal = foundation.journal_signature(connection.cursor(), expected)
        require(
            sha(foundation.project_managed(metadata(connection.cursor(), managed=True)))
            == sha(expected)
        )
    workspace = create_foundation_app(
        load_settings(runtime_directory)
    ).state.sql_workspace
    with workspace.transaction() as cursor:
        crm = {
            table: cursor.execute("SELECT COUNT(*) FROM " + table).fetchval()
            for table in foundation.RIGHTS
        }
    return {
        "source": source,
        "academic": academic,
        "journal": journal,
        "crm_counts": crm,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("before", "after"))
    parser.add_argument("--private-directory", type=Path, required=True)
    parser.add_argument("--runtime-directory", type=Path, required=True)
    parser.add_argument("--c4-baseline", type=Path)
    args = parser.parse_args()
    try:
        require(args.private_directory.is_absolute())
        path = args.private_directory / "before.json"
        if args.action == "before":
            require(not path.exists() and args.c4_baseline is not None)
            c4 = load(args.c4_baseline)
            current = signatures(c4["context"], args.runtime_directory)
            require(
                current["source"] == c4["source"]
                and current["academic"] == c4["restored"]
                and current["journal"] == c4["journal_sha256"]
            )
            save(path, {"context": c4["context"], "signatures": current})
        else:
            before = load(path)
            current = signatures(before["context"], args.runtime_directory)
            require(
                all(
                    current[key] == before["signatures"][key]
                    for key in ("source", "academic", "journal")
                )
            )
        result = {
            "stage": "SQL-C5",
            "action": args.action,
            "database": foundation.DATABASE,
            "read_only_evidence": True,
            "source_unchanged": True,
            "academic_tables": 50,
            "academic_rows": current["source"]["data"]["rows"],
            "academic_metadata_and_data_preserved": True,
            "journal_unchanged": True,
            "frozen_managed_shape_preserved": True,
            "crm_counts": current["crm_counts"],
        }
        save(args.private_directory / (args.action + "-result.json"), result)
        print(json.dumps(result))
    except Exception as error:
        print(json.dumps({"status": "blocked", "error": type(error).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
