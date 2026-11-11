"""Atomic, current-Windows-user DPAPI storage for the local AI bench."""

import ctypes
import os
import tempfile
import threading
from pathlib import Path

from pydantic import Field, SecretStr, field_validator

from app.modules.ai.domain.models import PROVIDERS, StrictModel
from app.modules.ai.infrastructure.providers import AiError


class CredentialRequest(StrictModel):
    revision: int = Field(ge=0)
    api_key: SecretStr = Field(min_length=1, max_length=4096)

    @field_validator("api_key")
    @classmethod
    def valid_key(cls, value: SecretStr):
        text = value.get_secret_value()
        if any(ord(char) < 33 or ord(char) > 126 for char in text):
            raise ValueError("invalid_key")
        return value


class OutboundRequest(StrictModel):
    revision: int = Field(ge=0)
    enabled: bool


class CredentialDeleteRequest(StrictModel):
    revision: int = Field(ge=0)


class Credentials(StrictModel):
    revision: int = Field(default=0, ge=0)
    keys: dict[str, SecretStr] = Field(default_factory=dict)
    outbound: bool | None = None

    @field_validator("keys")
    @classmethod
    def valid_keys(cls, values):
        for provider, key in values.items():
            if provider not in PROVIDERS:
                raise ValueError("invalid_provider")
            CredentialRequest(revision=0, api_key=key)
        return values


class WindowsProtector:
    def transform(self, value: bytes, *, decrypt: bool) -> bytes:
        try:
            return self._transform(value, decrypt=decrypt)
        except OSError:
            raise AiError("credential_storage_unavailable", 503) from None

    def _transform(self, value: bytes, *, decrypt: bool) -> bytes:
        if os.name != "nt":
            raise AiError("credential_storage_unsupported", 503)
        from ctypes import wintypes

        class Blob(ctypes.Structure):
            _fields_ = [
                ("size", wintypes.DWORD),
                ("data", ctypes.POINTER(ctypes.c_char)),
            ]

        crypt = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
        operation.argtypes = [
            ctypes.POINTER(Blob),
            ctypes.c_void_p,
            ctypes.POINTER(Blob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(Blob),
        ]
        operation.restype = wintypes.BOOL
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        buffer = ctypes.create_string_buffer(value)
        source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
        output = Blob()
        try:
            if not operation(
                ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)
            ):
                raise AiError("credential_storage_unavailable", 503)
            return ctypes.string_at(output.data, output.size)
        finally:
            ctypes.memset(buffer, 0, len(buffer))
            if output.data:
                ctypes.memset(output.data, 0, output.size)
                kernel.LocalFree(output.data)


class CredentialRepository:
    storage_backend = "windows_dpapi"

    @property
    def available(self):
        return os.name == "nt"

    def __init__(self, path: Path, protector=None):
        self.path = path
        self.protector = protector or WindowsProtector()
        self.lock = threading.Lock()

    def read(self) -> Credentials:
        try:
            if not self.path.exists():
                return Credentials()
            if self.path.stat().st_size > 64000:
                raise ValueError()
            return Credentials.model_validate_json(
                self.protector.transform(self.path.read_bytes(), decrypt=True)
            )
        except (OSError, ValueError):
            raise AiError("credential_storage_unavailable", 503) from None

    def update(
        self, revision: int, *, provider=None, key=None, outbound=None, remove=False
    ):
        with self.lock:
            current = self.read()
            if current.revision != revision:
                raise AiError("credential_revision_conflict", 409)
            if provider is not None:
                if remove:
                    current.keys.pop(provider, None)
                else:
                    current.keys[provider] = key
            if outbound is not None:
                current.outbound = outbound
            current.revision += 1
            # SecretStr serialization deliberately redacts by default. Only the
            # buffer entering DPAPI contains plaintext; disk receives ciphertext.
            import json

            payload = json.dumps(
                {
                    "revision": current.revision,
                    "keys": {
                        name: secret.get_secret_value()
                        for name, secret in current.keys.items()
                    },
                    "outbound": current.outbound,
                }
            ).encode("utf-8")
            encrypted = self.protector.transform(payload, decrypt=False)
            temporary = None
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    dir=self.path.parent, delete=False
                ) as file:
                    temporary = file.name
                    file.write(encrypted)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, self.path)
            except OSError:
                raise AiError("credential_storage_unavailable", 503) from None
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
            return current
