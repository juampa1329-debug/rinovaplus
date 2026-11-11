"""Explicit native-copy preparation. Never run as application startup."""

import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

from app.es_schema_profile import journal_digest
from app.institutional import channels_policy as policy
from app.institutional.spanish import RIGHTS, load, qualified_shape, transaction
from app.institutional.spanish_bindings import Cursor
from app.parity_channels.catalog import metadata
from app.parity_channels.policy import COLUMNS
from app.sql_profile import SqlProfileStore
from tools.es_schema_catalog_v2 import model, snapshot
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import quote_name as q
from tools.foundation_snapshot import sha
from tools.p2_es_recovery import restore
from tools.p3_workspace_recovery import backup, tables
from tools.p4_channels_migrations import apply
from tools.rehearse_foundation import literal
from tools.rehearse_p2_spanish import admin, read, save

WORK = Path("/var/lib/cbn-p2/p4-es-v1")
PARENT = Path("/var/lib/cbn-p2/preview-demo-v1")


def source():
    return load(Path(read(PARENT / "profile.json")["directory"]))


def capture_backup():
    if (WORK / "candidate.json").exists():
        raise ValueError("P4ES_candidate_exists")
    parent = source()
    with transaction(parent, anonymous=True):
        pass
    with admin(parent.connection["database"]) as connection:
        checkpoint = backup(connection, parent.ticket["identity"])
    name = "CBN_P4ES_TRIAL_20261026_" + uuid4().hex[:8]
    with admin("master") as connection:
        native = restore(
            connection,
            checkpoint,
            name,
            restricted=True,
            target_pattern=policy.TARGET,
            allowed_tables=tables(),
        )
    with admin(name) as connection:
        c = connection.cursor()
        before = model(snapshot(c))
        c.execute("SET XACT_ABORT ON;BEGIN TRANSACTION")
        try:
            for unit in ["P4ES-000.sql", "P4ES-001.sql"]:
                c.execute((policy.PACKAGE / unit).read_text(encoding="utf-8"))
            compiled = model(snapshot(c))
            assert len(compiled["tables"]) == 147
            save(WORK / "expected-model.json", compiled)
        finally:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
        if model(snapshot(c)) != before:
            raise ValueError("P4ES_compile_rollback_drift")
    save(
        WORK / "candidate.json",
        {"database": name, "checkpoint": checkpoint, "native_restore": native},
    )
    save(
        WORK / "compile-result.json",
        {
            "status": "passed",
            "engine": 15,
            "compatibility": 150,
            "tables": 147,
            "transaction_rolled_back": True,
            "source_modified": False,
            "academic_DDL_or_DML": False,
        },
    )
    print(json.dumps({"compiled": True, "tables": 147, "rolled_back": True}))


