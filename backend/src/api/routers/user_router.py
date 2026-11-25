from fastapi import APIRouter, Request

from src.api.dependencies import CurrentUser, get_session_user_id
from src.core.limiter import READ_LIMIT, limiter
from src.modules.user.schemas.user_schemas import UserResponse
from src.modules.user.services import user_service

router = APIRouter(prefix="/user", tags=["User"])


# Who is signed in: the frontend asks it on every page load
@router.get("/me")
@limiter.limit(READ_LIMIT, key_func=get_session_user_id)
async def me(request: Request, current: CurrentUser) -> UserResponse:
    return user_service.me(current.user)
