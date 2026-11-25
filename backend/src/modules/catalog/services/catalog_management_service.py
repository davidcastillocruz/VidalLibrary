import logging
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail, get_response
from src.modules.catalog.cover import cover_files, cover_image
from src.modules.catalog.repositories import genre_repository, item_repository, language_repository
from src.modules.catalog.schemas.catalog_schemas import (
    GenreResponse,
    GenreSchema,
    ItemCreatedResponse,
    ItemSchema,
    LanguageResponse,
    NameSchema,
)
from src.modules.loan.repositories import loan_repository
from src.shared.schemas import MessageResponse
from src.storage import files

logger = logging.getLogger(__name__)


# 404 when the work of the path doesn't exist: raised by every change of a work
def _item_not_found(language: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=get_error_detail("ITEM_NOT_FOUND", language),
    )


# 404 when the genre of the path doesn't exist: renaming it and deleting it
def _genre_not_found(language: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=get_error_detail("GENRE_NOT_FOUND", language),
    )


# 409 when the kind already has a genre with that name: creating one and renaming it
def _genre_exists(language: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=get_error_detail("GENRE_EXISTS", language),
    )


# 404 when the language of the path doesn't exist: renaming it and deleting it
def _language_not_found(language: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=get_error_detail("LANGUAGE_NOT_FOUND", language),
    )


# 409 when there is already a language with that name: creating one and renaming it
def _language_exists(language: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=get_error_detail("LANGUAGE_EXISTS", language),
    )


# What a work gets has to exist: its language, and its genres, each one of its kind. A 400 otherwise
async def _check_language_and_genres(db: AsyncSession, body: ItemSchema, language: str) -> None:
    if body.language_id and not await language_repository.get_language_by_id(db, body.language_id, lock=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_detail("UNKNOWN_LANGUAGE", language),
        )
    genres = await genre_repository.get_genres_by_ids(db, body.genre_ids, lock=True)
    if len(genres) != len(set(body.genre_ids)) or any(genre.kind != body.kind for genre in genres):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_detail("INVALID_GENRES", language),
        )


# Adds a work to the catalog with its genres, all in one commit
async def create_item(db: AsyncSession, body: ItemSchema, language: str) -> ItemCreatedResponse:
    await _check_language_and_genres(db, body, language)
    item = await item_repository.create_item(db, body.kind, body.model_dump(exclude={"kind", "genre_ids"}))
    await item_repository.set_item_genres(db, item.id, list(set(body.genre_ids)))
    await db.commit()
    logger.info("Item created", extra={"item_id": item.id})

    return ItemCreatedResponse(id=item.id, message=get_response("ITEM_CREATED", language)["message"])


# Saves the whole work, its genres included, all in one commit. Its kind can change: its genres then have to be
# of the new one. Its copies never fall under its open loans
async def update_item(db: AsyncSession, item_id: uuid.UUID, body: ItemSchema, language: str) -> MessageResponse:
    if not await item_repository.get_item_by_id(db, item_id, lock=True):
        raise _item_not_found(language)
    await _check_language_and_genres(db, body, language)
    # Locked above: a reservation at this same moment waits, and is counted here or counts the new copies
    open_loans = (await loan_repository.get_open_loan_counts_by_item_ids(db, [item_id])).get(item_id, 0)
    if body.copies < open_loans:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("COPIES_BELOW_OPEN_LOANS", language, {"detail": (open_loans,)}),
        )
    await item_repository.update_item(db, item_id, body.model_dump(exclude={"genre_ids"}))
    await item_repository.set_item_genres(db, item_id, list(set(body.genre_ids)))
    await db.commit()
    logger.info("Item saved", extra={"item_id": item_id})

    return MessageResponse(**get_response("ITEM_SAVED", language))


# Removes a work from the catalog, never with open loans: its finished ones go with it. The file of its cover goes
# after the commit, once the database no longer points to it
async def delete_item(db: AsyncSession, item_id: uuid.UUID, language: str) -> MessageResponse:
    item = await item_repository.get_item_by_id(db, item_id, lock=True)
    if not item:
        raise _item_not_found(language)
    # Locked above: a reservation at this same moment waits, and then finds no work
    if await loan_repository.get_open_loan_counts_by_item_ids(db, [item_id]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("ITEM_HAS_OPEN_LOANS", language),
        )
    await item_repository.delete_item(db, item_id)
    await db.commit()
    logger.info("Item deleted", extra={"item_id": item_id})

    if item.cover_key:
        await cover_files.remove_cover_file(item.cover_key)
    return MessageResponse(**get_response("ITEM_DELETED", language))


