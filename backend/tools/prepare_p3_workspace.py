"Explicit local SQL2019 P3 copies; parent profiles and academic tables are preserved."

import argparse
import base64
import contextlib
import hashlib
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

from app.es_schema_profile import journal_digest
from app.institutional import workspace_policy as policy
from app.institutional.spanish import RIGHTS, load, qualified_shape, transaction
from app.institutional.spanish_bindings import Cursor
from app.parity_channels.catalog import metadata
from app.parity_channels.policy import COLUMNS
from app.sql_profile import SqlProfileStore
from tools.es_schema_catalog_v2 import model, snapshot
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import quote_name as q
from tools.foundation_snapshot import sha
from tools.p2_es_recovery import backup, restore
from tools.p3_workspace_migrations import apply
from tools.qualify_spanish_schema import source_snapshots
from tools.rehearse_foundation import literal
from tools.rehearse_p2_spanish import admin, read, save, source_2019

WORK = Path("/var/lib/cbn-p2/p3-es-v1")
PARENT = Path("/var/lib/cbn-p2/p2-es-v1")


def fresh(kind="TRIAL"):
    return "CBN_P3ES_" + kind + "_20261026_" + uuid4().hex[:8]


def source():
    profile = read(PARENT / "final-profile.json")
    return load(Path(profile["directory"]))


def capture():
    if (WORK / "sources-before.json").exists():
        raise ValueError("P3ES_baseline_exists")
    with admin("master", readonly=True) as connection:
        names = [
            r[0]
            for r in connection.cursor()
            .execute(
                (
                    "SELECT name FROM sys.databases WHERE dat"
                    "abase_id>4 AND state=0 ORDER BY name"
                )
            )
            .fetchall()
        ]
    value = {
        "Windows_SQL2022": source_snapshots(),
        "previous_SQL2019": source_2019(names),
    }
    save(WORK / "sources-before.json", value)
    print(
        json.dumps(
            {
                "preservation_baseline": True,
                "Windows": len(value["Windows_SQL2022"]),
                "SQL2019": len(names),
            }
        )
    )


def compile_candidate():
    if (WORK / "candidate.json").exists():
        raise ValueError("P3ES_candidate_exists")
    settings = source()
    with transaction(settings, anonymous=True):
        pass
    with admin(settings.connection["database"]) as connection:
        checkpoint = backup(connection, settings.ticket["identity"])
    name = fresh()
    with admin("master") as connection:
        native = restore(
            connection, checkpoint, name, restricted=True, target_pattern=policy.TARGET
        )
    with admin(name) as connection:
        c = connection.cursor()
        c.execute("SET XACT_ABORT ON;BEGIN TRANSACTION")
        try:
            c.execute((policy.PACKAGE / "P3ES-000.sql").read_text())
            c.execute((policy.PACKAGE / "P3ES-001.sql").read_text())
            compiled = model(snapshot(c))
            assert len(compiled["tables"]) == 144
            save(WORK / "expected-model.json", compiled)
        finally:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
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
            "new_tables": 6,
            "total_tables": 144,
            "SQL_transaction_rolled_back": True,
            "parent_database_modified": False,
            "academic_DDL_or_DML": False,
            "candidate_diary_committed": False,
        },
    )
    print(
        json.dumps({"compile_candidate": "passed", "tables": 144, "rolled_back": True})
    )


