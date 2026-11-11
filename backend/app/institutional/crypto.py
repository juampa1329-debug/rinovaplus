"""Standard password KDF, opaque credentials, authenticated secret encryption."""

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
import unicodedata

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERATIONS = 1_000_000


def password_bytes(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
        raise ValueError("invalid_password")
    return unicodedata.normalize("NFC", value).encode("utf-8")


def password_hash(value, *, enforce=True):
    raw = password_bytes(value)
    if enforce and (
        len(value) < 15
        or value.casefold()
        in {
            "passwordpassword",
            "123456789012345",
            "contraseñacontraseña",
            "password123456789",
            "qwertyuiopasdfgh",
            "administrador123",
        }
    ):
        raise ValueError("password_policy")
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", raw, salt, ITERATIONS)
    return f"pbkdf2-sha256${ITERATIONS}${salt.hex()}${derived.hex()}"


def password_matches(value, encoded):
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2-sha256" or int(iterations) != ITERATIONS:
            return False
        salt, expected = bytes.fromhex(salt), bytes.fromhex(expected)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password_bytes(value), salt, ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        return False


def token():
    return secrets.token_urlsafe(32)


def token_hash(value):
    return hashlib.sha256(value.encode("utf-8")).digest()


def canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def request_digest(key, value):
    return hmac.digest(key, canonical(value), "sha256")


def seal(key, owner, value):
    nonce = secrets.token_bytes(12)
    return nonce, AESGCM(key).encrypt(nonce, value.encode("utf-8"), canonical(owner))


def unseal(key, owner, nonce, ciphertext):
    return (
        AESGCM(key)
        .decrypt(bytes(nonce), bytes(ciphertext), canonical(owner))
        .decode("utf-8")
    )


def totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_code(secret, step):
    padded = secret + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded, casefold=False)
    result = hmac.digest(key, struct.pack(">Q", step), "sha1")
    offset = result[-1] & 15
    number = struct.unpack(">I", result[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 1_000_000).zfill(6)


def matching_step(secret, code, *, last=-1, now=None):
    if (
        not isinstance(code, str)
        or len(code) != 6
        or not code.isascii()
        or not code.isdigit()
    ):
        return None
    current = int(time.time() if now is None else now) // 30
    for step in (current, current - 1, current + 1):
        if step > last and hmac.compare_digest(totp_code(secret, step), code):
            return step
    return None


def recovery_codes():
    return [secrets.token_hex(16) for _ in range(8)]
