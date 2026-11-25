import uuid

from fastapi import HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail
from src.modules.catalog.cover import cover_files
from src.modules.catalog.models.item_model import Item, ItemKind
from src.modules.catalog.repositories import genre_repository, item_repository, language_repository
from src.modules.catalog.schemas.catalog_schemas import (
    CatalogPage,
    CatalogQuery,
    GenreResponse,
    ItemDetail,
    ItemSummary,
    LanguageResponse,
)
from src.storage import files

# Works in each page of the catalog: two rows of a wide screen
PAGE_SIZE = 24


# A work as its card shows it
def _summary(item: Item) -> ItemSummary:
    return ItemSummary(
        id=item.id,
        kind=item.kind,
        title=item.title,
        creator=item.creator,
        year=item.year,
        copies=item.copies,
        cover=cover_files.cover_version(item.cover_key) if item.cover_key else None,
    )


# One page of the catalog, with the filters of the query. Anyone can browse it, with or without a session
async def get_items(db: AsyncSession, query: CatalogQuery) -> CatalogPage:
    items, total = await item_repository.get_items(db, query, PAGE_SIZE)
    return CatalogPage(
        items=[_summary(item) for item in items],
        total=total,
    )


# A work with its language and its genres, or a 404
async def get_item(db: AsyncSession, item_id: uuid.UUID, language: str) -> ItemDetail:
    item = await item_repository.get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_error_detail("ITEM_NOT_FOUND", language),
        )
    item_language = None
    if item.language_id:
        item_language = await language_repository.get_language_by_id(db, item.language_id, lock=False)
    genres = await genre_repository.get_genres_by_item_id(db, item.id)
    return ItemDetail(
        **_summary(item).model_dump(),
        synopsis=item.synopsis,
        language=LanguageResponse.model_validate(item_language, from_attributes=True) if item_language else None,
        genres=[GenreResponse.model_validate(genre, from_attributes=True) for genre in genres],
    )


# The genres of a kind, for its filter, or of every kind, for the panel of the library
async def get_genres(db: AsyncSession, kind: ItemKind | None) -> list[GenreResponse]:
    genres = await genre_repository.get_genres(db, kind)
    return [GenreResponse.model_validate(genre, from_attributes=True) for genre in genres]


# Every language, for the filter and the form of a work
async def get_languages(db: AsyncSession) -> list[LanguageResponse]:
    languages = await language_repository.get_languages(db)
    return [LanguageResponse.model_validate(language, from_attributes=True) for language in languages]


# The cover of a work, as WebP. Public like the catalog. Asked with the version it has now (version, from ?v=), the
# browser keeps it for good: a new cover comes with a new version, so with a new address. Asked without it, or with an
# old one, it has to ask again each time
async def get_cover(db: AsyncSession, item_id: uuid.UUID, version: str | None, language: str) -> Response:
    key = await item_repository.get_cover_key_by_item_id(db, item_id, lock=False)
    content = await files.read_file(key) if key else None
    if not key or not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=get_error_detail("NOT_FOUND", language))
    current = version == cover_files.cover_version(key)
    cache = "public, max-age=31536000, immutable" if current else "public, no-cache"
    return Response(content, media_type="image/webp", headers={"Cache-Control": cache})
