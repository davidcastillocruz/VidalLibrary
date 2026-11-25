import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from src.api.dependencies import Language
from src.core.limiter import CATALOG_LIMIT, COVER_LIMIT, limiter
from src.database.session import DbSession
from src.modules.catalog.models.item_model import ItemKind
from src.modules.catalog.schemas.catalog_schemas import (
    CatalogPage,
    CatalogQuery,
    GenreResponse,
    ItemDetail,
    LanguageResponse,
)
from src.modules.catalog.services import catalog_service

router = APIRouter(prefix="/catalog", tags=["Catalog"])


# One page of the catalog, with its filters and its sort. Public: it is browsed without a session
@router.get("/items")
@limiter.limit(CATALOG_LIMIT)
async def get_items(request: Request, db: DbSession, query: Annotated[CatalogQuery, Query()]) -> CatalogPage:
    return await catalog_service.get_items(db, query)


# A work on its own page
@router.get("/items/{item_id}")
@limiter.limit(CATALOG_LIMIT)
async def get_item(request: Request, item_id: uuid.UUID, db: DbSession, language: Language) -> ItemDetail:
    return await catalog_service.get_item(db, item_id, language)


# The cover of a work, as WebP: a normal <img>, not a fetch. v: its version (the cover of the work in the catalog)
@router.get("/items/{item_id}/cover")
@limiter.limit(COVER_LIMIT)
async def get_cover(
    request: Request,
    item_id: uuid.UUID,
    db: DbSession,
    language: Language,
    v: Annotated[str | None, Query(max_length=64)] = None,
) -> Response:
    return await catalog_service.get_cover(db, item_id, v, language)


# The genres of a kind, or of every kind without ?kind=
@router.get("/genres")
@limiter.limit(CATALOG_LIMIT)
async def get_genres(request: Request, db: DbSession, kind: ItemKind | None = None) -> list[GenreResponse]:
    return await catalog_service.get_genres(db, kind)


# Every language of the works
@router.get("/languages")
@limiter.limit(CATALOG_LIMIT)
async def get_languages(request: Request, db: DbSession) -> list[LanguageResponse]:
    return await catalog_service.get_languages(db)
