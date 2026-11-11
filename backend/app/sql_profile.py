"""Private, atomic SQL profile storage; importing this module performs no IO."""

import json
import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class ProfileUnavailable(Exception):
    pass


class SqlProfileStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self.path = directory / "profile.enc"
        self.key_path = directory / "profile.key"

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            key = self.key_path.read_bytes()
            data = self.path.read_bytes()
            if len(key) != 32 or len(data) > 64000:
                raise ValueError()
            result = json.loads(
                AESGCM(key).decrypt(data[:12], data[12:], b"CBN-SQL-v1")
            )
            if (
                not isinstance(result, dict)
                or type(result.get("revision")) is not int
                or result["revision"] < 1
                or not isinstance(result.get("connection"), dict)
                or not isinstance(result.get("review"), dict)
            ):
                raise ValueError()
            connection = result["connection"]
            if (
                any(
                    not isinstance(connection.get(k), str)
                    for k in (
                        "server",
                        "username",
                        "password",
                        "certificate_hostname",
                        "database",
                    )
                )
                or type(connection.get("port")) is not int
                or not 1 <= connection["port"] <= 65535
            ):
                raise ValueError()
            return result
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise ProfileUnavailable() from error
        except Exception as error:
            # Includes an authentication-tag failure; never recreate a missing key.
            raise ProfileUnavailable() from error

    def save(self, profile: dict) -> None:
        temporary = None
        try:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            if not self.key_path.exists():
                if self.path.exists():
                    raise ProfileUnavailable()
                descriptor = os.open(
                    self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(AESGCM.generate_key(bit_length=256))
                    stream.flush()
                    os.fsync(stream.fileno())
            key = self.key_path.read_bytes()
            if len(key) != 32:
                raise ProfileUnavailable()
            nonce = os.urandom(12)
            data = nonce + AESGCM(key).encrypt(
                nonce, json.dumps(profile, ensure_ascii=True).encode(), b"CBN-SQL-v1"
            )
            descriptor, temporary = tempfile.mkstemp(dir=self.directory, prefix=".sql-")
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            temporary = None
        except OSError as error:
            raise ProfileUnavailable() from error
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)
