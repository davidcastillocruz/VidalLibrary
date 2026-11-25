import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.models.language_model import ItemLanguage

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back


# Every language, sorted by name
async def get_languages(db: AsyncSession) -> list[ItemLanguage]:
    return list(await db.scalars(select(ItemLanguage).order_by(func.lower(ItemLanguage.name))))


# The language of an id, None if there is none.
# lock: locked until the commit (FOR KEY SHARE): a language being given to a work can't be deleted under it
async def get_language_by_id(db: AsyncSession, language_id: uuid.UUID, lock: bool) -> ItemLanguage | None:
    return await db.get(ItemLanguage, language_id, with_for_update={"read": True, "key_share": True} if lock else None)


# A new language. The flush gives it its id, and a repeated name fails here
async def create_language(db: AsyncSession, name: str) -> ItemLanguage:
    language = ItemLanguage(name=name)
    db.add(language)
    await db.flush()
    return language


# Renames the language. A repeated name fails here
async def update_language_name(db: AsyncSession, language_id: uuid.UUID, name: str) -> None:
    await db.execute(update(ItemLanguage).where(ItemLanguage.id == language_id).values(name=name))


# Deletes the language: its works are left without one (SET NULL)
async def delete_language(db: AsyncSession, language_id: uuid.UUID) -> None:
    await db.execute(delete(ItemLanguage).where(ItemLanguage.id == language_id))
