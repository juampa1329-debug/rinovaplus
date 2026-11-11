"""Native COPY_ONLY/CHECKSUM recovery into a new explicit SQL2019 database."""

from pathlib import PurePosixPath
from uuid import uuid4

from tools.es_schema_migrate import TARGET, guard, identity
from tools.foundation_snapshot import quote_name
from tools.rehearse_foundation import checkdb, execute_results, literal


def backup(connection, expected):
    cursor = connection.cursor()
    guard(cursor, expected)
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
    execute_results(
        cursor, "RESTORE VERIFYONLY FROM DISK=" + literal(path) + " WITH CHECKSUM"
    )
    header = execute_results(cursor, "RESTORE HEADERONLY FROM DISK=" + literal(path))
    if (
        len(header) != 1
        or header[0]["DatabaseName"] != expected["database"]
        or not header[0]["HasBackupChecksums"]
        or not header[0]["IsCopyOnly"]
        or header[0]["SoftwareVersionMajor"] != 15
    ):
        raise ValueError("ES_backup_header")
    return {
        "path": path,
        "source": expected,
        "backup_uuid": str(header[0]["BackupSetGUID"]),
        "checksum": True,
        "copy_only": True,
    }


def restore(master, checkpoint, target):
    if not TARGET.fullmatch(target) or target == checkpoint["source"]["database"]:
        raise ValueError("ES_restore_target")
    cursor = master.cursor()
    server = identity(cursor)
    if (server["engine"], server["machine"], server["server"]) != (
        15,
        checkpoint["source"]["machine"],
        checkpoint["source"]["server"],
    ):
        raise ValueError("ES_restore_server")
    if cursor.execute("SELECT 1 FROM sys.databases WHERE name=?", target).fetchone():
        raise ValueError("ES_restore_existing_database")
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
    return {
        "target": target,
        "backup_uuid": checkpoint["backup_uuid"],
        "verify_only": True,
        "checkdb": True,
        "replace": False,
        "source_database_modified": False,
    }
