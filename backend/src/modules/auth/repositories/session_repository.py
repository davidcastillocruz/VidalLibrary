import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.user.models.user_model import User
from src.security.cookies import SESSION_DURATION

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back


# Valid session of the token with its user: not revoked and not expired. None if there is none
async def get_valid_session(db: AsyncSession, token_hash: str) -> tuple[AuthSession, User] | None:
    query = (
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > func.now(),
        )
    )
    row = (await db.execute(query)).first()
    return (row[0], row[1]) if row else None


# Last time the session was used
async def mark_session_used(db: AsyncSession, session_id: uuid.UUID) -> None:
    await db.execute(update(AuthSession).where(AuthSession.id == session_id).values(last_used_at=func.now()))


# New session of the user, valid for SESSION_DURATION. Only the hash of its token is saved
async def create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    token_hash: str,
    user_agent: str | None,
    ip: str,
) -> None:
    session = AuthSession(
        user_id=user_id,
        token_hash=token_hash,
        user_agent=user_agent,
        ip=ip,
        expires_at=datetime.now(UTC) + SESSION_DURATION,
    )
    db.add(session)


# Closes one session, the one of a sign-out
async def revoke_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    await db.execute(update(AuthSession).where(AuthSession.id == session_id).values(revoked_at=func.now()))
