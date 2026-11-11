"""Explicit P11 native-copy issuance; never run by application startup."""

import base64
import hashlib
import secrets
import time
from pathlib import Path
from uuid import uuid4

from app.es_schema_profile import journal_digest
from app.institutional import learning_policy
from app.institutional import operations_policy as policy
from app.institutional.spanish import RIGHTS, load, qualified_shape, transaction
from app.institutional.spanish_bindings import Cursor
from app.parity_channels.catalog import metadata
from app.parity_channels.policy import COLUMNS
from app.sql_profile import SqlProfileStore
from tools.es_schema_migrate_v2 import identity
from tools.foundation_snapshot import quote_name as q
from tools.foundation_snapshot import sha
from tools.p2_es_recovery import restore
from tools.p10_learning_recovery import backup as parent_backup
from tools.rehearse_foundation import literal
from tools.rehearse_p2_spanish import admin, read, save

WORK = Path("/var/lib/cbn-p2/p11-es-v1")
PARENT = Path("/var/lib/cbn-p2/p10-es-v1")


def source():
    # The earlier final-runtime was a rejected prototype. Only final-v2 is accepted.
    return load(Path(read(PARENT / "final-v2-profile.json")["directory"]))


def capture():
    if (WORK / "checkpoint.json").exists():
        raise ValueError("P11ES_fresh_checkpoint_required")
    parent = source()
    with transaction(parent, anonymous=True):
        pass
    with admin(parent.connection["database"]) as connection:
        checkpoint = parent_backup(connection, parent.ticket["identity"])
    save(WORK / "checkpoint.json", checkpoint)
    print("P11 source backup verified; no schema or academic changes.")


def authenticate_secrets(c, parent):
    from app.institutional.channel_secrets import OWNERS, binding
    from app.institutional.crypto import unseal
    from app.institutional.db import rows

    key = base64.b64decode(parent.review["secrets_key"], validate=True)
    counts = {}
    for table in [
        "crm_access.Secret",
        "crm_channels2.SecretVersion",
        "crm_ads9.Secret",
    ]:
        values = rows(c, "SELECT * FROM " + table)
        for row in values:
            if table == "crm_channels2.SecretVersion":
                owner = next(n for n, col in OWNERS.items() if row[col] is not None)
                aad = binding(
                    parent,
                    owner,
                    str(row[OWNERS[owner]]),
                    row["Kind"],
                    row["VersionNo"],
                    str(row["SecretId"]),
                )
            else:
                if (
                    table == "crm_ads9.Secret"
                    and row["KeyId"] != hashlib.sha256(key).hexdigest()[:32]
                ):
                    raise ValueError("P11ES_secret_key_binding")
                aad = dict(
                    institution=parent.ticket["context"][0][1],
                    scope="ads9" if table == "crm_ads9.Secret" else row["Scope"],
                    owner=str(row["AccountId"]).lower()
                    if table == "crm_ads9.Secret"
                    else row["OwnerRef"],
                    kind=row["Kind"],
                    version=row["VersionNo"],
                    secret_id=str(row["SecretId"]).lower(),
                )
            unseal(key, aad, row["Nonce"], row["Ciphertext"])
        counts[table] = len(values)
    return counts


