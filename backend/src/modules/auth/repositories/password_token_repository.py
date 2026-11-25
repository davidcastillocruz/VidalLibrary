import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models.password_token_model import PasswordToken, PasswordTokenPurpose
from src.modules.user.models.user_model import User
from src.security.tokens import INVITATION_DURATION, PASSWORD_RESET_DURATION

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back

# How long a link lasts, by its purpose
DURATIONS = {
    PasswordTokenPurpose.INVITATION: INVITATION_DURATION,
    PasswordTokenPurpose.PASSWORD_RESET: PASSWORD_RESET_DURATION,
}


# Revokes the pending links of the user, whatever their purpose: only the newest one works
async def revoke_password_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    query = (
        update(PasswordToken)
        .where(
            PasswordToken.user_id == user_id,
            PasswordToken.used_at.is_(None),
            PasswordToken.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )
    await db.execute(query)


# A link of the user for this purpose. expires_at is computed here and not with func.now(): the object keeps a real
# datetime after the commit
async def create_password_token(
    db: AsyncSession,
    user_id: uuid.UUID,
    purpose: PasswordTokenPurpose,
    token_hash: str,
) -> PasswordToken:
    password_token = PasswordToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + DURATIONS[purpose],
    )
    db.add(password_token)
    return password_token


# The link with its user if it can still be used: not used, not revoked and not expired. None otherwise, without
# telling why. The link is locked until the commit (FOR UPDATE, not its user): if it is opened twice at once, the second
# request waits for the first one and then finds it used, instead of doing it twice
async def get_valid_password_token_with_user(db: AsyncSession, token_hash: str) -> tuple[PasswordToken, User] | None:
    query = (
        select(PasswordToken, User)
        .join(User, User.id == PasswordToken.user_id)
        .where(
            PasswordToken.token_hash == token_hash,
            PasswordToken.used_at.is_(None),
            PasswordToken.revoked_at.is_(None),
            PasswordToken.expires_at > func.now(),
        )
        .with_for_update(of=PasswordToken)
    )
    row = (await db.execute(query)).first()
    return (row[0], row[1]) if row else None


# Spends the link: it can't be opened again
async def use_password_token(db: AsyncSession, password_token_id: uuid.UUID) -> None:
    await db.execute(update(PasswordToken).where(PasswordToken.id == password_token_id).values(used_at=func.now()))
