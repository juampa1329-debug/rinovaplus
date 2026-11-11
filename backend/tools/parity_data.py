"""Administrative binary digests over the exact 89-table C12 partition."""

import hashlib

from tools.channels_parity_snapshot import NEW_TABLES, OLD_TABLES
from tools.foundation_snapshot import encode, quote_name, records, sha

ALLOWED = set(OLD_TABLES + NEW_TABLES)


def signature(cursor, tables):
    if not set(tables) <= ALLOWED or len(tables) != len(set(tables)):
        raise ValueError("C12_digest_partition")
    result = []
    for table in sorted(tables):
        columns = records(
            cursor,
            (
                "SELECT name FROM sys.columns WHERE "
                "object_id=OBJECT_ID(?,'U') ORDER BY column_id"
            ),
            (table,),
        )
        if not columns:
            raise ValueError("C12_digest_missing_table")
        projection = ",".join(
            "CONVERT(varbinary(max)," + quote_name(r["name"]) + ")" for r in columns
        )
        cursor.execute(
            "SELECT "
            + projection
            + " FROM "
            + ".".join(map(quote_name, table.split(".")))
        )
        values = []
        while batch := cursor.fetchmany(1000):
            values.extend(hashlib.sha256(encode(list(row))).digest() for row in batch)
            if len(values) > 1000000:
                raise ValueError("C12_digest_row_limit")
        result.append(
            {
                "table": table,
                "rows": len(values),
                "sha256": hashlib.sha256(b"".join(sorted(values))).hexdigest(),
            }
        )
    return {
        "tables": len(result),
        "rows": sum(r["rows"] for r in result),
        "sha256": sha(result),
    }


def full_snapshot(connection):
    from tools.channels_parity_snapshot import metadata

    cursor = connection.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;BEGIN TRANSACTION;")
    try:
        shape = metadata(cursor)
        names = [
            r["schema_name"] + "." + r["name"]
            for r in shape["catalog"]
            if r["type"].strip() == "U"
        ]
        result = {"catalog_sha256": sha(shape), "data": signature(cursor, names)}
        cursor.execute("COMMIT;SET TRANSACTION ISOLATION LEVEL READ COMMITTED;")
        return result
    except BaseException:
        cursor.execute("IF @@TRANCOUNT>0 ROLLBACK;")
        raise
    finally:
        cursor.close()
