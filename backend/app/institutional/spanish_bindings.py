"""Closed Spanish table map for trusted repository SQL; parameters stay opaque."""

import json
import re
from pathlib import Path
from uuid import UUID

VERSION = "cbn-institutional-spanish-p2-v1"
TARGET = re.compile(r"CBN_P2ES_(REF|TRIAL|FAULT|RECOVERY)_20261026_([0-9a-f]{8})\Z")
PACKAGE = (
    Path(__file__).resolve().parents[2] / "migrations/cbn_institutional_spanish_v1"
)
LOGICAL = re.compile(
    r"(?<![\w.])\[?(crm(?:_[a-z0-9]+)?|crm_meta)\]?\s*\.\s*\[?([A-Za-z_][A-Za-z0-9_]*)\]?(?![\w.])"
)
TOKENS = re.compile(r"N?'(?:''|[^'])*'|--[^\n]*|/\*[\s\S]*?\*/|" + LOGICAL.pattern)
OBJECT_LITERAL = re.compile(
    r"(\bOBJECT_ID\s*\(\s*N?')((?:crm(?:_[a-z0-9]+)?|crm_meta)\.[A-Za-z_][A-Za-z0-9_]*)(?=')",
    re.IGNORECASE,
)


def principal(database):
    match = TARGET.fullmatch(database)
    if not match:
        raise ValueError("P2ES_isolated_target_required")
    return "cbn_institutional_es_" + match[2]


def canonical_context(rows):
    return [[int(row[0]), str(UUID(str(row[1]))), row[2]] for row in rows]


def layout():
    value = json.loads((PACKAGE / "table_map.json").read_text(encoding="utf-8"))
    mapping = value["tables"]
    base = json.loads(
        (PACKAGE.parent / "cbn_spanish_schema_v2/table_map.json").read_text(
            encoding="utf-8"
        )
    )
    if {key: mapping.get(key) for key in base["CRM_map"]} != base["CRM_map"] or value[
        "academic_tables"
    ] != base["academic_tables"]:
        raise ValueError("P2ES_parent_semantic_map_changed")
    if len(mapping) != 108 or len(set(mapping.values())) != 108:
        raise ValueError("P2ES_closed_map_required")
    if (
        mapping.get("crm.Contact") != "dbo.CRMContacto"
        or mapping.get("crm_meta.MigrationJournal") != "crm_meta.MigrationJournal"
    ):
        raise ValueError("P2ES_core_mapping_changed")
    if len(value["academic_tables"]) != 30 or set(mapping.values()) & set(
        value["academic_tables"]
    ):
        raise ValueError("P2ES_academic_partition")
    return value


def translate(sql, mapping):
    if not isinstance(sql, str):
        raise ValueError("P2ES_trusted_SQL_string_required")

    def object_literal(match):
        if match[2] not in mapping:
            raise ValueError("P2ES_unknown_object_probe")
        return match[1] + mapping[match[2]]

    def replace(match):
        if match[1] is None:
            return match[0]
        key = match[1] + "." + match[2]
        if key not in mapping:
            raise ValueError("P2ES_unknown_logical_identifier")
        return ".".join("[" + part + "]" for part in mapping[key].split("."))

    return TOKENS.sub(replace, OBJECT_LITERAL.sub(object_literal, sql))


class Cursor:
    def __init__(self, cursor, mapping=None):
        self.physical = cursor
        self.mapping = mapping if mapping is not None else layout()["tables"]

    def execute(self, sql, *parameters):
        self.physical.execute(translate(sql, self.mapping), *parameters)
        return self

    def executemany(self, sql, parameters):
        self.physical.executemany(translate(sql, self.mapping), parameters)
        return self

    def __iter__(self):
        return iter(self.physical)

    def __getattr__(self, name):
        return getattr(self.physical, name)
