import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail
from src.modules.catalog.models.item_model import ItemKind
from src.modules.catalog.repositories import genre_repository, item_repository, language_repository
from src.modules.catalog.schemas.catalog_schemas import (
    CatalogPage,
    CatalogQuery,
    GenreResponse,
    ItemDetail,
    ItemSummary,
    LanguageResponse,
)

# Works in each page of the catalog: two rows of a wide screen
PAGE_SIZE = 24


# One page of the catalog, with the filters of the query. Anyone can browse it, with or without a session
async def get_items(db: AsyncSession, query: CatalogQuery) -> CatalogPage:
    items, total = await item_repository.get_items(db, query, PAGE_SIZE)
    return CatalogPage(
        items=[ItemSummary.model_validate(item, from_attributes=True) for item in items],
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
        **ItemSummary.model_validate(item, from_attributes=True).model_dump(),
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