def quarantine(c):
    """Invalidate copied authority; never replay uncertain provider effects."""
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
        c.execute(
            "UPDATE crm_access."
            + table
            + " SET "
            + field
            + "=ISNULL("
            + field
            + ",SYSUTCDATETIME())"
        )
    c.execute(
        "UPDATE crm_access.Factor SET LastStep=CASE WHEN LastStep<? THEN ? ELSE LastStep END,PendingSecretId=NULL,SetupId=NULL,SetupSessionId=NULL,SetupExpiresAt=NULL",
        floor,
        floor,
    )
    c.execute(
        "UPDATE crm_channels2.OAuthSession SET Status=CASE WHEN Status='exchanging' THEN 'uncertain' ELSE 'cancelled' END,ClaimId=NULL,ClaimUntil=NULL,CompletedAt=SYSUTCDATETIME() WHERE Status IN('pending','exchanging','assets_ready')"
    )
    c.execute(
        "UPDATE crm_agents5.Request SET State='uncertain',ErrorCode='native_restore_requires_review',LeaseId=NULL,LeaseUntil=NULL WHERE State='running'"
    )
    c.execute(
        "UPDATE crm_broadcast7.Campaign SET State='paused',Revision=Revision+1,Epoch=Epoch+1,ActorId=NULL,ActorAuthVersion=NULL,ActorSessionId=NULL,ApprovedAt=NULL WHERE State IN('running','scheduled')"
    )
    c.execute(
        "UPDATE crm_broadcast7.Recipient SET State='cancelled',LastError='native_restore_requires_review' WHERE State='prepared'"
    )
    c.execute(
        "UPDATE crm_campaign8.Record SET State='paused',Epoch=Epoch+1,Revision=Revision+1,ActorId=NULL,ActorAuthVersion=NULL,ActorSessionId=NULL,ApprovedAt=NULL WHERE Kind IN('campaign','flow','trigger') AND State='active'"
    )
    c.execute(
        "UPDATE crm_campaign8.Enrollment SET State='paused',LastReason='native_restore_requires_review' WHERE State IN('waiting','queued')"
    )
    c.execute(
        "UPDATE crm_channels2.SendJob SET State=CASE WHEN State='sending' THEN 'uncertain' ELSE 'cancelled' END,LastErrorCode='native_restore_requires_review',LeaseId=NULL,LeaseUntil=NULL WHERE State IN('queued','sending')"
    )
    c.execute(
        "UPDATE crm_channels2.ProviderOperation SET Status=CASE WHEN Status='running' THEN 'uncertain' ELSE 'failed' END,ResultCode='native_restore_requires_review',LeaseId=NULL,LeaseUntil=NULL WHERE Status IN('pending','running')"
    )
    c.execute(
        "UPDATE crm_ads9.Account SET State='paused',Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE State='connected'"
    )
    c.execute(
        "UPDATE crm_learning10.Deployment SET State='paused',Revision=Revision+1 WHERE State<>'paused'"
    )
    return floor


def prepare(label="fixture", *, checkpoint=None, recovering_from=None, access=None):
    WORK.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        not label.replace("-", "").isalnum()
        or (WORK / (label + "-profile.json")).exists()
    ):
        raise ValueError("P11ES_fresh_label_required")
    parent = recovering_from or source()
    if recovering_from and access is None:
        raise ValueError("P11ES_recovery_access_binding_required")
    if parent.ticket["version"] not in {learning_policy.VERSION, policy.VERSION}:
        raise ValueError("P11ES_parent_profile_required")
    checkpoint = checkpoint or read(WORK / "checkpoint.json")
    if checkpoint["source"] != parent.ticket["identity"]:
        raise ValueError("P11ES_checkpoint_binding")
    name = (
        "CBN_P11ES_"
        + ("RECOVERY" if recovering_from else "TRIAL")
        + "_20261028_"
        + uuid4().hex[:8]
    )
    mapping = policy.layout()
    with admin("master") as connection:
        native = restore(
            connection,
            checkpoint,
            name,
            restricted=True,
            target_pattern=policy.TARGET,
            allowed_tables=set(mapping["tables"].values())
            | set(mapping["academic_tables"]),
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
    with admin(name) as connection:
        c = connection.cursor()
        actual = identity(c)
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
        for logical, names in policy.columns(COLUMNS).items():
            c.execute(
                "GRANT SELECT ON OBJECT::"
                + mapping["tables"][logical]
                + "("
                + ",".join(map(q, names))
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
        secrets_checked = authenticate_secrets(mapped, parent)
        floor = quarantine(mapped)
        lineage = list(parent.ticket.get("operations_lineage", [])) + [
            {
                "source_database": parent.connection["database"],
                "backup_uuid": checkpoint["backup_uuid"],
            }
        ]
        workspace_lineage = list(parent.ticket.get("workspace_lineage", [])) + [
            lineage[-1]
        ]
        catalog = metadata(c)
        ticket = dict(
            parent.ticket,
            version=policy.VERSION,
            scope="isolated_institutional_operations",
            identity=actual,
            sid=sid,
            operations_release_sha256=policy.release(),
            operations_origin=parent.ticket.get(
                "operations_origin", parent.connection["database"]
            ),
            operations_lineage=lineage,
            workspace_lineage=workspace_lineage,
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
            "secrets_checked": secrets_checked,
            "new_domain_DDL": False,
        },
    )
    access = access or read(PARENT / "final-v2-access.json")
    save(WORK / (label + "-access.json"), dict(access, profile=str(directory)))
    print(
        f"P11 {label} prepared: own profile, 185 tables, TLS verified, copied authority paused."
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["capture", "fixture", "final"])
    action = parser.parse_args().action
    capture() if action == "capture" else prepare(action)
