"""Compatibility for legacy statements used by the PostgreSQL rehearsal flows."""

import re
from uuid import UUID


LITERALS = re.compile(r"(N?'(?:''|[^'])*')")
TABLE = re.compile(r"(?<![\w.])\b(crm(?:_[a-z0-9]+)?)\.([A-Za-z_]\w*)\b")
BOUND_TOP = re.compile(r"^SELECT\s+TOP\s*\(\?\)", re.I)
TOP = re.compile(r"^SELECT\s+TOP\s*\((\d+|%s)\)\s+", re.I)
BOUNDED_WRITE = re.compile(r"^(DELETE|UPDATE)\s+TOP\s*\((\d+)\)\s+(\S+)\s+(.+)$", re.I)
SAVEPOINT = re.compile(r"(SAVE|ROLLBACK) TRANSACTION (event_projection|p8_next_part|p8_prepare_step|whatsapp_gemini|comment_auto)\Z")
JSON_SCALAR = re.compile(r"\bJSON_VALUE\(\s*([\w.]+)\s*,\s*N?'\$((?:\.[A-Za-z0-9_]+)+)'\s*\)", re.I)
JSON_CAST = re.compile(
    r"\bTRY_CONVERT\(\s*(uniqueidentifier|bigint|int)\s*,\s*(" + JSON_SCALAR.pattern + r")\s*\)", re.I
)
TSQL_UPDATE = re.compile(r"^UPDATE\s+(\w+)\s+SET\s+(.+?)\s+FROM\s+(\w+\.\w+)\s+(\w+)\s+(.*)$", re.I | re.S)
UPDATE_JOIN = re.compile(r"^JOIN\s+(\w+\.\w+)\s+(\w+)\s+ON\s+(.+?)\s+WHERE\s+(.+)$", re.I | re.S)
NOW = "(statement_timestamp() AT TIME ZONE 'UTC')"
UNIT = r"(millisecond|second|minute|hour|day)"
NESTED_TOP = re.compile(r"\(\s*SELECT\s+(TOP\s*\((\d+)\)\s*)", re.I)
OUTER_APPLY = re.compile(r"\bOUTER\s+APPLY\s*(?=\()", re.I)
DATE_COLUMN = re.compile(
    rf"DATEADD\({UNIT}\s*,\s*(-?\d+|\?|[\w.]+)\s*,\s*([\w.]+|CONVERT\(datetime2,\s*\?\))\)", re.I,
)


def rewrite_subqueries(statement):
    # Blanking string literals keeps parentheses and keyword offsets aligned.
    source = LITERALS.sub(lambda match: " " * len(match[0]), statement)
    edits = []
    boundaries = {}
    stack = []
    for token in re.finditer(r"[()]", source):
        if token[0] == "(":
            stack.append(token.start())
        elif stack:
            boundaries[stack.pop()] = token.start()
    for match in NESTED_TOP.finditer(source):
        end = boundaries.get(match.start())
        if end is None:
            raise ValueError("unported_subquery_limit")
        edits.extend(((match.start(1), match.end(1), ""), (end, end, f" LIMIT {match[2]}")))
    for match in OUTER_APPLY.finditer(source):
        end = boundaries.get(match.end())
        alias = re.match(r"\s+(?:AS\s+)?[A-Za-z_]\w*", source[end + 1:], re.I) if end is not None else None
        if alias is None:
            raise ValueError("unported_outer_apply")
        after_alias = end + 1 + alias.end()
        edits.extend(((match.start(), match.end(), "LEFT JOIN LATERAL "), (after_alias, after_alias, " ON TRUE")))
    for start, end, replacement in sorted(edits, reverse=True):
        statement = statement[:start] + replacement + statement[end:]
    return statement


def json_scalar(match):
    source, path = match.groups()
    pg_path = "{" + ",".join(path[1:].split(".")) + "}"
    node = f"({source}::jsonb #> '{pg_path}')"
    value = f"({source}::jsonb #>> '{pg_path}')"
    return f"(CASE WHEN jsonb_typeof({node}) IN ('string','number','boolean') AND length({value})<=4000 THEN {value} END)"


