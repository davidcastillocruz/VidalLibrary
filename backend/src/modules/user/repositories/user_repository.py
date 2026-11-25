import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.models.user_model import User, UserRole

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back


# The email must come lowercased, as it is saved (the schemas lowercase it)
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


# The user of an id, None if there is none
async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


# Saves a new hash of the password: a stronger one after a login, or the one chosen from an email
async def set_password_hash(db: AsyncSession, user_id: uuid.UUID, password_hash: str) -> None:
    await db.execute(update(User).where(User.id == user_id).values(password_hash=password_hash))


# New account without a password: its owner chooses it from the invitation. The email must come lowercased.
# The flush gives it its id, and a repeated email fails here
async def create_user(db: AsyncSession, email: str, name: str, role: UserRole) -> User:
    user = User(email=email, name=name, role=role)
    db.add(user)
    await db.flush()
    return user
