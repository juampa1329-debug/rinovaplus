"""SQL-owned configuration and write-only authenticated credential encryption."""

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path

import pyodbc
from fastapi import HTTPException

from app.sql_workspace import connection_string, verify_target

CHANNELS = ("whatsapp", "instagram", "messenger", "facebook", "tiktok")
SECRET_KINDS = ("accessToken", "appSecret", "verifyToken", "refreshToken")


def document(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class ChannelStore:
    def __init__(self, settings):
        self.settings = settings
        if settings.mode == "local_channels":
            self.key_path = Path(settings.channels_key_path)
            return
        self.key_path = (
            Path(
                os.environ.get(
                    "CRM_AI_STATE_DIR",
                    str(Path(__file__).resolve().parents[4] / ".local"),
                )
            )
            / "channels-aes256.key"
        )

    @contextmanager
    def transaction(self):
        if self.settings.mode == "local_channels":
            from app.channels_contract import transaction

            with transaction(self.settings) as cursor:
                yield cursor
            return
        if self.settings.mode != "local_sql_copy":
            raise HTTPException(503, "local_sql_copy_required")
        connection = None
        try:
            connection = pyodbc.connect(
                connection_string(self.settings), timeout=1, autocommit=False
            )
            connection.timeout = 1
            cursor = connection.cursor()
            cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 500;")
            verify_target(cursor, self.settings)
            marker = cursor.execute(
                "SELECT CONVERT(nvarchar(80),value) FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_channels') AND name=N'crm_channels.contract'"
            ).fetchone()
            if not marker or marker[0] != "CRM-channels-v1":
                raise HTTPException(503, "channels_schema_required")
            yield cursor
            connection.commit()
        except pyodbc.Error:
            if connection:
                connection.rollback()
            raise HTTPException(503, "channels_storage_unavailable") from None
        except BaseException:
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()

    def key(self, cursor):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if self.settings.mode == "local_channels":
            try:
                value = self.key_path.read_bytes()
                if (
                    len(value) == 32
                    and hashlib.sha256(value).hexdigest()
                    == self.settings.channels_key_sha256
                ):
                    return value
            except OSError:
                pass
            raise HTTPException(503, "channel_encryption_key_unavailable")
        if not self.key_path.exists():
            if cursor.execute(
                "SELECT TOP(1) KeyId FROM crm_channels.Credential"
            ).fetchone():
                raise HTTPException(503, "channel_encryption_key_unavailable")
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(
                    self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(AESGCM.generate_key(bit_length=256))
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError:
                pass
        value = self.key_path.read_bytes()
        if len(value) != 32:
            raise HTTPException(503, "channel_encryption_key_unavailable")
        return value

    def write_secret(self, cursor, channel, kind, value):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = self.key(cursor)
        nonce = os.urandom(12)
        encrypted = AESGCM(key).encrypt(
            nonce, value.encode(), f"crm_channels:{channel}:{kind}:v1".encode()
        )
        key_id = hashlib.sha256(key).hexdigest()[:32]
        cursor.execute(
            "DELETE crm_channels.Credential WHERE Channel=? AND Kind=?", channel, kind
        )
        cursor.execute(
            "INSERT crm_channels.Credential(Channel,Kind,KeyId,Nonce,Ciphertext) VALUES(?,?,?,?,?)",
            channel,
            kind,
            key_id,
            nonce,
            encrypted,
        )

    def secrets(self, cursor, channel):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        rows = cursor.execute(
            "SELECT Kind,KeyId,Nonce,Ciphertext FROM crm_channels.Credential WHERE Channel=?",
            channel,
        ).fetchall()
        if not rows:
            return {}
        key = self.key(cursor)
        key_id = hashlib.sha256(key).hexdigest()[:32]
        if any(r[1] != key_id for r in rows):
            raise HTTPException(503, "channel_encryption_key_unavailable")
        try:
            return {
                r[0]: AESGCM(key)
                .decrypt(
                    bytes(r[2]),
                    bytes(r[3]),
                    f"crm_channels:{channel}:{r[0]}:v1".encode(),
                )
                .decode()
                for r in rows
            }
        except Exception:
            raise HTTPException(503, "channel_credential_unavailable") from None

    def get(self, cursor, channel, private=False):
        row = cursor.execute(
            "SELECT Configuration,State,Revision,Capabilities,LastError,VerifiedAt FROM crm_channels.Account WHERE Channel=?",
            channel,
        ).fetchone()
        result = {
            "channel": channel,
            "configuration": {},
            "state": "unconfigured",
            "revision": 0,
            "capabilities": {},
            "lastError": None,
            "verifiedAt": None,
            "credentials": [],
        }
        if row:
            result.update(
                configuration=json.loads(row[0]),
                state=row[1],
                revision=row[2],
                capabilities=json.loads(row[3]),
                lastError=row[4],
                verifiedAt=row[5].isoformat() + "Z" if row[5] else None,
            )
            result["credentials"] = [
                r[0]
                for r in cursor.execute(
                    "SELECT Kind FROM crm_channels.Credential WHERE Channel=?", channel
                ).fetchall()
            ]
        if private:
            result["secrets"] = self.secrets(cursor, channel)
        return result

    def save_configuration(self, cursor, channel, body):
        store = self
        cursor.execute(
            "DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource=?,@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=500; IF @r<0 THROW 51000,'Channel busy',1;",
            "crm.channels.config." + channel,
        )
        current = store.get(cursor, channel)
        if current["revision"] != body.revision:
            raise HTTPException(409, "channel_configuration_changed")
        config = body.configuration.model_dump()
        identity_fields = (
            "appId",
            "wabaId",
            "phoneNumberId",
            "pageId",
            "accountId",
            "instagramLogin",
        )
        if current["revision"] and any(
            config.get(k) != current["configuration"].get(k) for k in identity_fields
        ):
            cursor.execute(
                "DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource=N'crm.local.commit',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=500; IF @r<0 THROW 51000,'Workspace busy',1;"
            )
            linked = cursor.execute(
                "SELECT CASE WHEN EXISTS(SELECT 1 FROM crm_channels.ExternalIdentity WHERE Channel=?) OR EXISTS(SELECT 1 FROM crm_channels.social_comments WHERE Channel=?) OR EXISTS(SELECT 1 FROM crm_channels.outbound_queue WHERE Channel=?) OR EXISTS(SELECT 1 FROM crm_channels.webhook_events e CROSS APPLY OPENJSON(e.Payload,'$.channels') c WHERE c.value=?) THEN 1 ELSE 0 END",
                channel,
                channel,
                channel,
                channel,
            ).fetchone()[0]
            if linked:
                raise HTTPException(409, "channel_identity_has_history")
        if current["revision"]:
            cursor.execute(
                "UPDATE crm_channels.Account SET Configuration=?,State='configured',Revision=Revision+1,Capabilities='{}',VerifiedAt=NULL,LastError=NULL,UpdatedAt=SYSUTCDATETIME() WHERE Channel=?",
                document(config),
                channel,
            )
        else:
            cursor.execute(
                "INSERT crm_channels.Account(Channel,Configuration) VALUES(?,?)",
                channel,
                document(config),
            )
        for kind in SECRET_KINDS:
            value = getattr(body, kind).strip()
            if value:
                store.write_secret(cursor, channel, kind, value)
        cursor.execute(
            "INSERT crm_channels.Audit(Channel,Action) VALUES(?,'configuration_saved')",
            channel,
        )
        return store.get(cursor, channel)