def json_cast(match):
    type_name = {"uniqueidentifier": "uuid", "bigint": "bigint", "int": "integer"}[match[1].lower()]
    value = json_scalar(JSON_SCALAR.fullmatch(match[2]))
    return f"(CASE WHEN pg_input_is_valid({value},'{type_name}') THEN {value}::{type_name} END)"


def evidence_array(match):
    document, alias = match.groups()
    node = f"{document}::jsonb->'evidence_message_ids'"
    return (
        f"jsonb_array_elements_text(CASE WHEN jsonb_typeof({node})='array' "
        f"THEN {node} ELSE '[]'::jsonb END) AS {alias or 'evidence_items'}(value)"
    )


def date_column(match):
    unit, delta, timestamp = match.groups()
    if timestamp.upper().startswith("CONVERT"):
        timestamp = "CAST(? AS timestamp)"
    return f"(({delta}) * INTERVAL '1 {unit.lower()}' + {timestamp})"


def joined_update(statement):
    match = TSQL_UPDATE.fullmatch(statement)
    if not match:
        return statement
    alias, assignment, table, target, tail = match.groups()
    if alias.lower() != target.lower():
        raise ValueError("unported_update_target")
    assignment = re.sub(rf"(?:^|,\s*)({alias}\.)(?=\w+\s*=)", lambda m: m[0][:-len(m[1])], assignment, flags=re.I)
    if tail.upper().startswith("WHERE "):
        return f"UPDATE {table} AS {alias} SET {assignment} {tail}"
    join = UPDATE_JOIN.fullmatch(tail)
    if not join:
        raise ValueError("unported_update_join")
    source, source_alias, relationship, condition = join.groups()
    return f"UPDATE {table} AS {alias} SET {assignment} FROM {source} AS {source_alias} WHERE ({relationship}) AND ({condition})"


