import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.models.genre_model import Genre
from src.modules.catalog.models.item_model import ItemKind, item_genres

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back


# The genres of a kind, or of every kind, sorted by name
async def get_genres(db: AsyncSession, kind: ItemKind | None) -> list[Genre]:
    query = select(Genre).order_by(Genre.kind, func.lower(Genre.name))
    return list(await db.scalars(query.where(Genre.kind == kind) if kind else query))


# The genres of a work, sorted by name
async def get_genres_by_item_id(db: AsyncSession, item_id: uuid.UUID) -> list[Genre]:
    query = (
        select(Genre)
        .join(item_genres, item_genres.c.genre_id == Genre.id)
        .where(item_genres.c.item_id == item_id)
        .order_by(func.lower(Genre.name))
    )
    return list(await db.scalars(query))


# The genres of these ids that exist, to check the ones a work gets.
# lock: locked until the commit (FOR KEY SHARE), in the order of their ids: a genre being given to a work can't be
# deleted under it (its deletion waits), and two works saved at once never wait for each other in a circle
async def get_genres_by_ids(db: AsyncSession, genre_ids: list[uuid.UUID], lock: bool) -> list[Genre]:
    query = select(Genre).where(Genre.id.in_(genre_ids)).order_by(Genre.id)
    return list(await db.scalars(query.with_for_update(read=True, key_share=True) if lock else query))


# The genre of an id, None if there is none
async def get_genre_by_id(db: AsyncSession, genre_id: uuid.UUID) -> Genre | None:
    return await db.get(Genre, genre_id)


# A new genre. The flush gives it its id, and a name repeated in its kind fails here
async def create_genre(db: AsyncSession, kind: ItemKind, name: str) -> Genre:
    genre = Genre(kind=kind, name=name)
    db.add(genre)
    await db.flush()
    return genre


# Renames the genre. A name repeated in its kind fails here
async def update_genre_name(db: AsyncSession, genre_id: uuid.UUID, name: str) -> None:
    await db.execute(update(Genre).where(Genre.id == genre_id).values(name=name))


# Deletes the genre: its works lose it (cascade)
async def delete_genre(db: AsyncSession, genre_id: uuid.UUID) -> None:
    await db.execute(delete(Genre).where(Genre.id == genre_id))