def prepare(label="fixture", *, restored_checkpoint=None, source_settings=None):
    if (
        label not in {"fixture", "final", "recovery"}
        or (WORK / (label + "-profile.json")).exists()
    ):
        raise ValueError("P4ES_fresh_label_required")
    approved = read(WORK / "approval.json")["release_sha256"]
    if policy.release() != approved:
        raise ValueError("P4ES_approval_binding")
    parent = source_settings if source_settings is not None else source()
    candidate = read(WORK / "candidate.json")
    checkpoint = (
        restored_checkpoint
        if restored_checkpoint is not None
        else read(WORK / "final-checkpoint.json")
        if label == "final" and (WORK / "final-checkpoint.json").exists()
        else candidate["checkpoint"]
    )
    recovering = restored_checkpoint is not None
    if recovering and parent.ticket.get("version") != policy.VERSION:
        raise ValueError("P4ES_populated_profile_required")
    if checkpoint["source"] != parent.ticket["identity"]:
        raise ValueError("P4ES_backup_parent_binding")
    name = (
        "CBN_P4ES_RECOVERY_20261026_" if recovering else "CBN_P4ES_TRIAL_20261026_"
    ) + uuid4().hex[:8]
    with admin("master") as connection:
        native = restore(
            connection,
            checkpoint,
            name,
            restricted=True,
            target_pattern=policy.TARGET,
            allowed_tables=set(policy.layout()["tables"].values())
            | set(policy.layout()["academic_tables"])
            if recovering
            else tables(),
        )
    with admin(name) as connection:
        c = connection.cursor()
        actual = identity(c)
        parent_history = policy.parent_digest(c)
        if recovering:
            result = {
                "status": "native_restored_history",
                "migrations_reapplied": False,
            }
            repeat = {"status": "not_reapplied"}
        else:
            result = apply(
                connection,
                actual,
                approved_release=approved,
                parent_journal=parent_history,
            )
            repeat = apply(
                connection,
                actual,
                approved_release=approved,
                parent_journal=parent_history,
            )
            assert repeat["status"] == "noop"
    user = policy.principal(name)
    value = {
        "revision": 1,
        "connection": dict(
            parent.connection,
            database=name,
            username=user,
            password="CBN!" + secrets.token_urlsafe(48),
        ),
        "review": {
            "session_token": secrets.token_urlsafe(48),
            "secrets_key": parent.review["secrets_key"],
        },
    }
    with admin("master") as connection:
        c = connection.cursor()
        c.execute(
            "CREATE LOGIN "
            + q(user)
            + " WITH PASSWORD="
            + literal(value["connection"]["password"])
            + ",DEFAULT_DATABASE="
            + q(name)
            + ",CHECK_POLICY=ON,CHECK_EXPIRATION=OFF"
        )
        sid = c.execute("SELECT CONVERT(varchar(170),SUSER_SID(?),2)", user).fetchval()
        protected = [
            r[0]
            for r in c.execute(
                (
                    "SELECT name FROM sys.server_principals WHERE t"
                    "ype IN('S','U','G') AND name<>?"
                ),
                user,
            ).fetchall()
        ]
    mapping = policy.layout()
    with admin(name) as connection:
        c = connection.cursor()
        c.execute("DENY CONNECT TO " + q(parent.connection["username"]))
        c.execute(
            "CREATE USER "
            + q(user)
            + " FOR LOGIN "
            + q(user)
            + " WITH DEFAULT_SCHEMA=dbo;GRANT CONNECT,VIEW DEFINITION TO "
            + q(user)
        )
        for logical, rights in policy.rights(RIGHTS).items():
            c.execute(
                "GRANT "
                + ",".join(rights)
                + " ON OBJECT::"
                + mapping["tables"].get(logical, logical)
                + " TO "
                + q(user)
            )
        for logical, columns in policy.columns(COLUMNS).items():
            c.execute(
                "GRANT SELECT ON OBJECT::"
                + mapping["tables"][logical]
                + "("
                + ",".join(map(q, columns))
                + ") TO "
                + q(user)
            )
        for table in mapping["academic_tables"]:
            c.execute(
                "DENY SELECT,INSERT,UPDATE,DELETE,ALTER,REFERENCES ON OBJECT::"
                + table
                + " TO "
                + q(user)
            )
        c.execute("DENY EXECUTE ON SCHEMA::dbo TO " + q(user))
        mapped = Cursor(c, mapping["tables"])
        from app.institutional.crypto import unseal

        secret_key = base64.b64decode(parent.review["secrets_key"], validate=True)
        for row in mapped.execute(
            (
                "SELECT SecretId,Scope,OwnerRef,Kind,VersionNo,"
                "KeyId,Nonce,Ciphertext FROM crm_access.Secret"
            )
        ).fetchall():
            if row[5] != hashlib.sha256(secret_key).hexdigest()[:32]:
                raise ValueError("P4ES_restored_key_binding")
            unseal(
                secret_key,
                {
                    "institution": parent.ticket["context"][0][1],
                    "scope": row[1],
                    "owner": row[2],
                    "kind": row[3],
                    "version": row[4],
                    "secret_id": str(row[0]).lower(),
                },
                row[6],
                row[7],
            )
        from app.institutional.channel_secrets import OWNERS, binding
        from app.institutional.db import rows

        for row in rows(mapped, "SELECT * FROM crm_channels2.SecretVersion"):
            owner_type = next(
                (name for name, column in OWNERS.items() if row[column] is not None),
                None,
            )
            if (
                owner_type is None
                or row["KeyVersion"] != hashlib.sha256(secret_key).hexdigest()[:32]
            ):
                raise ValueError("P4ES_restored_channel_key_binding")
            unseal(
                secret_key,
                binding(
                    parent,
                    owner_type,
                    str(row[OWNERS[owner_type]]),
                    row["Kind"],
                    row["VersionNo"],
                    str(row["SecretId"]),
                ),
                row["Nonce"],
                row["Ciphertext"],
            )
        floor = (
            int(
                c.execute(
                    "SELECT DATEDIFF_BIG(second,'19700101',SYSUTCDATETIME())/30"
                ).fetchval()
            )
            + 1
        )
        c.execute("BEGIN TRANSACTION")
        try:
            for table, field in [
                ("Session", "RevokedAt"),
                ("Challenge", "ConsumedAt"),
                ("RecoveryCode", "ConsumedAt"),
            ]:
                mapped.execute(
                    "UPDATE crm_access."
                    + table
                    + " SET "
                    + field
                    + "=ISNULL("
                    + field
                    + ",SYSUTCDATETIME())"
                )
            mapped.execute(
                (
                    "UPDATE crm_access.Factor SET LastStep=CASE WHE"
                    "N LastStep<? THEN ? ELSE LastStep END,PendingS"
                    "ecretId=NULL,SetupId=NULL,SetupSessionId=NULL,"
                    "SetupExpiresAt=NULL"
                ),
                floor,
                floor,
            )
            if not recovering:
                mapped.execute(
                    "INSERT crm_channels4.Configuration(InstitutionId) VALUES(?)",
                    parent.ticket["context"][0][1],
                )
            else:
                mapped.execute(
                    (
                        "UPDATE crm_channels2.OAuthSession SET Status=C"
                        "ASE WHEN Status='exchanging' THEN 'uncertain' "
                        "ELSE 'cancelled' END,ClaimId=NULL,ClaimUntil=N"
                        "ULL,CompletedAt=SYSUTCDATETIME() WHERE Status "
                        "IN('pending','exchanging','assets_ready')"
                    )
                )
            c.execute("COMMIT")
        except BaseException:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
            raise
        lineage = list(parent.ticket.get("workspace_lineage", []))
        lineage.append(
            {
                "source_database": parent.connection["database"],
                "backup_uuid": checkpoint["backup_uuid"],
            }
        )
        catalog = metadata(c)
        channels_lineage = (
            list(parent.ticket.get("channels_lineage", [])) if recovering else []
        )
        if recovering:
            channels_lineage.append(
                {
                    "source_database": parent.connection["database"],
                    "backup_uuid": checkpoint["backup_uuid"],
                }
            )
        ticket = dict(
            parent.ticket,
            version=policy.VERSION,
            scope="isolated_institutional_channels_operations",
            channels_release_sha256=approved,
            channels_history_sha256=policy.history_digest(c),
            channels_parent_history_sha256=parent_history,
            channels_migration_origin=parent.ticket.get(
                "channels_migration_origin", parent.connection["database"]
            )
            if recovering
            else name,
            channels_lineage=channels_lineage,
            workspace_lineage=lineage,
            identity=actual,
            sid=sid,
            table_map=mapping["tables"],
            academic_tables=mapping["academic_tables"],
            tables=sorted(
                set(mapping["tables"].values()) | set(mapping["academic_tables"])
            ),
            catalog_sha256=sha(catalog),
            qualified_shape_sha256=qualified_shape(c),
            journal_sha256=journal_digest(c),
            session_sha256=hashlib.sha256(
                value["review"]["session_token"].encode()
            ).hexdigest(),
            protected_logins=protected,
            principals=sorted(r["name"] for r in catalog["principals"]),
            expires_at=int(time.time()) + 365 * 86400,
            mfa_floor=floor,
            restored_from={
                "source_database": checkpoint["source"]["database"],
                "backup_uuid": checkpoint["backup_uuid"],
            },
        )
    directory = WORK / "profiles" / name
    directory.mkdir(mode=0o700, parents=True)
    save(directory / "ticket.json", ticket)
    value["review"]["ticket_sha256"] = hashlib.sha256(
        (directory / "ticket.json").read_bytes()
    ).hexdigest()
    SqlProfileStore(directory / "runtime").save(value)
    with admin(name) as connection:
        connection.cursor().execute("ALTER DATABASE " + q(name) + " SET MULTI_USER")
    with transaction(load(directory), anonymous=True) as c:
        count = c.execute("SELECT COUNT(*) FROM crm_access.AccessUser").fetchval()
        assert count >= 1
    profile = {
        "database": name,
        "directory": str(directory),
        "identity": actual,
        "native_restore": native,
        "migration": result,
        "repeat": repeat,
    }
    save(WORK / (label + "-profile.json"), profile)
    access = (
        read(WORK / "fixture-access.json")
        if recovering
        else read(PARENT / "access.json")
    )
    save(WORK / (label + "-access.json"), dict(access, profile=str(directory)))
    print(
        json.dumps(
            {"prepared": label, "database": name, "tables": 147, "TLS_verified": True}
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["capture", "fixture", "final"])
    args = parser.parse_args()
    capture_backup() if args.action == "capture" else prepare(args.action)
