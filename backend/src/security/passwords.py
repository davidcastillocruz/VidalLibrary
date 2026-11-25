import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Length allowed for a password: no composition rules (uppercase, symbols...), only length, as NIST recommends.
# The maximum stops a huge password from keeping the server busy hashing it
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128

# Argon2id with the library's defaults (RFC 9106). Raising them later is safe:
# old hashes keep working and password_needs_rehash() says when to replace them
_hasher = PasswordHasher()

# Hash of a password nobody knows, checked when the email has no account: a login with an unknown email
# takes as long as one with a wrong password, so the response time doesn't reveal which emails have an account
_UNKNOWN_USER_HASH = _hasher.hash("vidal-library-unknown-user")


# Hashing takes tens of milliseconds of CPU: it runs in a thread so the server keeps answering other requests
async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hasher.hash, password)


# True only when the password matches. password_hash is None when the email has no account:
# the check still runs, against _UNKNOWN_USER_HASH, and answers False
async def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        matches = await asyncio.to_thread(_hasher.verify, password_hash or _UNKNOWN_USER_HASH, password)
    except (VerificationError, InvalidHashError):
        # Wrong password (VerifyMismatchError is a VerificationError) or a stored value that isn't an Argon2 hash
        return False
    return matches and bool(password_hash)


# True when the hash was made with older parameters than the current ones:
# after a successful login, hash the password again and save the new hash
def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)
