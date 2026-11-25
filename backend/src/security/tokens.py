import hashlib
import secrets
from datetime import timedelta

# 32 random bytes: 256 bits, impossible to guess. URL-safe base64 gives 43 characters,
# usable as they are in a cookie and in the link of an email
TOKEN_BYTES = 32

# A link to choose a new password expires 30 minutes after it is sent. An invitation lasts a week: a new account
# doesn't always read its email the same day
PASSWORD_RESET_DURATION = timedelta(minutes=30)
INVITATION_DURATION = timedelta(days=7)


# Random token for a cookie or an email link. It only goes to the user, never to the database
def generate_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


# What the database keeps instead of the token: if the table leaks, its hashes can't be used to sign in.
# SHA-256 without salt is enough here (unlike passwords): the token is random and long, there is nothing to brute-force,
# and the same token must always give the same hash so it can be looked up by its unique index
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# A new token and its hash: the token goes to the user, the hash to the database
def new_token() -> tuple[str, str]:
    token = generate_token()
    return token, hash_token(token)

