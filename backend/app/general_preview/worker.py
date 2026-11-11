"""Durable local-only operations worker; no provider, URL or arbitrary tool input."""

import hashlib
import os
import time
import uuid
from pathlib import Path

from app.general_preview.store import load, transaction
from app.parity_channels.policy import canonical, require

ACTION = "c13_local_recovery"
REQUEST = hashlib.sha256(
    canonical({"action": ACTION, "effect": "local-marker-v1"})
).digest()


def seed(settings, operation):
    operation = str(uuid.UUID(operation))
    institution = settings.ticket["context"][0][1]
    application = str(uuid.uuid5(uuid.UUID(institution), "C13 isolated local worker"))
    with transaction(settings, True) as cursor:
        if not cursor.execute(
            (
                "SELECT 1 FROM crm_channels2.Application WHERE "
                "InstitutionId=? AND ApplicationId=?"
            ),
            institution,
            application,
        ).fetchone():
            cursor.execute(
                (
                    "INSERT crm_channels2.Application(InstitutionId,App"
                    "licationId,Provider,ClientId,ApiVersion,IssuerProf"
                    "ile,RedirectUri,EgressProfile,State,CreatedAt,Upda"
                    "tedAt) VALUES(?,?,'meta','c13-local-worker','','me"
                    "ta_whatsapp','','disabled-"
                    "c13','draft',SYSUTCDATETIME(),SYSUTCDATETIME())"
                ),
                institution,
                application,
            )
        prior = cursor.execute(
            (
                "SELECT RequestDigest FROM "
                "crm_channels2.ProviderOperation WHERE "
                "InstitutionId=? AND OperationId=?"
            ),
            institution,
            operation,
        ).fetchone()
        if prior:
            require(bytes(prior[0]) == REQUEST, "C13_job_conflict")
            return "noop"
        cursor.execute(
            (
                "INSERT crm_channels2.ProviderOperation(Institution"
                "Id,OperationId,ApplicationId,ActorRef,Action,Reque"
                "stDigest,Status,ResultMetadata,CreatedAt,EffectKey"
                ") VALUES(?,?,?,'local-drill:SQL-"
                "C13',?,?,'pending','{}',SYSUTCDATETIME(),?)"
            ),
            institution,
            operation,
            application,
            ACTION,
            REQUEST,
            hashlib.sha256(operation.encode()).digest(),
        )
    return "queued"


def pause(point, operation, directory):
    if os.environ.get("CBN_LOCAL_WORKER_PAUSE") != point:
        return
    marker = directory / ("paused-" + point + ".json")
    marker.write_bytes(canonical({"operation": operation, "point": point}))
    marker.chmod(0o600)
    while True:
        time.sleep(0.2)


def effect(directory, operation, digest):
    require(digest == REQUEST, "C13_local_action_digest")
    path = directory / (str(uuid.UUID(operation)) + ".json")
    value = canonical(
        {
            "operation": str(uuid.UUID(operation)).lower(),
            "request": digest.hex(),
            "effect": "local-marker-v1",
        }
    )
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        require(path.read_bytes() == value, "C13_effect_evidence_mismatch")
        return False
    with os.fdopen(fd, "wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def tick(settings, directory):
    institution = settings.ticket["context"][0][1]
    lease = str(uuid.uuid4())
    with transaction(settings, True) as cursor:
        row = cursor.execute(
            (
                "SELECT TOP(1) "
                "OperationId,Status,RequestDigest,LeaseVersion FROM"
                " crm_channels2.ProviderOperation WHERE "
                "InstitutionId=? AND Action=? AND ActorRef='local-"
                "drill:SQL-C13' AND (Status='pending' OR "
                "(Status='uncertain' AND "
                "ResultCode='lease_expired') OR (Status='running' "
                "AND LeaseUntil<SYSUTCDATETIME())) ORDER BY "
                "CreatedAt,OperationId"
            ),
            institution,
            ACTION,
        ).fetchone()
        if not row:
            return None
        operation = str(row[0]).lower()
        previous = row[1]
        version = row[3] + 1
        digest = bytes(row[2])
        if previous == "running":
            cursor.execute(
                (
                    "UPDATE crm_channels2.ProviderOperation SET Status="
                    "'uncertain',ResultCode='lease_expired',LeaseId=NUL"
                    "L,LeaseUntil=NULL WHERE InstitutionId=? AND "
                    "OperationId=? AND LeaseVersion=?"
                ),
                institution,
                operation,
                row[3],
            )
            return "uncertain"
        cursor.execute(
            (
                "UPDATE crm_channels2.ProviderOperation SET Status="
                "'running',LeaseId=?,LeaseUntil=DATEADD(second,15,S"
                "YSUTCDATETIME()),LeaseVersion=?,Attempts=Attempts+"
                "1 WHERE InstitutionId=? AND OperationId=? AND "
                "LeaseVersion=?"
            ),
            lease,
            version,
            institution,
            operation,
            row[3],
        )
        require(cursor.rowcount == 1, "C13_worker_claim_conflict")
    pause("claim", operation, directory)
    try:
        created = effect(directory, operation, digest)
    except ValueError:
        with transaction(settings, True) as cursor:
            cursor.execute(
                (
                    "UPDATE crm_channels2.ProviderOperation SET Status="
                    "'uncertain',ResultCode='local_effect_evidence_mism"
                    "atch',LeaseUntil=DATEADD(day,1,SYSUTCDATETIME()) "
                    "WHERE InstitutionId=? AND OperationId=? AND "
                    "LeaseId=? AND LeaseVersion=?"
                ),
                institution,
                operation,
                lease,
                version,
            )
        return "uncertain_evidence"
    pause("effect", operation, directory)
    with transaction(settings, True) as cursor:
        # Expiry/fencing wins over a late worker even for a local adapter.
        cursor.execute(
            (
                "UPDATE crm_channels2.ProviderOperation SET Status="
                "?,ResultCode=?,ResultMetadata=?,CompletedAt=SYSUTC"
                "DATETIME(),LeaseId=NULL,LeaseUntil=NULL WHERE "
                "InstitutionId=? AND OperationId=? AND LeaseId=? "
                "AND LeaseVersion=? AND LeaseUntil>SYSUTCDATETIME()"
                " AND Status='running'"
            ),
            "reconciled" if previous == "uncertain" else "confirmed",
            "local_recovered" if previous == "uncertain" else "local_completed",
            canonical(
                {"scope": "local_marker_only", "effect_created": created}
            ).decode(),
            institution,
            operation,
            lease,
            version,
        )
        require(cursor.rowcount == 1, "C13_worker_lease_lost")
    return "reconciled" if previous == "uncertain" else "confirmed"


def main():
    settings = load(Path(os.environ["CRM_GENERAL_PROFILE_DIR"]))
    directory = Path(os.environ["CRM_AI_STATE_DIR"]) / "c13-local-operations"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    while True:
        tick(settings, directory)
        if os.environ.get("CBN_LOCAL_WORKER_ONCE") == "1":
            break
        time.sleep(1)


if __name__ == "__main__":
    main()