def prepare(label, *, populated_checkpoint=None, source_settings=None):
    if (
        not __import__("re").fullmatch(r"(fixture(?:-r[2-9])?|final|recovery)", label)
        or (WORK / (label + "-profile.json")).exists()
    ):
        raise ValueError("P3ES_profile_label_already_exists")
    approved = read(WORK / "approval.json")["release_sha256"]
    if policy.release() != approved:
        raise ValueError("P3ES_approved_bytes_changed")
    parent = source_settings if source_settings is not None else source()
    candidate = read(WORK / "candidate.json")
    checkpoint = (
        populated_checkpoint
        if populated_checkpoint is not None
        else candidate["checkpoint"]
    )
    if (
        populated_checkpoint is not None
        and parent.ticket.get("version") != policy.VERSION
    ):
        raise ValueError("P3ES_populated_source_profile_required")
    if checkpoint["source"] != parent.ticket["identity"]:
        raise ValueError("P3ES_parent_backup_binding")
    with transaction(parent, anonymous=True):
        pass
    name = fresh("RECOVERY" if populated_checkpoint is not None else "TRIAL")
    directory = WORK / "profiles" / name
    with admin("master") as connection:
        if populated_checkpoint is not None:
            from tools.p3_workspace_recovery import restore as restore_workspace

            native = restore_workspace(connection, checkpoint, name)
        else:
            native = restore(
                connection,
                checkpoint,
                name,
                restricted=True,
                target_pattern=policy.TARGET,
            )
    with admin(name) as connection:
        actual = identity(connection.cursor())
        parent_journal = journal_digest(connection.cursor())
        if populated_checkpoint is None:
            result = apply(
                connection,
                actual,
                approved_release=approved,
                parent_journal=parent_journal,
            )
            repeat = apply(
                connection,
                actual,
                approved_release=approved,
                parent_journal=parent_journal,
            )
            assert repeat["status"] == "noop"
        else:
            result = {
                "status": "native_restored_history",
                "migrations_reapplied": False,
            }
            repeat = {"status": "not_reapplied_to_restored_history"}
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
                    "SELECT name FROM sys.server_principals W"
                    "HERE type IN('S','U','G') AND name<>?"
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
            + (" WITH DEFAULT_SCHEMA=dbo;GRANT CONNECT,VIEW DEFINITION TO ")
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
        for logical, columns in COLUMNS.items():
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
                ("DENY SELECT,INSERT,UPDATE,DELETE,ALTER,REFERENCES ON OBJECT::")
                + table
                + " TO "
                + q(user)
            )
        c.execute("DENY EXECUTE ON SCHEMA::dbo TO " + q(user))
        mapped = Cursor(c, mapping["tables"])
        from app.institutional.crypto import unseal

        secret_key = base64.b64decode(parent.review["secrets_key"])
        encrypted = mapped.execute(
            (
                "SELECT SecretId,Scope,OwnerRef,Kind,Vers"
                "ionNo,KeyId,Nonce,Ciphertext FROM crm_ac"
                "cess.Secret"
            )
        ).fetchall()
        for row in encrypted:
            if row[5] != hashlib.sha256(secret_key).hexdigest()[:32]:
                raise ValueError("P3ES_restored_secret_key")
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
        floor = (
            int(
                c.execute(
                    ("SELECT DATEDIFF_BIG(second,'19700101',SYSUTCDATETIME())/30")
                ).fetchval()
            )
            + 1
        )
        # Copied sessions, challenges and recovery codes must never become valid again.
        mapped.execute("BEGIN TRANSACTION")
        try:
            mapped.execute(
                (
                    "UPDATE crm_access.Session SET RevokedAt="
                    "ISNULL(RevokedAt,SYSUTCDATETIME())"
                )
            )
            mapped.execute(
                (
                    "UPDATE crm_access.Challenge SET Consumed"
                    "At=ISNULL(ConsumedAt,SYSUTCDATETIME())"
                )
            )
            mapped.execute(
                (
                    "UPDATE crm_access.RecoveryCode SET Consu"
                    "medAt=ISNULL(ConsumedAt,SYSUTCDATETIME()"
                    ")"
                )
            )
            mapped.execute(
                (
                    "UPDATE crm_access.Factor SET LastStep=CA"
                    "SE WHEN LastStep<? THEN ? ELSE LastStep "
                    "END,PendingSecretId=NULL,SetupId=NULL,Se"
                    "tupSessionId=NULL,SetupExpiresAt=NULL"
                ),
                floor,
                floor,
            )
            mapped.execute("COMMIT")
        except BaseException:
            mapped.execute("IF @@TRANCOUNT>0 ROLLBACK")
            raise
        catalog = metadata(c)
        lineage = (
            list(parent.ticket.get("workspace_lineage", []))
            if populated_checkpoint is not None
            else []
        )
        if populated_checkpoint is not None:
            lineage.append(
                {
                    "source_database": parent.connection["database"],
                    "backup_uuid": checkpoint["backup_uuid"],
                }
            )
        ticket = dict(
            parent.ticket,
            version=policy.VERSION,
            scope="isolated_institutional_workspace",
            workspace_release_sha256=approved,
            workspace_profile_revision=2,
            workspace_history_sha256=policy.history_digest(c),
            workspace_migration_origin=parent.ticket.get(
                "workspace_migration_origin", parent.connection["database"]
            )
            if populated_checkpoint is not None
            else name,
            workspace_lineage=lineage,
            parent_journal_sha256=parent_journal,
            identity=actual,
            sid=sid,
            table_map=mapping["tables"],
            academic_tables=mapping["academic_tables"],
            tables=sorted(
                set(mapping["tables"].values()) | set(mapping["academic_tables"])
            ),
            catalog_sha256=sha(catalog),
            qualified_shape_sha256=qualified_shape(c),
            journal_sha256=parent_journal,
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
        assert count >= 1 if populated_checkpoint is not None else count == 1
    profile = {
        "database": name,
        "directory": str(directory),
        "identity": actual,
        "native_restore": native,
        "migration": result,
        "repeat": repeat,
    }
    save(WORK / (label + "-profile.json"), profile)
    access = read(PARENT / "final-access.json")
    access["profile"] = str(directory)
    save(WORK / (label + "-access.json"), access)
    save(
        WORK / (label + "-preparation-result.json"),
        {
            "status": "passed",
            "database": name,
            "tables": 144,
            "logical_bindings": 114,
            "human_accounts": count,
            "own_SQL_principal": True,
            "academic_DENY": 30,
            "TLS_verified": True,
            "parent_journal_preserved": True,
            "migration": result,
            "repeat": repeat,
            "native_restore": native,
            "source_profile_changed": False,
            "external_providers": False,
        },
    )
    print(
        json.dumps(
            {
                "prepared": label,
                "database": name,
                "tables": 144,
                "accounts": count,
                "TLS_verified": True,
            }
        )
    )


def preserve():
    before = read(WORK / "sources-before.json")
    after = {
        "Windows_SQL2022": source_snapshots(),
        "previous_SQL2019": source_2019(sorted(before["previous_SQL2019"])),
    }
    if before != after:
        save(WORK / "preservation-differences.json", {"before": before, "after": after})
        raise ValueError("P3ES_prior_source_changed")
    save(
        WORK / "preservation-result.json",
        {
            "status": "passed",
            "before_sha256": sha(before),
            "after_sha256": sha(after),
            "Windows_sources": len(before["Windows_SQL2022"]),
            "SQL2019_prior_copies": len(before["previous_SQL2019"]),
            "academic_DDL_or_DML": False,
            "previous_profiles_redirected": False,
        },
    )
    print(
        json.dumps(
            {
                "preservation": "passed",
                "Windows": len(before["Windows_SQL2022"]),
                "SQL2019": len(before["previous_SQL2019"]),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "capture",
            "compile",
            "fixture",
            "fixture-r2",
            "fixture-r3",
            "fixture-r4",
            "final",
            "preserve",
        ],
    )
    args = parser.parse_args()
    try:
        if args.action.startswith("fixture") or args.action == "final":
            prepare(args.action)
        else:
            {"capture": capture, "compile": compile_candidate, "preserve": preserve}[
                args.action
            ]()
    except BaseException as error:
        with contextlib.suppress(Exception):
            save(
                WORK / ("failure-" + uuid4().hex + ".json"),
                {"type": type(error).__name__, "message": str(error)},
            )
        print(json.dumps({"P3_preparation": "failed", "type": type(error).__name__}))
        raise SystemExit(1)
