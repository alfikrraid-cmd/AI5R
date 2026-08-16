"""MWO-LTSA-AUTH-001 -- password hashing.

Uses hashlib.scrypt (Python stdlib, RFC 7914) -- no new dependency,
never invented cryptography, per this MWO's own "use secure password
hashing from an appropriate already-installed dependency" /
"do not invent cryptography" rules. bcrypt/passlib are not installed
anywhere in this repository (confirmed before writing this module);
scrypt is the standard-library-native equivalent already available in
every Python 3.6+ interpreter this codebase runs on, requiring no new
requirements.txt entry.

Encoded format: "scrypt$n$r$p$<base64 salt>$<base64 hash>" -- a single
self-describing string, the same "store the whole recipe with the
hash" convention bcrypt/passlib use, so cost parameters can change in
the future without invalidating already-hashed passwords (old hashes
keep verifying against their own recorded n/r/p).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

_SCHEME = "scrypt"
_DEFAULT_N = 2**14  # CPU/memory cost -- interactive-login-appropriate, RFC 7914's own suggested minimum
_DEFAULT_R = 8
_DEFAULT_P = 1
_SALT_BYTES = 16
_DKLEN = 32


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password must not be empty")

    salt = os.urandom(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_DEFAULT_N, r=_DEFAULT_R, p=_DEFAULT_P, dklen=_DKLEN
    )
    return "$".join(
        [
            _SCHEME,
            str(_DEFAULT_N),
            str(_DEFAULT_R),
            str(_DEFAULT_P),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(derived).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    """Never raises -- a malformed/foreign encoded hash is a verification
    failure, not a 500. Constant-time comparison (hmac.compare_digest)
    so hash equality checking itself cannot leak timing information."""
    try:
        scheme, n, r, p, salt_b64, hash_b64 = encoded.split("$")
        if scheme != _SCHEME:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        candidate = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate, expected)


__all__ = ["hash_password", "verify_password"]
