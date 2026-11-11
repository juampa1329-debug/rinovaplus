"""Local SQL authority for AI settings and authenticated encrypted credentials."""

import hashlib
import os
from contextlib import contextmanager

import pyodbc
from pydantic import SecretStr

from app.modules.ai.domain.models import AiSettings, SaveSettings
from app.modules.ai.infrastructure.credentials import Credentials
from app.modules.ai.infrastructure.providers import AiError
from app.sql_workspace import connection_string, verify_target


class SqlAiStore:
    def __init__(self, settings, path):
        self.settings, self.path = settings, path

    @contextmanager
    def transaction(self, write=False):
        connection = None
        try:
            connection = pyodbc.connect(
                connection_string(self.settings), timeout=5, autocommit=False
            )
            connection.timeout = 10
            cursor = connection.cursor()
            cursor.execute("SET XACT_ABORT ON; SET LOCK_TIMEOUT 3000;")
            verify_target(cursor, self.settings)
            marker = cursor.execute(
                "SELECT CONVERT(nvarchar(80),value) FROM sys.extended_properties WHERE class=3 AND major_id=SCHEMA_ID(N'crm_ai') AND name=N'crm_ai.contract'"
            ).fetchone()
            if not marker or marker[0] != "CRM-ai-v1":
                raise AiError("ai_sql_schema_required", 503)
            row = cursor.execute(
                "DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource=N'crm.ai.settings',@LockMode=?,@LockOwner='Transaction',@LockTimeout=3000; SELECT @r",
                "Exclusive" if write else "Shared",
            ).fetchone()
            if not row or row[0] < 0:
                raise AiError("settings_storage_unavailable", 503)
            yield cursor
            connection.commit()
        except AiError:
            if connection:
                connection.rollback()
            raise
        except Exception:
            if connection:
                connection.rollback()
            raise AiError("settings_storage_unavailable", 503) from None
        finally:
            if connection:
                connection.close()

    def key(self, cursor):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key_path = self.path.parent / "ai-provider-aes256.key"
        if not key_path.exists():
            if cursor.execute("SELECT TOP(1) KeyId FROM crm_ai.Credential").fetchone():
                raise AiError("credential_storage_unavailable", 503)
            key_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(AESGCM.generate_key(bit_length=256))
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError:
                pass
        key = key_path.read_bytes()
        if len(key) != 32:
            raise AiError("credential_storage_unavailable", 503)
        if any(
            r[0] != hashlib.sha256(key).hexdigest()[:32]
            for r in cursor.execute(
                "SELECT DISTINCT KeyId FROM crm_ai.Credential"
            ).fetchall()
        ):
            raise AiError("credential_storage_unavailable", 503)
        return key


class SqlSettingsRepository:
    def __init__(self, store):
        self.store, self.path = store, store.path

    def read(self):
        with self.store.transaction() as cursor:
            row = cursor.execute(
                "SELECT Revision,Document FROM crm_ai.Configuration WHERE ConfigurationId=1"
            ).fetchone()
            if not row:
                raise AiError("ai_sql_schema_required", 503)
            return SaveSettings(
                revision=row[0], settings=AiSettings.model_validate_json(row[1])
            )

    def save(self, request):
        with self.store.transaction(True) as cursor:
            cursor.execute(
                "UPDATE crm_ai.Configuration SET Document=?,Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE ConfigurationId=1 AND Revision=?",
                request.settings.model_dump_json(),
                request.revision,
            )
            if cursor.rowcount != 1:
                raise AiError("settings_revision_conflict", 409)
            return SaveSettings(
                revision=request.revision + 1, settings=request.settings
            )


class SqlCredentialRepository:
    available = True
    storage_backend = "sql_server_aes256_gcm"

    def __init__(self, store):
        self.store, self.path = store, store.path.parent / "ai-provider-aes256.key"

    def read(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        with self.store.transaction() as cursor:
            row = cursor.execute(
                "SELECT Revision,Outbound FROM crm_ai.Connection WHERE ConnectionId=1"
            ).fetchone()
            if not row:
                raise AiError("credential_storage_unavailable", 503)
            rows = cursor.execute(
                "SELECT Provider,KeyId,Nonce,Ciphertext FROM crm_ai.Credential"
            ).fetchall()
            keys = {}
            if rows:
                key = self.store.key(cursor)
                key_id = hashlib.sha256(key).hexdigest()[:32]
                try:
                    for provider, stored_id, nonce, cipher in rows:
                        if stored_id != key_id:
                            raise ValueError()
                        keys[provider] = SecretStr(
                            AESGCM(key)
                            .decrypt(
                                bytes(nonce),
                                bytes(cipher),
                                f"crm_ai:credential:{provider}:v1".encode(),
                            )
                            .decode()
                        )
                except Exception:
                    raise AiError("credential_storage_unavailable", 503) from None
            return Credentials(revision=row[0], outbound=bool(row[1]), keys=keys)

    def update(self, revision, *, provider=None, key=None, outbound=None, remove=False):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        with self.store.transaction(True) as cursor:
            current = cursor.execute(
                "SELECT Revision FROM crm_ai.Connection WHERE ConnectionId=1"
            ).fetchone()
            if not current or current[0] != revision:
                raise AiError("credential_revision_conflict", 409)
            if provider is not None:
                master = self.store.key(cursor) if not remove else None
                cursor.execute("DELETE crm_ai.Credential WHERE Provider=?", provider)
                if not remove:
                    nonce = os.urandom(12)
                    cipher = AESGCM(master).encrypt(
                        nonce,
                        key.get_secret_value().encode(),
                        f"crm_ai:credential:{provider}:v1".encode(),
                    )
                    cursor.execute(
                        "INSERT crm_ai.Credential(Provider,KeyId,Nonce,Ciphertext) VALUES(?,?,?,?)",
                        provider,
                        hashlib.sha256(master).hexdigest()[:32],
                        nonce,
                        cipher,
                    )
            if outbound is None:
                cursor.execute(
                    "UPDATE crm_ai.Connection SET Revision=Revision+1,UpdatedAt=SYSUTCDATETIME() WHERE ConnectionId=1"
                )
            else:
                cursor.execute(
                    "UPDATE crm_ai.Connection SET Revision=Revision+1,Outbound=?,UpdatedAt=SYSUTCDATETIME() WHERE ConnectionId=1",
                    bool(outbound),
                )
        return self.read()
