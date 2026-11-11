"""Identity-bound native SQL2019 recovery; no overwrite or source mutations."""

import hashlib
from pathlib import PurePosixPath
from uuid import uuid4

from tools.es_schema_migrate_v2 import PACKAGE, TARGET, guard, identity, shape
from tools.foundation_snapshot import encode, quote_name, sha
from tools.rehearse_foundation import checkdb, execute_results, literal


def data_fingerprint(cursor):
    import json

    layout = json.loads((PACKAGE / "table_map.json").read_text(encoding="utf-8"))
    allowed = (
        set(layout["CRM_map"].values())
        | set(layout["academic_tables"])
        | {"crm_meta.MigrationJournal"}
    )
    names = [
        r[0] + "." + r[1]
        for r in cursor.execute(
            "SELECT SCHEMA_NAME(schema_id),name FROM sys.tables WHERE is_ms_shipped=0 ORDER BY SCHEMA_NAME(schema_id),name"
        ).fetchall()
    ]
    if not set(names) <= allowed:
        raise ValueError("ES_data_fingerprint_partition")
    result = []
    for name in names:
        columns = [
            r[0]
            for r in cursor.execute(
                "SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(?) ORDER BY column_id",
                name,
            ).fetchall()
        ]
        projection = ",".join(
            "CONVERT(varbinary(max)," + quote_name(c) + ")" for c in columns
        )
        cursor.execute(
            "SELECT "
            + projection
            + " FROM "
            + ".".join(map(quote_name, name.split(".")))
        )
        rows = []
        while batch := cursor.fetchmany(1000):
            rows.extend(hashlib.sha256(encode(list(row))).digest() for row in batch)
            if len(rows) > 1000000:
                raise ValueError("ES_data_fingerprint_limit")
        result.append(
            {
                "table": name,
                "rows": len(rows),
                "sha256": hashlib.sha256(b"".join(sorted(rows))).hexdigest(),
            }
        )
    return {
        "tables": len(names),
        "rows": sum(r["rows"] for r in result),
        "sha256": sha(result),
    }


def verify_backup(cursor, checkpoint):
    path = PurePosixPath(checkpoint["path"])
    if (
        path.parent != PurePosixPath("/var/opt/mssql/data")
        or not path.name.startswith(checkpoint["source"]["database"] + "_")
        or path.suffix != ".bak"
    ):
        raise ValueError("ES_backup_path_binding")
    rows = execute_results(cursor, "RESTORE HEADERONLY FROM DISK=" + literal(str(path)))
    if len(rows) != 1:
        raise ValueError("ES_backup_media_layout")
    header = rows[0]
    if (
        str(header["BackupSetGUID"]).lower() != checkpoint["backup_uuid"].lower()
        or header["DatabaseName"] != checkpoint["source"]["database"]
        or header["SoftwareVersionMajor"] != 15
        or header["BackupType"] != 1
        or header["Position"] != 1
        or not header["HasBackupChecksums"]
        or not header["IsCopyOnly"]
        or header["ServerName"] != checkpoint["source"]["server"]
    ):
        raise ValueError("ES_backup_identity_or_header")
    execute_results(
        cursor, "RESTORE VERIFYONLY FROM DISK=" + literal(str(path)) + " WITH CHECKSUM"
    )
    return header


def backup(connection, expected):
    cursor = connection.cursor()
    guard(cursor, expected)
    before_shape = shape(cursor)
    before_data = data_fingerprint(cursor)
    path = str(
        PurePosixPath("/var/opt/mssql/data")
        / (expected["database"] + "_" + uuid4().hex + ".bak")
    )
    if cursor.execute(
        "SELECT file_exists FROM sys.dm_os_file_exists(?)", path
    ).fetchval():
        raise ValueError("ES_backup_collision")
    execute_results(
        cursor,
        "BACKUP DATABASE "
        + quote_name(expected["database"])
        + " TO DISK="
        + literal(path)
        + " WITH COPY_ONLY,CHECKSUM",
    )
    header = execute_results(cursor, "RESTORE HEADERONLY FROM DISK=" + literal(path))
    if len(header) != 1:
        raise ValueError("ES_backup_media_layout")
    value = {
        "path": path,
        "source": expected,
        "backup_uuid": str(header[0]["BackupSetGUID"]).lower(),
        "checksum": True,
        "copy_only": True,
        "shape_sha256": before_shape,
        "data": before_data,
    }
    verify_backup(cursor, value)
    if shape(cursor) != before_shape or data_fingerprint(cursor) != before_data:
        raise ValueError("ES_backup_source_changed")
    cursor.close()
    return value


def restore(master, checkpoint, target):
    if not TARGET.fullmatch(target) or target == checkpoint["source"]["database"]:
        raise ValueError("ES_restore_target")
    cursor = master.cursor()
    server = identity(cursor)
    if server["database"] != "master" or (
        server["engine"],
        server["machine"],
        server["server"],
    ) != (15, checkpoint["source"]["machine"], checkpoint["source"]["server"]):
        raise ValueError("ES_restore_server")
    if cursor.execute("SELECT 1 FROM sys.databases WHERE name=?", target).fetchone():
        raise ValueError("ES_restore_existing_database")
    verify_backup(cursor, checkpoint)
    files = execute_results(
        cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(checkpoint["path"])
    )
    if len(files) != 2 or {f["Type"] for f in files} != {"D", "L"}:
        raise ValueError("ES_restore_file_layout")
    moves = []
    for f in files:
        path = str(
            PurePosixPath("/var/opt/mssql/data")
            / (target + ("_log.ldf" if f["Type"] == "L" else ".mdf"))
        )
        if cursor.execute(
            "SELECT file_exists FROM sys.dm_os_file_exists(?)", path
        ).fetchval():
            raise ValueError("ES_restore_file_collision")
        moves.append("MOVE " + literal(f["LogicalName"]) + " TO " + literal(path))
    execute_results(
        cursor,
        "RESTORE DATABASE "
        + quote_name(target)
        + " FROM DISK="
        + literal(checkpoint["path"])
        + " WITH "
        + ",".join(moves)
        + ",CHECKSUM,RECOVERY",
    )
    checkdb(cursor, target)
    cursor.execute("USE " + quote_name(target))
    try:
        restored_shape = shape(cursor)
        restored_data = data_fingerprint(cursor)
        if (
            restored_shape != checkpoint["shape_sha256"]
            or restored_data != checkpoint["data"]
        ):
            raise ValueError("ES_restored_catalog_or_data_mismatch")
        if identity(cursor)["engine"] != 15:
            raise ValueError("ES_restored_engine")
    finally:
        cursor.execute("USE master")
        cursor.close()
    return {
        "target": target,
        "backup_uuid": checkpoint["backup_uuid"],
        "header_identity_verified": True,
        "verify_only": True,
        "checkdb": True,
        "catalog_equal": True,
        "data_equal": True,
        "replace": False,
        "source_database_modified": False,
    }
