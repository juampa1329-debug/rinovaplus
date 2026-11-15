"""Compatibility for legacy statements used by the PostgreSQL rehearsal flows."""

import re
from uuid import UUID


LITERALS = re.compile(r"(N?'(?:''|[^'])*')")
TABLE = re.compile(r"(?<![\w.])\b(crm(?:_[a-z0-9]+)?)\.([A-Za-z_]\w*)\b")
TOP = re.compile(r"^SELECT\s+TOP\s*\((\d+)\)\s+", re.I)
BOUNDED_WRITE = re.compile(r"^(DELETE|UPDATE)\s+TOP\s*\((\d+)\)\s+(\S+)\s+(.+)$", re.I)
NOW = "(statement_timestamp() AT TIME ZONE 'UTC')"
UNIT = r"(second|minute|hour|day)"


def postgres_sql(statement, table_map):
    statement = statement.strip()
    if statement == "SAVE TRANSACTION event_projection":
        return "SAVEPOINT event_projection"
    if statement == "ROLLBACK TRANSACTION event_projection":
        return "ROLLBACK TO SAVEPOINT event_projection"
    if not re.match(r"^(SELECT|INSERT|UPDATE|DELETE)\b", statement, re.I):
        raise ValueError("unported_statement")
    # SQL Server accepts Unicode-prefixed strings, the fixture uses UTF-8.
    statement = statement.replace(
        "DATEDIFF_BIG(second,CONVERT(datetime2,'19700101'),SYSUTCDATETIME())",
        "floor(extract(epoch FROM SYSUTCDATETIME()))::bigint",
    )
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
        part = re.sub(r"\bISNULL\s*\(", "COALESCE(", part, flags=re.I)
        part = re.sub(r"\bCOUNT_BIG\s*\(", "COUNT(", part, flags=re.I)
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
        part = re.sub(r"CONVERT\(varchar\(\d+\),\s*([\w.]+)\)", r"(\1)::text", part, flags=re.I)
        part = re.sub(r"\bSYSUTCDATETIME\(\)", NOW, part, flags=re.I)
        if re.search(r"(?:--|/\*|;)|\b(?:OPENJSON|OUTPUT|CROSS APPLY|OUTER APPLY|OBJECT_ID)\b", part, re.I):
            raise ValueError("unported_statement")
        fragments[index] = part.replace("%", "%%").replace("?", "%s")
    statement = "".join(fragments)
    statement = re.sub(r"^INSERT\s+(?!INTO\b)", "INSERT INTO ", statement, flags=re.I)
    match = TOP.match(statement)
    if match:
        statement = "SELECT " + statement[match.end():] + f" LIMIT {int(match[1])}"
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
    return statement


class Cursor:
    dialect = "postgresql"

    def __init__(self, cursor, table_map, columns):
        self._cursor = cursor
        self._table_map = table_map
        self._columns = columns
        self._aliases = {}

    def execute(self, statement, *parameters):
        sql = postgres_sql(statement, self._table_map)
        return self.native(sql, *parameters)

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

    def __iter__(self):
        return (self._row(row) for row in self._cursor)
