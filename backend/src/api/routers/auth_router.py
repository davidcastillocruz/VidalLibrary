from fastapi import APIRouter, Depends, Request, Response

from src.api.dependencies import ClientIp, CurrentUser, Language, UserAgent, get_session_user_id, require_guest
from src.core.limiter import SIGN_IN_LIMIT, limiter
from src.database.session import DbSession
from src.modules.auth.schemas.auth_schemas import LoginSchema
from src.modules.auth.services import auth_service
from src.shared.schemas import MessageResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


# Signs in with the email and the password: the session goes to its cookie
@router.post("/login", dependencies=[Depends(require_guest)])
@limiter.limit(SIGN_IN_LIMIT)
async def login(
    request: Request,
    body: LoginSchema,
    db: DbSession,
    language: Language,
    response: Response,
    client_ip: ClientIp,
    user_agent: UserAgent = None,
) -> MessageResponse:
    return await auth_service.login(db, body, language, response, client_ip, user_agent)


# Closes the session of this browser
@router.post("/logout")
@limiter.limit(SIGN_IN_LIMIT, key_func=get_session_user_id)
async def logout(
    request: Request,
    db: DbSession,
    language: Language,
    response: Response,
    current: CurrentUser,
) -> MessageResponse:
    return await auth_service.logout(db, language, response, current.session)