def postgres_sql(statement, table_map):
    statement = statement.strip()
    if statement == "SELECT OBJECT_ID(N'crm_agents.Execution')":
        execution = table_map.get("crm_agents.Execution")
        if execution is None:
            return "SELECT NULL"
        table = execution.split(".", 1)[1].lower()
        return f"SELECT to_regclass('rinovaplus_crm.{table}')"
    savepoint = SAVEPOINT.fullmatch(statement)
    if savepoint:
        command = "SAVEPOINT" if savepoint[1] == "SAVE" else "ROLLBACK TO SAVEPOINT"
        return f"{command} {savepoint[2]}"
    if not re.match(r"^(?:SELECT|INSERT|UPDATE|DELETE|WITH base AS)\b", statement, re.I):
        raise ValueError("unported_statement")
    # SQL Server accepts Unicode-prefixed strings, the fixture uses UTF-8.
    statement = statement.replace(
        "DATEDIFF_BIG(second,CONVERT(datetime2,'19700101'),SYSUTCDATETIME())",
        "floor(extract(epoch FROM SYSUTCDATETIME()))::bigint",
    )
    statement = statement.replace(
        "DATEFROMPARTS(YEAR(SYSUTCDATETIME()),MONTH(SYSUTCDATETIME()),1)",
        "date_trunc('month',SYSUTCDATETIME())",
    )
    statement = rewrite_subqueries(statement)
    statement = re.sub(
        r"\bSTRING_SPLIT\(([\w.]+)\s*,\s*','\)", r"string_to_table(\1,',') AS split_values(value)", statement, flags=re.I,
    )
    statement = re.sub(
        r"\bOPENJSON\(([\w.]+)\s*,\s*'\$\.evidence_message_ids'\)(?:\s+(e)\b)?",
        evidence_array, statement, flags=re.I,
    )
    statement = DATE_COLUMN.sub(date_column, statement)
    statement = re.sub(
        r"\bCHARINDEX\(\?\s*,\s*(Name|Phone|ISNULL\(Body,''\))\)",
        r'strpos(lower(\1 COLLATE "default"),lower(?))', statement, flags=re.I,
    )
    statement = JSON_SCALAR.sub(json_scalar, JSON_CAST.sub(json_cast, statement))
    fragments = LITERALS.split(statement)
    for index, part in enumerate(fragments):
        if index % 2:
            fragments[index] = part.removeprefix("N").replace("%", "%%")
            continue

        def qualify(match):
            name = table_map.get(match[0])
            if name is None:
                raise ValueError("unmapped_crm_table")
            return "rinovaplus_crm." + name.split(".", 1)[1].lower()

        part = TABLE.sub(qualify, part)
        # Channel settings build SET assignments with SQL Server's quoted column names.
        part = re.sub(
            r"(?<=[ ,])\[([A-Za-z_][A-Za-z_0-9]*)\](?=\s*=)",
            lambda match: '"' + match[1].lower() + '"',
            part,
        )
        part = re.sub(r"\bISNULL\s*\(", "COALESCE(", part, flags=re.I)
        part = re.sub(r"\bCOUNT_BIG\s*\(", "COUNT(", part, flags=re.I)
        part = re.sub(r"\b([\w.]+)\s+LIKE\b", r'(\1 COLLATE "default") ILIKE', part, flags=re.I)
        part = re.sub(r"\bCOLLATE\s+Latin1_General_100_BIN2\b", 'COLLATE "C"', part, flags=re.I)
        part = re.sub(r"\bCROSS\s+APPLY\s*\(", "CROSS JOIN LATERAL (", part, flags=re.I)
        part = re.sub(
            r"\bOPENJSON\((\?|r\.Actions)\)",
            r"jsonb_array_elements_text(CAST(\1 AS jsonb)) AS json_values(value)",
            part,
            flags=re.I,
        )
        part = re.sub(
            r"\bOPENJSON\((u\.ChainJson)\)\s+j\b",
            r"jsonb_array_elements_text(CAST(\1 AS jsonb)) AS j(value)",
            part,
            flags=re.I,
        )
        part = re.sub(r"\bCONVERT\(uniqueidentifier,\s*value\)", "CAST(value AS uuid)", part, flags=re.I)
        part = re.sub(
            r"\bTRY_CONVERT\(int,\s*value\)",
            "CASE WHEN pg_input_is_valid(value,'integer') THEN CAST(value AS integer) END", part, flags=re.I,
        )
        part = re.sub(
            r"\bTRY_CONVERT\(uniqueidentifier,\s*e\.value\)",
            "CASE WHEN pg_input_is_valid(e.value,'uuid') THEN CAST(e.value AS uuid) END", part, flags=re.I,
        )
        part = re.sub(r"\s+WITH\s*\(\s*UPDLOCK\s*,\s*HOLDLOCK\s*\)", "", part, flags=re.I)
        part = re.sub(
            r"DATEADD\(" + UNIT + r"\s*,\s*(-?\d+|\?|[a-zA-Z_]\w*)\s*,\s*SYSUTCDATETIME\(\)\)",
            lambda m: f"({NOW} + ({m[2]}) * INTERVAL '1 {m[1].lower()}')",
            part, flags=re.I,
        )
        part = re.sub(
            r"DATEDIFF\(second,\s*(\w+),\s*SYSUTCDATETIME\(\)\)",
            lambda m: f"(floor(extract(epoch FROM {NOW})) - floor(extract(epoch FROM {m[1]})))",
            part, flags=re.I,
        )
        part = re.sub(r"CONVERT\(date,SYSUTCDATETIME\(\)\)", NOW + "::date", part, flags=re.I)
        part = re.sub(
            r"CONVERT\(n?varchar\(\d+\),\s*([\w.]+)\)",
            r"(\1)::text", part, flags=re.I,
        )
        part = re.sub(r"CONVERT\(bigint,\s*([\w.]+)\)", r"(\1)::bigint", part, flags=re.I)
        part = re.sub(r"CONVERT\(int,\s*(FallbackUsed)\)", r"(\1)::integer", part, flags=re.I)
        part = re.sub(r"\bSYSUTCDATETIME\(\)", NOW, part, flags=re.I)
        if re.search(r"(?:--|/\*|;)|\b(?:DATEADD|OPENJSON|OUTPUT|JSON_VALUE|OUTER APPLY|OBJECT_ID)\b", part, re.I):
            raise ValueError("unported_statement")
        fragments[index] = part.replace("%", "%%").replace("?", "%s")
    statement = "".join(fragments)
    statement = re.sub(r"^INSERT\s+(?!INTO\b)", "INSERT INTO ", statement, flags=re.I)
    match = TOP.match(statement)
    if match:
        statement = "SELECT " + statement[match.end():] + " LIMIT " + match[1]
    match = BOUNDED_WRITE.fullmatch(statement)
    if match:
        command, limit, table, tail = match.groups()
        if command.upper() == "DELETE":
            table, tail = tail.split(" ", 1) if table.upper() == "FROM" else (table, tail)
            where = re.fullmatch(r"WHERE (.+)", tail, re.I)[1]
            statement = f"DELETE FROM {table} WHERE ctid IN (SELECT ctid FROM {table} WHERE {where} LIMIT {int(limit)})"
        else:
            assignment, where = re.split(r"\s+WHERE\s+", tail, maxsplit=1, flags=re.I)
            statement = f"UPDATE {table} {assignment} WHERE ctid IN (SELECT ctid FROM {table} WHERE {where} LIMIT {int(limit)})"
    return joined_update(statement)


