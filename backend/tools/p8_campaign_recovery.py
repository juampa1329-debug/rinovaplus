"""Native P8 backup/restoration with a closed 167-table partition."""

import hashlib
import shutil
from pathlib import Path, PurePosixPath
from uuid import uuid4
from app.institutional.campaign_policy import TARGET, layout
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import quote_name
from tools.p2_es_migrations import shape
from tools.p2_es_recovery import data_fingerprint, verify_backup
from tools.p2_es_recovery import restore as native_restore
from tools.rehearse_foundation import execute_results, literal


def tables():
    mapping = layout()
    return set(mapping["tables"].values()) | set(mapping["academic_tables"])


def fingerprint(cursor):
    return data_fingerprint(cursor, allowed_tables=tables())


def backup(connection, expected):
    cursor = connection.cursor()
    actual = identity(cursor)
    if (
        actual != expected
        or not TARGET.fullmatch(actual["database"])
        or (actual["engine"], actual["compatibility"]) != (15, 150)
    ):
        raise ValueError("P8ES_backup_target")
    before_shape = shape(cursor)
    before_data = fingerprint(cursor)
    path = str(
        PurePosixPath("/var/opt/mssql/data")
        / (expected["database"] + "_" + uuid4().hex + ".bak")
    )
    if cursor.execute(
        "SELECT file_exists FROM sys.dm_os_file_exists(?)", path
    ).fetchval():
        raise ValueError("P8ES_backup_collision")
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
        raise ValueError("P8ES_backup_media")
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
        raise ValueError("P8ES_backup_source_changed")
    return result


def restore(master, checkpoint, target):
    return native_restore(
        master,
        checkpoint,
        target,
        restricted=True,
        target_pattern=TARGET,
        allowed_tables=tables(),
    )


def copy_media(cursor, source_root, destination_root):
    """Copy only closed ready blobs; SQL backup alone does not contain file bytes."""
    source, destination = (Path(source_root), Path(destination_root))
    if (
        not source.is_absolute()
        or not destination.is_absolute()
        or source.is_symlink()
        or destination.exists()
        or (source.resolve() == destination.resolve())
    ):
        raise ValueError("P8ES_private_new_media_destination_required")
    destination.mkdir(mode=448, parents=True)
    manifest = []
    for media_id, storage, digest in cursor.execute(
        "SELECT MediaId,StorageKey,ContentHash FROM dbo.CRMCanalOperacionArchivo WHERE State='ready' ORDER BY MediaId"
    ).fetchall():
        from uuid import UUID

        expected = UUID(str(media_id)).hex + ".bin"
        if storage != expected:
            raise ValueError("P8ES_media_storage_identity")
        item = source / expected
        if (
            item.is_symlink()
            or not item.is_file()
            or hashlib.sha256(item.read_bytes()).digest() != bytes(digest)
        ):
            raise ValueError("P8ES_backup_media_integrity")
        target = destination / expected
        shutil.copyfile(item, target)
        target.chmod(384)
        if hashlib.sha256(target.read_bytes()).digest() != bytes(digest):
            raise ValueError("P8ES_restored_media_integrity")
        manifest.append(
            {"media_id": str(media_id).lower(), "sha256": bytes(digest).hex()}
        )
    import json

    for event_id, raw in cursor.execute(
        "SELECT EventId,Document FROM dbo.CRMFlujoEvento WHERE Kind='template_asset' ORDER BY EventId"
    ).fetchall():
        from uuid import UUID

        value = json.loads(raw)
        expected = UUID(str(event_id)).hex + ".bin"
        if value["id"] != str(UUID(str(event_id))):
            raise ValueError("P8ES_library_blob_identity")
        item = source / expected
        if (
            item.is_symlink()
            or not item.is_file()
            or item.stat().st_size != value["size"]
            or hashlib.sha256(item.read_bytes()).hexdigest() != value["sha256"]
        ):
            raise ValueError("P8ES_library_blob_integrity")
        target = destination / expected
        if target.exists():
            raise ValueError("P8ES_library_blob_collision")
        shutil.copyfile(item, target)
        target.chmod(0o600)
        if hashlib.sha256(target.read_bytes()).hexdigest() != value["sha256"]:
            raise ValueError("P8ES_library_restored_integrity")
        manifest.append(
            dict(
                media_id=str(UUID(str(event_id))),
                sha256=value["sha256"],
                scope="CRM_template_library",
            )
        )
    return manifest
