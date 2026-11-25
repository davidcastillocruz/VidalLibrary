import uuid
from typing import Any

from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.models.item_model import Item, ItemKind, item_genres
from src.modules.catalog.schemas.catalog_schemas import CatalogQuery

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back

# The order of each sort of the catalog. id breaks ties: the same rows always give the same pages
SORTS = {
    "title": (func.lower(Item.title), Item.id),
    "newest": (Item.created_at.desc(), Item.id),
    "year": (Item.year.desc().nulls_last(), func.lower(Item.title), Item.id),
}


# One page of the works that match the query, and how many match in all
async def get_items(db: AsyncSession, query: CatalogQuery, limit: int) -> tuple[list[Item], int]:
    conditions = []
    if query.kind:
        conditions.append(Item.kind == query.kind)
    if query.language:
        conditions.append(Item.language_id == query.language)
    if query.genre:
        tagged = select(item_genres.c.item_id).where(item_genres.c.genre_id == query.genre)
        conditions.append(Item.id.in_(tagged))
    if query.q and query.q.strip():
        # autoescape: a % or a _ in the search is looked for as it is, not as a wildcard
        search = query.q.strip().lower()
        conditions.append(or_(
            func.lower(Item.title).contains(search, autoescape=True),
            func.lower(Item.creator).contains(search, autoescape=True),
        ))
    total = await db.scalar(select(func.count()).select_from(Item).where(*conditions)) or 0
    page = select(Item).where(*conditions).order_by(*SORTS[query.sort])
    items = await db.scalars(page.offset((query.page - 1) * limit).limit(limit))
    return list(items), total


# The work of an id, None if there is none.
# lock: its row locked until the commit (FOR NO KEY UPDATE) and read again even if this session already had it: a
# reservation and a change of its copies wait for each other, so the copies never fall under the open loans
async def get_item_by_id(db: AsyncSession, item_id: uuid.UUID, lock: bool) -> Item | None:
    return await db.get(Item, item_id, with_for_update={"key_share": True} if lock else None, populate_existing=lock)


# Locks the works of a language until the commit (FOR NO KEY UPDATE), in the order of their ids. Deleting the
# language sets theirs to NULL: taking them first is the order of saving a work (the work, then its language), so a
# deletion and a save of one of its works wait for each other instead of each holding what the other needs
async def lock_items_by_language_id(db: AsyncSession, language_id: uuid.UUID) -> None:
    query = select(Item.id).where(Item.language_id == language_id).order_by(Item.id)
    await db.execute(query.with_for_update(key_share=True))


# The key of the cover of the work, None without one (or without the work).
# lock: to change it, its row locked until the commit (FOR NO KEY UPDATE): two changes of the cover at once would both
# remove the same old file and leave the other new one behind
async def get_cover_key_by_item_id(db: AsyncSession, item_id: uuid.UUID, lock: bool) -> str | None:
    query = select(Item.cover_key).where(Item.id == item_id)
    return await db.scalar(query.with_for_update(key_share=True) if lock else query)


# Saves the key of the cover in the storage, None when it is removed. False when the work no longer exists (deleted
# while its new cover was being processed): nothing was saved
async def set_cover_key(db: AsyncSession, item_id: uuid.UUID, key: str | None) -> bool:
    query = update(Item).where(Item.id == item_id).values(cover_key=key).returning(Item.id)
    return bool(await db.scalar(query))


# A new work. The flush gives it its id, for its genres
async def create_item(db: AsyncSession, kind: ItemKind, values: dict[str, Any]) -> Item:
    item = Item(kind=kind, **values)
    db.add(item)
    await db.flush()
    return item


# Saves the fields of the work: values is {column: new value}
async def update_item(db: AsyncSession, item_id: uuid.UUID, values: dict[str, Any]) -> None:
    await db.execute(update(Item).where(Item.id == item_id).values(values))


# Replaces the genres of the work with these ones
async def set_item_genres(db: AsyncSession, item_id: uuid.UUID, genre_ids: list[uuid.UUID]) -> None:
    await db.execute(delete(item_genres).where(item_genres.c.item_id == item_id))
    if genre_ids:
        await db.execute(insert(item_genres), [{"item_id": item_id, "genre_id": genre_id} for genre_id in genre_ids])


# Deletes the work, with its genres (cascade)
async def delete_item(db: AsyncSession, item_id: uuid.UUID) -> None:
    await db.execute(delete(Item).where(Item.id == item_id))
