"""Explicit native-copy preparation, never called by application startup."""

import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from uuid import uuid4

from app.es_schema_profile import journal_digest
from app.institutional import agents_policy as policy
from app.institutional import channels_policy
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
from tools.p4_channels_recovery import backup
from tools.p5_agents_migrations import apply
from tools.rehearse_foundation import literal
from tools.rehearse_p2_spanish import admin, read, save

WORK = Path("/var/lib/cbn-p2/p5-es-v1")
PARENT = Path("/var/lib/cbn-p2/p4-es-v1")


def source():
    return load(Path(read(PARENT / "final-profile.json")["directory"]))


def parent_tables():
    mapping = channels_policy.layout()
    return set(mapping["tables"].values()) | set(mapping["academic_tables"])


def capture():
    if (WORK / "candidate.json").exists():
        raise ValueError("P5ES_candidate_already_exists")
    parent = source()
    with transaction(parent, anonymous=True):
        pass
    with admin(parent.connection["database"]) as connection:
        checkpoint = backup(connection, parent.ticket["identity"])
    name = "CBN_P5ES_TRIAL_20261027_" + uuid4().hex[:8]
    with admin("master") as connection:
        native = restore(
            connection,
            checkpoint,
            name,
            restricted=True,
            target_pattern=policy.TARGET,
            allowed_tables=parent_tables(),
        )
    with admin(name) as connection:
        c = connection.cursor()
        before = model(snapshot(c))
        c.execute("SET XACT_ABORT ON;BEGIN TRANSACTION")
        try:
            for unit in ["P5ES-000.sql", "P5ES-001.sql"]:
                c.execute((policy.PACKAGE / unit).read_text(encoding="utf-8"))
            compiled = model(snapshot(c))
            assert len(compiled["tables"]) == 150
            save(WORK / "expected-model.json", compiled)
        finally:
            c.execute("IF @@TRANCOUNT>0 ROLLBACK")
        assert model(snapshot(c)) == before
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
            "tables": 150,
            "transaction_rolled_back": True,
            "academic_DDL_or_DML": False,
        },
    )
    print(
        json.dumps(
            {"compiled_tables": 150, "rolled_back": True, "source_modified": False}
        )
    )


def prepare(label="fixture", *, checkpoint=None, recovering_from=None):
    WORK.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (WORK / (label + "-profile.json")).exists():
        raise ValueError("P5ES_fresh_label_required")
    parent = recovering_from or source()
    recovering = recovering_from is not None
    candidate = read(WORK / "candidate.json")
    checkpoint = checkpoint or (
        read(WORK / "final-checkpoint.json")
        if label == "final"
        else candidate["checkpoint"]
    )
    if checkpoint["source"] != parent.ticket["identity"]:
        raise ValueError("P5ES_checkpoint_binding")
    approved = read(WORK / "approval.json")["release_sha256"]
    if approved != policy.release():
        raise ValueError("P5ES_release_binding")
    name = (
        "CBN_P5ES_"
        + ("RECOVERY" if recovering else "TRIAL")
        + "_20261027_"
        + uuid4().hex[:8]
    )
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
            else parent_tables(),
        )
    with admin(name) as connection:
        actual = identity(connection.cursor())
        history = policy.parent_digest(connection.cursor())
        result = (
            {"status": "native_restored_history"}
            if recovering
            else apply(
                connection, actual, approved_release=approved, parent_journal=history
            )
        )
        if not recovering:
            assert (
                apply(
                    connection,
                    actual,
                    approved_release=approved,
                    parent_journal=history,
                )["status"]
                == "noop"
            )
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
                "SELECT name FROM sys.server_principals WHERE type IN('S','U','G') AND name<>?",
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
        from app.institutional.channel_secrets import OWNERS, binding
        from app.institutional.crypto import unseal
        from app.institutional.db import rows

        secret_key = base64.b64decode(parent.review["secrets_key"], validate=True)
        for row in rows(mapped, "SELECT * FROM crm_access.Secret"):
            unseal(
                secret_key,
                {
                    "institution": parent.ticket["context"][0][1],
                    "scope": row["Scope"],
                    "owner": row["OwnerRef"],
                    "kind": row["Kind"],
                    "version": row["VersionNo"],
                    "secret_id": str(row["SecretId"]).lower(),
                },
                row["Nonce"],
                row["Ciphertext"],
            )
        for row in rows(mapped, "SELECT * FROM crm_channels2.SecretVersion"):
            owner = next(n for n, col in OWNERS.items() if row[col] is not None)
            unseal(
                secret_key,
                binding(
                    parent,
                    owner,
                    str(row[OWNERS[owner]]),
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
            "UPDATE crm_access.Factor SET LastStep=CASE WHEN LastStep<? THEN ? ELSE LastStep END,PendingSecretId=NULL,SetupId=NULL,SetupSessionId=NULL,SetupExpiresAt=NULL",
            floor,
            floor,
        )
        mapped.execute(
            "UPDATE crm_channels2.OAuthSession SET Status=CASE WHEN Status='exchanging' THEN 'uncertain' ELSE 'cancelled' END,ClaimId=NULL,ClaimUntil=NULL,CompletedAt=SYSUTCDATETIME() WHERE Status IN('pending','exchanging','assets_ready')"
        )
        if recovering:
            mapped.execute(
                "UPDATE crm_agents5.Request SET State='uncertain',ErrorCode='native_restore_requires_review',LeaseId=NULL,LeaseUntil=NULL WHERE State='running'"
            )
        lineage = list(parent.ticket.get("workspace_lineage", [])) + [
            {
                "source_database": parent.connection["database"],
                "backup_uuid": checkpoint["backup_uuid"],
            }
        ]
        agents_lineage = (
            list(parent.ticket.get("agents_lineage", []))
            + [
                {
                    "source_database": parent.connection["database"],
                    "backup_uuid": checkpoint["backup_uuid"],
                }
            ]
            if recovering
            else []
        )
        catalog = metadata(c)
        ticket = dict(
            parent.ticket,
            version=policy.VERSION,
            scope="isolated_institutional_agents",
            identity=actual,
            sid=sid,
            agents_release_sha256=approved,
            agents_parent_history_sha256=history,
            agents_history_sha256=policy.history_digest(c),
            agents_migration_origin=parent.ticket.get("agents_migration_origin")
            if recovering
            else name,
            agents_lineage=agents_lineage,
            workspace_lineage=lineage,
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
    with transaction(load(directory), anonymous=True):
        pass
    save(
        WORK / (label + "-profile.json"),
        {
            "database": name,
            "directory": str(directory),
            "identity": actual,
            "native_restore": native,
            "migration": result,
        },
    )
    access = (
        read(WORK / "fixture-access.json")
        if recovering
        else read(PARENT / "final-access.json")
    )
    save(WORK / (label + "-access.json"), dict(access, profile=str(directory)))
    print(
        json.dumps(
            {"prepared": label, "database": name, "tables": 150, "TLS_verified": True}
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["capture", "fixture", "final"])
    action = parser.parse_args().action
    capture() if action == "capture" else prepare(action)
