import uuid

from fastapi import APIRouter, Request, UploadFile, status

from src.api.dependencies import CurrentLibrarian, Language, get_session_user_id
from src.core.limiter import OCCASIONAL_LIMIT, limiter
from src.database.session import DbSession
from src.modules.catalog.schemas.catalog_schemas import (
    GenreResponse,
    GenreSchema,
    ItemCreatedResponse,
    ItemSchema,
    LanguageResponse,
    NameSchema,
)
from src.modules.catalog.services import catalog_management_service
from src.shared.schemas import MessageResponse

router = APIRouter(prefix="/admin/catalog", tags=["Catalog management"])


# Adds a work to the catalog
@router.post("/items", status_code=status.HTTP_201_CREATED)
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def create_item(
    request: Request,
    body: ItemSchema,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> ItemCreatedResponse:
    return await catalog_management_service.create_item(db, body, language)


# Saves the whole work, its genres included
@router.put("/items/{item_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def update_item(
    request: Request,
    item_id: uuid.UUID,
    body: ItemSchema,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await catalog_management_service.update_item(db, item_id, body, language)


# Removes a work from the catalog
@router.delete("/items/{item_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def delete_item(
    request: Request,
    item_id: uuid.UUID,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await catalog_management_service.delete_item(db, item_id, language)


# A new cover of a work, as a file (multipart): PNG, JPEG or WebP
@router.put("/items/{item_id}/cover")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def update_cover(
    request: Request,
    item_id: uuid.UUID,
    cover: UploadFile,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await catalog_management_service.update_cover(db, item_id, cover, language)


# Removes the cover of a work
@router.delete("/items/{item_id}/cover")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def remove_cover(
    request: Request,
    item_id: uuid.UUID,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await catalog_management_service.remove_cover(db, item_id, language)


# A new genre of a kind
@router.post("/genres", status_code=status.HTTP_201_CREATED)
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def create_genre(
    request: Request,
    body: GenreSchema,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> GenreResponse:
    return await catalog_management_service.create_genre(db, body, language)


# Renames a genre
@router.put("/genres/{genre_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def rename_genre(
    request: Request,
    genre_id: uuid.UUID,
    body: NameSchema,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await catalog_management_service.rename_genre(db, genre_id, body, language)


# Deletes a genre: its works stay, without it
@router.delete("/genres/{genre_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def delete_genre(
    request: Request,
    genre_id: uuid.UUID,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await catalog_management_service.delete_genre(db, genre_id, language)


# A new language of the works
@router.post("/languages", status_code=status.HTTP_201_CREATED)
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def create_language(
    request: Request,
    body: NameSchema,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> LanguageResponse:
    return await catalog_management_service.create_language(db, body, language)


# Renames a language
@router.put("/languages/{language_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def rename_language(
    request: Request,
    language_id: uuid.UUID,
    body: NameSchema,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await catalog_management_service.rename_language(db, language_id, body, language)


# Deletes a language: its works stay, without one
@router.delete("/languages/{language_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def delete_language(
    request: Request,
    language_id: uuid.UUID,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await catalog_management_service.delete_language(db, language_id, language)
