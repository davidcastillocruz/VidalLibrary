import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request, status

from src.api.dependencies import CurrentLibrarian, Language, get_session_user_id
from src.core.limiter import OCCASIONAL_LIMIT, READ_LIMIT, limiter
from src.database.session import DbSession
from src.modules.user.schemas.user_schemas import (
    AdminUserPage,
    AdminUserQuery,
    NewUserSchema,
    UserCreatedResponse,
    UserUpdateSchema,
)
from src.modules.user.services import user_management_service
from src.shared.schemas import MessageResponse

router = APIRouter(prefix="/admin/users", tags=["Accounts management"])


# One page of the accounts, with their open loans
@router.get("")
@limiter.limit(READ_LIMIT, key_func=get_session_user_id)
async def get_users(
    request: Request,
    db: DbSession,
    query: Annotated[AdminUserQuery, Query()],
    current: CurrentLibrarian,
) -> AdminUserPage:
    return await user_management_service.get_users(db, query)


# Creates an account and emails its invitation
@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def create_user(
    request: Request,
    body: NewUserSchema,
    db: DbSession,
    language: Language,
    background_tasks: BackgroundTasks,
    current: CurrentLibrarian,
) -> UserCreatedResponse:
    return await user_management_service.create_user(db, body, language, background_tasks)


# Sends the invitation again, to an account without a password yet
@router.post("/{user_id}/invitation")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def resend_invitation(
    request: Request,
    user_id: uuid.UUID,
    db: DbSession,
    language: Language,
    background_tasks: BackgroundTasks,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await user_management_service.resend_invitation(db, user_id, language, background_tasks)


# Saves the name and the role of an account
@router.put("/{user_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def update_user(
    request: Request,
    user_id: uuid.UUID,
    body: UserUpdateSchema,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await user_management_service.update_user(db, user_id, body, language, current.user)


# Deletes an account without open loans
@router.delete("/{user_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def delete_user(
    request: Request,
    user_id: uuid.UUID,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await user_management_service.delete_user(db, user_id, language, current.user)
