"""Independent full SQL2019 catalog reader for the Spanish schema qualification."""

import json
from collections import defaultdict

from app.parity_channels.catalog import metadata
from tools.foundation_snapshot import records, sha

JOURNAL = ("crm_meta", "MigrationJournal")
ACTIONS = {0: "NO_ACTION", 1: "CASCADE", 2: "SET_NULL", 3: "SET_DEFAULT"}


def canonical(value):
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return sorted(
            (canonical(v) for v in value),
            key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False),
        )
    return value


def model(snapshot):
    keys = (
        "tables",
        "columns",
        "indexes",
        "checks",
        "foreign_keys",
        "table_options",
        "ansi_padding",
    )
    result = {k: snapshot[k] for k in keys}
    result["tables"] = [
        {"schema": t["schema"], "name": t["name"]} for t in result["tables"]
    ]
    return canonical(result)


def snapshot(cursor, *, omit_journal=False, raw_catalog=None, only_tables=None):
    # Trusted internal reuse is confined to the same guarded transaction.
    raw = metadata(cursor) if raw_catalog is None else raw_catalog
    selected = {
        (r["schema_name"], r["name"])
        for r in raw["catalog"]
        if r["type"].strip() == "U"
    }
    if only_tables is not None:
        selected = {(schema, name) for schema, name in selected if f"{schema}.{name}" in only_tables}
    if omit_journal:
        selected.discard(JOURNAL)
    # No complement of a schema is silently trusted. Any extra table remains visible.
    unsupported = [
        r
        for r in raw["catalog"]
        if r["type"].strip() not in {"U", "PK", "UQ", "C", "F", "D"}
    ]
    if only_tables is None and unsupported:
        raise ValueError("ES_unexpected_routine_trigger_or_object")
    features = records(
        cursor,
        """SELECT s.name AS [schema],t.name AS [table],c.name,
      SCHEMA_NAME(ty.schema_id) AS type_schema,c.is_rowguidcol,c.is_sparse,
      c.is_column_set,c.generated_always_type,c.encryption_type,c.is_ansi_padded
      FROM sys.columns c JOIN sys.tables t ON t.object_id=c.object_id
      JOIN sys.schemas s ON s.schema_id=t.schema_id JOIN sys.types ty ON ty.user_type_id=c.user_type_id
      WHERE t.is_ms_shipped=0 ORDER BY s.name,t.name,c.column_id""",
    )
    featuremap = {(r["schema"], r["table"], r["name"]): r for r in features}
    columns = []
    for c in raw["columns"]:
        if (c["schema_name"], c["table_name"]) not in selected:
            continue
        result = {"schema": c["schema_name"], "table": c["table_name"]}
        for field in (
            "name",
            "type_name",
            "max_length",
            "precision",
            "scale",
            "is_nullable",
            "is_identity",
            "is_computed",
            "collation_name",
            "identity_seed",
            "identity_increment",
            "computed_definition",
            "default_name",
            "default_definition",
        ):
            result[field] = c[field]
        result["ordinal"] = c["ordinal"]
        f = featuremap[(c["schema_name"], c["table_name"], c["name"])]
        for field in (
            "type_schema",
            "is_rowguidcol",
            "is_sparse",
            "is_column_set",
            "generated_always_type",
            "encryption_type",
        ):
            result[field] = f[field]
        columns.append(result)
    storage = records(
        cursor,
        """SELECT s.name AS [schema],t.name AS [table],i.name,
      ds.name AS data_space,ds.type_desc AS data_space_type,p.partition_number,p.data_compression_desc,i.optimize_for_sequential_key,CONVERT(bit,ISNULL(st.no_recompute,0)) AS statistics_norecompute
      FROM sys.indexes i JOIN sys.tables t ON t.object_id=i.object_id
      JOIN sys.schemas s ON s.schema_id=t.schema_id JOIN sys.data_spaces ds ON ds.data_space_id=i.data_space_id
      LEFT JOIN sys.stats st ON st.object_id=i.object_id AND st.stats_id=i.index_id
      JOIN sys.partitions p ON p.object_id=i.object_id AND p.index_id=i.index_id
      WHERE t.is_ms_shipped=0 AND i.name IS NOT NULL ORDER BY s.name,t.name,i.name,p.partition_number""",
    )
    groups = defaultdict(list)
    storages = defaultdict(list)
    for r in raw["indexes"]:
        if (r["schema_name"], r["table_name"]) in selected:
            groups[(r["schema_name"], r["table_name"], r["name"])].append(r)
    for r in storage:
        storages[(r["schema"], r["table"], r["name"])].append(r)
    indexes = []
    for key, values in groups.items():
        if key[2] is None:
            raise ValueError("ES_unexpected_heap")
        first = values[0]
        result = {"schema": key[0], "table": key[1], "name": key[2]}
        for field in (
            "type_desc",
            "is_unique",
            "is_primary_key",
            "is_unique_constraint",
            "is_disabled",
            "has_filter",
            "filter_definition",
            "fill_factor",
            "is_padded",
            "ignore_dup_key",
            "allow_row_locks",
            "allow_page_locks",
        ):
            result[field] = first[field]
        store = storages[key]
        result.update(
            data_space=store[0]["data_space"],
            data_space_type=store[0]["data_space_type"],
        )
        result["columns"] = [
            {
                "name": r["column_name"],
                "key_ordinal": r["key_ordinal"],
                "index_column_id": r["index_column_id"],
                "is_descending_key": r["is_descending_key"],
                "is_included_column": r["is_included_column"],
            }
            for r in values
        ]
        result["optimize_for_sequential_key"] = store[0]["optimize_for_sequential_key"]
        result["statistics_norecompute"] = store[0]["statistics_norecompute"]
        result["compression"] = [
            {
                "partition_number": r["partition_number"],
                "data_compression_desc": r["data_compression_desc"],
            }
            for r in store
        ]
        indexes.append(result)
    checks = [
        {
            "schema": r["schema_name"],
            "table": r["table_name"],
            **{
                k: r[k]
                for k in (
                    "name",
                    "definition",
                    "is_disabled",
                    "is_not_trusted",
                    "is_not_for_replication",
                )
            },
        }
        for r in raw["checks"]
        if (r["schema_name"], r["table_name"]) in selected
    ]
    groups = defaultdict(list)
    for r in raw["foreign_keys"]:
        if (r["schema_name"], r["table_name"]) in selected:
            groups[(r["schema_name"], r["table_name"], r["name"])].append(r)
    foreign_keys = []
    for key, values in groups.items():
        r = values[0]
        foreign_keys.append(
            {
                "schema": key[0],
                "table": key[1],
                "name": key[2],
                "referenced_schema": r["target_schema"],
                "referenced_table": r["target_table"],
                "delete_action": ACTIONS[r["delete_referential_action"]],
                "update_action": ACTIONS[r["update_referential_action"]],
                **{
                    k: r[k]
                    for k in ("is_disabled", "is_not_trusted", "is_not_for_replication")
                },
                "columns": [
                    {
                        "column": v["column_name"],
                        "referenced_column": v["target_column"],
                        "ordinal": v["ordinal"],
                    }
                    for v in values
                ],
            }
        )
    options = records(
        cursor,
        """SELECT s.name AS [schema],t.name AS [table],t.lock_escalation_desc,
      t.large_value_types_out_of_row,t.text_in_row_limit,t.is_memory_optimized,t.temporal_type,t.is_filetable
      FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id WHERE t.is_ms_shipped=0""",
    )
    types = {(c["schema"], c["table"], c["name"]): c["type_name"] for c in columns}
    ansi = [
        {
            "schema": r["schema"],
            "table": r["table"],
            "column": r["name"],
            "type_name": types[(r["schema"], r["table"], r["name"])],
            "is_ansi_padded": r["is_ansi_padded"],
        }
        for r in features
        if (r["schema"], r["table"]) in selected
        and types[(r["schema"], r["table"], r["name"])]
        in {"char", "varchar", "nchar", "nvarchar", "binary", "varbinary"}
    ]
    return model(
        {
            "tables": [{"schema": s, "name": t} for s, t in selected],
            "columns": columns,
            "indexes": indexes,
            "checks": checks,
            "foreign_keys": foreign_keys,
            "table_options": [
                r for r in options if (r["schema"], r["table"]) in selected
            ],
            "ansi_padding": ansi,
        }
    )


def compare(actual, expected):
    actual, expected = model(actual), model(expected)
    differing = [k for k in expected if actual[k] != expected[k]]
    return {
        "passed": not differing,
        "actual_sha256": sha(actual),
        "expected_sha256": sha(expected),
        "differing_sections": differing,
    }
