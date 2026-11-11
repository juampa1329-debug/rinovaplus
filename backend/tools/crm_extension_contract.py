"""Independent final 011+012 contract, not learned from the reference database."""

import json
import re

from tools.crm_extension_snapshot import PACKAGE, extension_shape, require


def compact(value):
    parts = re.split(r"('(?:''|[^'])*')", value or "")
    return "".join(
        part if part.startswith("'") else re.sub(r"[\s\[\]()]", "", part).lower()
        for part in parts
    )


def default_value(value):
    if value is None:
        return None
    text = value.strip()
    while text.startswith("(") and text.endswith(")"):
        depth, quoted, outer = 0, False, True
        for i, char in enumerate(text):
            if char == "'":
                quoted = not quoted
            if not quoted:
                depth += (char == "(") - (char == ")")
                if depth == 0 and i != len(text) - 1:
                    outer = False
                    break
        if not outer:
            break
        text = text[1:-1].strip()
    return text if text.startswith("'") else text.lower()


def check_definition(actual, expected):
    value = compact(actual)
    column = expected["column"].lower()
    if expected["kind"] == "json":
        return value == "isjson" + column + "=1"
    allowed = set(expected["values"])
    if value.startswith(column + "in"):
        rest = value[len(column) + 2 :]
        values = re.findall(r"'([^']*)'", rest)
        return (
            set(values) == allowed
            and len(values) == len(allowed)
            and rest == ",".join("'" + v + "'" for v in values)
        )
    terms = value.split("or")
    return len(terms) == len(allowed) and set(terms) == {
        column + "='" + v + "'" for v in allowed
    }


def verify_final_shape(shape, collation):
    spec = json.loads((PACKAGE / "shape-spec.json").read_text(encoding="utf-8"))
    ext = extension_shape(shape)
    columns = {(c["table_name"], c["name"]): c for c in ext["columns"]}
    require(len(columns) == len(ext["columns"]) == 57, "column_count")
    require(
        set(columns) == {(c["table"], c["name"]) for c in spec["columns"]},
        "column_names",
    )
    for wanted in spec["columns"]:
        actual = columns[wanted["table"], wanted["name"]]
        for field in ("type_name", "max_length", "precision", "scale"):
            require(actual[field] == wanted[field], "column_" + field)
        require(actual["ordinal"] == wanted["ordinal"], "column_ordinal")
        require(
            actual["is_nullable"] == wanted["nullable"]
            and actual["is_identity"] == wanted["identity"]
            and actual["is_computed"] == 0
            and actual["computed_definition"] is None,
            "column_flags",
        )
        require(
            actual["collation_name"]
            == (
                collation
                if wanted["collation"] == "<database>"
                else wanted["collation"]
            ),
            "column_collation",
        )
        require(
            actual["default_name"] == wanted["default_name"]
            and default_value(actual["default_definition"])
            == default_value(wanted["default"]),
            "column_default",
        )
        require(
            actual["identity_seed"] == ("1" if wanted["identity"] else None)
            and actual["identity_increment"] == ("1" if wanted["identity"] else None),
            "identity_definition",
        )
    indexes = {}
    for row in ext["indexes"]:
        indexes.setdefault((row["table_name"], row["name"]), []).append(row)
    require(
        set(indexes) == {(i["table"], i["name"]) for i in spec["indexes"]},
        "index_names",
    )
    for wanted in spec["indexes"]:
        rows = sorted(
            indexes[wanted["table"], wanted["name"]], key=lambda r: r["key_ordinal"]
        )
        require(
            [r["column_name"] for r in rows] == wanted["columns"]
            and [r["key_ordinal"] for r in rows] == list(range(1, len(rows) + 1)),
            "index_columns",
        )
        for row in rows:
            require(
                bool(row["is_primary_key"]) == (wanted["kind"] == "PK")
                and bool(row["is_unique_constraint"]) == (wanted["kind"] == "UQ")
                and bool(row["is_unique"]) == wanted["unique"]
                and row["type_desc"]
                == ("CLUSTERED" if wanted["kind"] == "PK" else "NONCLUSTERED"),
                "index_kind",
            )
            require(
                not row["is_disabled"]
                and not row["is_included_column"]
                and not row["is_descending_key"]
                and row["fill_factor"] == 0
                and not row["is_padded"]
                and not row["ignore_dup_key"]
                and row["allow_row_locks"]
                and row["allow_page_locks"],
                "index_flags",
            )
            require(
                bool(row["has_filter"]) == bool(wanted["filter"])
                and compact(row["filter_definition"]) == compact(wanted["filter"]),
                "index_filter",
            )
    checks = {(r["table_name"], r["name"]): r for r in ext["checks"]}
    require(
        set(checks) == {(r["table"], r["name"]) for r in spec["checks"]}
        and len(checks) == len(ext["checks"]),
        "check_names",
    )
    for wanted in spec["checks"]:
        actual = checks[wanted["table"], wanted["name"]]
        require(
            check_definition(actual["definition"], wanted)
            and not actual["is_disabled"]
            and not actual["is_not_trusted"]
            and not actual["is_not_for_replication"],
            "check_definition",
        )
    fks = {r["name"]: r for r in ext["foreign_keys"]}
    require(
        set(fks) == {r["name"] for r in spec["foreign_keys"]}
        and len(fks) == len(ext["foreign_keys"]),
        "fk_names",
    )
    for wanted in spec["foreign_keys"]:
        row = fks[wanted["name"]]
        require(
            row["schema_name"] + "." + row["table_name"] == wanted["source_table"]
            and [row["column_name"]] == wanted["source_columns"]
            and row["target_schema"] + "." + row["target_table"]
            == wanted["target_table"]
            and [row["target_column"]] == wanted["target_columns"]
            and row["ordinal"] == 1
            and row["delete_referential_action"] == 0
            and row["update_referential_action"] == 0
            and not row["is_disabled"]
            and not row["is_not_trusted"]
            and not row["is_not_for_replication"],
            "fk_definition",
        )
    catalog = {(r["name"], r["type"].strip(), r["parent_name"]) for r in ext["catalog"]}
    expected = {(t, "U", None) for t, _ in columns}
    expected |= {
        (i["name"], i["kind"], i["table"])
        for i in spec["indexes"]
        if i["kind"] in {"PK", "UQ"}
    }
    expected |= {(c["name"], "C", c["table"]) for c in spec["checks"]}
    expected |= {
        (c["default_name"], "D", c["table"])
        for c in spec["columns"]
        if c["default_name"]
    }
    expected |= {
        (f["name"], "F", f["source_table"].split(".")[1]) for f in spec["foreign_keys"]
    }
    require(
        catalog == expected and len(catalog) == len(ext["catalog"]),
        "unexpected_catalog_object",
    )
    require(
        ext["schemas"] == [{"name": "crm_channels", "owner": "dbo"}], "schema_owner"
    )
    require(
        not ext["triggers"] and not ext["synonyms"] and not ext["user_types"],
        "executable_extension",
    )
    properties = ext["properties"]
    require(
        {r["name"]: r["value"] for r in properties} == spec["properties"]
        and len(properties) == 2
        and all(
            r["class"] == 3 and r["minor_id"] == 0 and r["object_name"] is None
            for r in properties
        ),
        "contract_properties",
    )
    for row in ext["dependencies"]:
        require(
            row["referenced_server_name"] is None
            and row["referenced_database_name"] is None
            and row["referenced_schema_name"] in {None, "crm", "crm_channels"}
            and not row["is_caller_dependent"]
            and not row["is_ambiguous"],
            "external_dependency",
        )
