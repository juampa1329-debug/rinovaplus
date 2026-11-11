"Identity-bound native SQL2019 recovery; no overwrite or source mutations."

import hashlib
from pathlib import PurePosixPath
from uuid import uuid4

from app.institutional.spanish_bindings import layout
from tools.foundation_snapshot import encode, quote_name, sha
from tools.p2_es_migrations import TARGET, guard, identity, shape
from tools.rehearse_foundation import checkdb, execute_results, literal


def data_fingerprint(cursor, *, omit_journal=False, allowed_tables=None):
    mapping = layout()
    allowed = set(mapping["tables"].values()) | set(mapping["academic_tables"])
    if allowed_tables is not None:
        allowed = set(allowed_tables)
    names = [
        r[0] + "." + r[1]
        for r in cursor.execute(
            (
                "SELECT SCHEMA_NAME(schema_id),name FROM "
                "sys.tables WHERE is_ms_shipped=0 ORDER B"
                "Y SCHEMA_NAME(schema_id),name"
            )
        ).fetchall()
    ]
    if omit_journal:
        names = [name for name in names if name != "crm_meta.MigrationJournal"]
    if not set(names) <= allowed:
        raise ValueError("P2ES_data_fingerprint_partition")
    result = []
    for name in names:
        columns = [
            r[0]
            for r in cursor.execute(
                (
                    "SELECT name FROM sys.columns WHERE objec"
                    "t_id=OBJECT_ID(?) ORDER BY column_id"
                ),
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
                raise ValueError("P2ES_data_fingerprint_limit")
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
        raise ValueError("P2ES_backup_path_binding")
    rows = execute_results(cursor, "RESTORE HEADERONLY FROM DISK=" + literal(str(path)))
    if len(rows) != 1:
        raise ValueError("P2ES_backup_media_layout")
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
        raise ValueError("P2ES_backup_identity_or_header")
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
        ("SELECT file_exists FROM sys.dm_os_file_exists(?)"), path
    ).fetchval():
        raise ValueError("P2ES_backup_collision")
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
        raise ValueError("P2ES_backup_media_layout")
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
        raise ValueError("P2ES_backup_source_changed")
    cursor.close()
    return value


def restore(
    master,
    checkpoint,
    target,
    *,
    restricted=False,
    target_pattern=TARGET,
    allowed_tables=None,
):
    if (
        not target_pattern.fullmatch(target)
        or target == checkpoint["source"]["database"]
    ):
        raise ValueError("P2ES_restore_target")
    cursor = master.cursor()
    server = identity(cursor)
    if server["database"] != "master" or (
        server["engine"],
        server["machine"],
        server["server"],
    ) != (15, checkpoint["source"]["machine"], checkpoint["source"]["server"]):
        raise ValueError("P2ES_restore_server")
    if cursor.execute("SELECT 1 FROM sys.databases WHERE name=?", target).fetchone():
        raise ValueError("P2ES_restore_existing_database")
    verify_backup(cursor, checkpoint)
    files = execute_results(
        cursor, "RESTORE FILELISTONLY FROM DISK=" + literal(checkpoint["path"])
    )
    if len(files) != 2 or {f["Type"] for f in files} != {"D", "L"}:
        raise ValueError("P2ES_restore_file_layout")
    moves = []
    for f in files:
        path = str(
            PurePosixPath("/var/opt/mssql/data")
            / (target + ("_log.ldf" if f["Type"] == "L" else ".mdf"))
        )
        if cursor.execute(
            ("SELECT file_exists FROM sys.dm_os_file_exists(?)"), path
        ).fetchval():
            raise ValueError("P2ES_restore_file_collision")
        moves.append("MOVE " + literal(f["LogicalName"]) + " TO " + literal(path))
    execute_results(
        cursor,
        "RESTORE DATABASE "
        + quote_name(target)
        + " FROM DISK="
        + literal(checkpoint["path"])
        + " WITH "
        + ",".join(moves)
        + ",CHECKSUM,RECOVERY"
        + (",RESTRICTED_USER" if restricted else ""),
    )
    checkdb(cursor, target)
    cursor.execute("USE " + quote_name(target))
    try:
        restored_shape = shape(cursor)
        restored_data = data_fingerprint(cursor, allowed_tables=allowed_tables)
        if (
            restored_shape != checkpoint["shape_sha256"]
            or restored_data != checkpoint["data"]
        ):
            raise ValueError("P2ES_restored_catalog_or_data_mismatch")
        if identity(cursor)["engine"] != 15:
            raise ValueError("P2ES_restored_engine")
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
        "restricted_from_restore": restricted,
    }
