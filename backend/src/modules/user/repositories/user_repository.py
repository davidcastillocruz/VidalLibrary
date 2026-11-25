import uuid

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.user.models.user_model import User, UserRole
from src.modules.user.schemas.user_schemas import AdminUserQuery

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back


# The email must come lowercased, as it is saved (the schemas lowercase it)
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


# The user of an id, None if there is none.
# lock: its row locked until the commit (FOR NO KEY UPDATE) and read again even if this session already had it: the
# reservations of one reader wait for each other, and each one counts the loans the previous one left
async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID, lock: bool) -> User | None:
    return await db.get(User, user_id, with_for_update={"key_share": True} if lock else None, populate_existing=lock)


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


# One page of the accounts that match the query, by name, and how many match in all
async def get_users(db: AsyncSession, query: AdminUserQuery, limit: int) -> tuple[list[User], int]:
    conditions = []
    if query.role:
        conditions.append(User.role == query.role)
    if query.q and query.q.strip():
        # autoescape: a % or a _ in the search is looked for as it is, not as a wildcard
        search = query.q.strip().lower()
        conditions.append(or_(
            func.lower(User.name).contains(search, autoescape=True),
            User.email.contains(search, autoescape=True),
        ))
    total = await db.scalar(select(func.count()).select_from(User).where(*conditions)) or 0
    page = select(User).where(*conditions).order_by(func.lower(User.name), User.id)
    users = await db.scalars(page.offset((query.page - 1) * limit).limit(limit))
    return list(users), total


# The ids of every librarian, locked until the commit (FOR NO KEY UPDATE) in the order of their ids. Taking a
# librarian away waits for any other change of a librarian, so two of them taking each other away at once can't leave
# the library with nobody: the second one finds the first change already done
async def get_librarian_ids_locked(db: AsyncSession) -> list[uuid.UUID]:
    query = select(User.id).where(User.role == UserRole.LIBRARIAN).order_by(User.id).with_for_update(key_share=True)
    return list(await db.scalars(query))


# Saves the name and the role of the account
async def update_user(db: AsyncSession, user_id: uuid.UUID, name: str, role: UserRole) -> None:
    await db.execute(update(User).where(User.id == user_id).values(name=name, role=role))


# Deletes the account: its sessions, links and finished loans go with it (cascade)
async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(User).where(User.id == user_id))