# A new cover of a work, PNG, JPEG or WebP, kept as WebP:
# - a new key on every change: the file the database points to is never overwritten
# - the key is read again with its row locked: two changes at once would remove the same old file
# - the new file is saved just before the commit, in the same try: it is removed if anything fails, a cancelled
#   request too (not an Exception). The old one goes after the commit
async def update_cover(db: AsyncSession, item_id: uuid.UUID, upload: UploadFile, language: str) -> MessageResponse:
    if not await item_repository.get_item_by_id(db, item_id, lock=False):
        raise _item_not_found(language)
    cover = await cover_image.read_cover(upload)
    if not cover:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_detail("COVER_INVALID", language),
        )

    old_key = await item_repository.get_cover_key_by_item_id(db, item_id, lock=True)
    new_key = cover_files.new_cover_key(item_id)
    # Deleted while its cover was being processed: no file is saved for a work that is gone
    if not await item_repository.set_cover_key(db, item_id, new_key):
        raise _item_not_found(language)
    try:
        await files.save_file(new_key, cover)
        await db.commit()
    except BaseException:
        await cover_files.remove_cover_file(new_key)
        raise
    logger.info("Cover changed", extra={"item_id": item_id})

    if old_key:
        await cover_files.remove_cover_file(old_key)
    return MessageResponse(**get_response("COVER_SAVED", language))


# Removes the cover of a work: the frontend draws its own again. Without one nothing changes. The file goes after the
# commit, once the database no longer points to it
async def remove_cover(db: AsyncSession, item_id: uuid.UUID, language: str) -> MessageResponse:
    if not await item_repository.get_item_by_id(db, item_id, lock=False):
        raise _item_not_found(language)
    old_key = await item_repository.get_cover_key_by_item_id(db, item_id, lock=True)
    if old_key:
        await item_repository.set_cover_key(db, item_id, None)
        await db.commit()
        logger.info("Cover removed", extra={"item_id": item_id})
        await cover_files.remove_cover_file(old_key)
    return MessageResponse(**get_response("COVER_REMOVED", language))


# A new genre of a kind. Its name can't repeat in the kind: two requests at once are stopped by the database
async def create_genre(db: AsyncSession, body: GenreSchema, language: str) -> GenreResponse:
    try:
        genre = await genre_repository.create_genre(db, body.kind, body.name)
    except IntegrityError:
        raise _genre_exists(language) from None
    await db.commit()
    logger.info("Genre created", extra={"genre_id": genre.id})

    return GenreResponse.model_validate(genre, from_attributes=True)


# Renames a genre: every work that has it shows the new name
async def rename_genre(db: AsyncSession, genre_id: uuid.UUID, body: NameSchema, language: str) -> MessageResponse:
    if not await genre_repository.get_genre_by_id(db, genre_id):
        raise _genre_not_found(language)
    try:
        await genre_repository.update_genre_name(db, genre_id, body.name)
    except IntegrityError:
        raise _genre_exists(language) from None
    await db.commit()
    logger.info("Genre renamed", extra={"genre_id": genre_id})

    return MessageResponse(**get_response("GENRE_SAVED", language))


# Deletes a genre: its works stay, without it
async def delete_genre(db: AsyncSession, genre_id: uuid.UUID, language: str) -> MessageResponse:
    if not await genre_repository.get_genre_by_id(db, genre_id):
        raise _genre_not_found(language)
    await genre_repository.delete_genre(db, genre_id)
    await db.commit()
    logger.info("Genre deleted", extra={"genre_id": genre_id})

    return MessageResponse(**get_response("GENRE_DELETED", language))


# A new language. Its name can't repeat: two requests at once are stopped by the database
async def create_language(db: AsyncSession, body: NameSchema, language: str) -> LanguageResponse:
    try:
        item_language = await language_repository.create_language(db, body.name)
    except IntegrityError:
        raise _language_exists(language) from None
    await db.commit()
    logger.info("Language created", extra={"language_id": item_language.id})

    return LanguageResponse.model_validate(item_language, from_attributes=True)


# Renames a language: every work in it shows the new name
async def rename_language(db: AsyncSession, language_id: uuid.UUID, body: NameSchema, language: str) -> MessageResponse:
    if not await language_repository.get_language_by_id(db, language_id, lock=False):
        raise _language_not_found(language)
    try:
        await language_repository.update_language_name(db, language_id, body.name)
    except IntegrityError:
        raise _language_exists(language) from None
    await db.commit()
    logger.info("Language renamed", extra={"language_id": language_id})

    return MessageResponse(**get_response("LANGUAGE_SAVED", language))


# Deletes a language: its works stay, without one. They are locked before it (see lock_items_by_language_id)
async def delete_language(db: AsyncSession, language_id: uuid.UUID, language: str) -> MessageResponse:
    if not await language_repository.get_language_by_id(db, language_id, lock=False):
        raise _language_not_found(language)
    await item_repository.lock_items_by_language_id(db, language_id)
    await language_repository.delete_language(db, language_id)
    await db.commit()
    logger.info("Language deleted", extra={"language_id": language_id})

    return MessageResponse(**get_response("LANGUAGE_DELETED", language))