class Cursor:
    dialect = "postgresql"

    def __init__(self, cursor, table_map, columns):
        self._cursor = cursor
        self._table_map = table_map
        self._columns = columns
        self._aliases = {}

    def execute(self, statement, *parameters):
        if BOUND_TOP.match(statement.strip()):
            parameters = (*parameters[1:], parameters[0])
        sql = postgres_sql(statement, self._table_map)
        tokens = re.finditer(r"(?<!%)%s", LITERALS.sub(lambda m: " " * len(m[0]), sql))
        values = list(parameters)
        for index, (token, value) in enumerate(zip(tokens, values)):
            if re.search(r"\bILIKE\s+$", sql[:token.start()], re.I) and isinstance(value, str):
                values[index] = re.sub(
                    r"\[\[\]|\[%\]|\[_\]|\\",
                    lambda m: {"[[]": "[", "[%]": r"\%", "[_]": r"\_", "\\": r"\\"}[m[0]],
                    value,
                )
        # Imported SQL Server bit columns use a checked smallint in PostgreSQL.
        return self.native(sql, *(int(value) if isinstance(value, bool) else value for value in values))

    def native(self, sql, *parameters):
        unquoted = "".join(LITERALS.split(sql)[::2])
        self._aliases = {
            alias.lower(): alias for alias in re.findall(r"\bAS\s+([a-zA-Z_]\w*)", unquoted, re.I)
        }
        self._cursor.execute(sql, parameters if parameters else None)
        return self

    @property
    def description(self):
        columns = self._cursor.description
        if columns is None:
            return None
        return [
            (self._aliases.get(col.name, self._columns.get(col.name, col.name)),)
            for col in columns
        ]

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @staticmethod
    def _row(row):
        return tuple(
            str(value) if isinstance(value, UUID)
            else bytes(value) if isinstance(value, memoryview)
            else value for value in row
        )

    def fetchone(self):
        row = self._cursor.fetchone()
        return None if row is None else self._row(row)

    def fetchval(self):
        row = self.fetchone()
        return None if row is None else row[0]

    def fetchall(self):
        return [self._row(row) for row in self._cursor.fetchall()]

    def nextset(self):
        # PostgreSQL workspace calls execute single statements.
        return None

    def __iter__(self):
        return (self._row(row) for row in self._cursor)
