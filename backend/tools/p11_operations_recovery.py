"""Native P11 backup; schema/readers from accepted predecessors stay immutable."""

from pathlib import PurePosixPath
from uuid import uuid4

from app.institutional.operations_policy import TARGET
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import quote_name
from tools.p2_es_migrations import shape
from tools.p2_es_recovery import verify_backup
from tools.p10_learning_recovery import copy_media as copy_media
from tools.p10_learning_recovery import fingerprint
from tools.rehearse_foundation import execute_results, literal


def backup(connection, expected):
    cursor = connection.cursor()
    actual = identity(cursor)
    if (
        actual != expected
        or not TARGET.fullmatch(actual["database"])
        or (actual["engine"], actual["compatibility"]) != (15, 150)
    ):
        raise ValueError("P11ES_backup_target")
    before_shape = shape(cursor)
    before_data = fingerprint(cursor)
    path = str(
        PurePosixPath("/var/opt/mssql/data")
        / (expected["database"] + "_" + uuid4().hex + ".bak")
    )
    if cursor.execute(
        "SELECT file_exists FROM sys.dm_os_file_exists(?)", path
    ).fetchval():
        raise ValueError("P11ES_backup_collision")
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
        raise ValueError("P11ES_backup_media")
    result = {
        "path": path,
        "source": actual,
        "backup_uuid": str(header[0]["BackupSetGUID"]).lower(),
        "checksum": True,
        "copy_only": True,
        "shape_sha256": before_shape,
        "data": before_data,
    }
    verify_backup(cursor, result)
    if shape(cursor) != before_shape or fingerprint(cursor) != before_data:
        raise ValueError("P11ES_backup_source_changed")
    return result
