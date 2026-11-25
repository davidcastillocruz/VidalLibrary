from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status

from src.core import request_context
from src.core.languages import get_error_detail
from src.core.settings import settings
from src.database.session import DbSession
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.auth.repositories import session_repository
from src.modules.user.models.user_model import User, UserRole
from src.security.cookies import delete_session_cookie, delete_session_cookie_header
from src.security.tokens import hash_token


# Client IP for logging, rate limiting and the sessions
def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# Client IP of the request, in an endpoint: client_ip: ClientIp
ClientIp = Annotated[str, Depends(get_client_ip)]

# User agent of the browser, kept with its session, in an endpoint: user_agent: UserAgent = None
UserAgent = Annotated[str | None, Header()]


# Language the API answers in, taken from the request
# Priority: ?lang= > "language" cookie > Accept-Language header > MAIN_LANGUAGE
def get_language(request: Request, lang: str | None = None) -> str:
    supported = settings.AVAILABLE_LANGUAGES
    tags: list[str] = []

    # 1. Query param: ?lang=es
    if lang:
        tags.append(lang.lower())

    # 2. Cookie saved when the user picked a language
    cookie_lang = request.cookies.get("language")
    if cookie_lang:
        tags.append(cookie_lang.lower())

    # 3. Accept-Language: "es-ES,es;q=0.9,en;q=0.8" -> ["es-es", "es", "en"]
    candidates: list[tuple[float, str]] = []
    # Spaces around ";" are valid ("es; q=0.9"). A quality of 0 means "not acceptable",
    # so q=0, a quality above 1 or one that isn't a number discards the tag
    for part in request.headers.get("accept-language", "").split(","):
        tag, *params = (piece.strip() for piece in part.split(";"))
        quality = 1.0
        for param in params:
            if param.lower().startswith("q="):
                try:
                    quality = float(param[2:])
                except ValueError:
                    quality = -1.0
        tag = tag.lower()
        if tag and tag != "*" and 0 < quality <= 1:
            candidates.append((quality, tag))

    # Highest quality first, ties keep the browser's order (sorted is stable)
    tags.extend(tag for _, tag in sorted(candidates, key=lambda c: -c[0]))

    # First supported tag wins, trying the base language too ("es-es" -> "es")
    for tag in tags:
        for option in (tag, tag.split("-")[0]):
            if option in supported:
                return option

    # 4. Fallback
    return settings.MAIN_LANGUAGE


# Language of the request, in an endpoint: language: Language
Language = Annotated[str, Depends(get_language)]


# What an endpoint gets from require_auth: the signed-in user and the session in use
@dataclass(frozen=True)
class CurrentSession:
    user: User
    session: AuthSession


# 401 when there is no valid session. clear_cookie: the browser sent a cookie that no longer works
# (unknown token, revoked or expired), the response deletes it so it isn't sent again
def _not_authenticated(language: str, clear_cookie: bool = False) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=get_error_detail("NOT_AUTHENTICATED", language),
        headers=delete_session_cookie_header() if clear_cookie else None,
    )


# The signed-in user of the request, or a 401
async def require_auth(request: Request, language: Language, db: DbSession) -> CurrentSession:
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token:
        raise _not_authenticated(language)

    # The database only keeps the hash: the same token always gives the same hash, looked up by its unique index
    found = await session_repository.get_valid_session(db, hash_token(session_token))
    if not found:
        raise _not_authenticated(language, clear_cookie=True)

    session, user = found
    await session_repository.mark_session_used(db, session.id)
    await db.commit()
    # The user goes in the logs: the contextvar for the lines written while the endpoint runs, request.state
    # for the line of log_requests, which runs in another task and doesn't see the contextvar (main.py)
    request_context.user_id.set(str(user.id))
    request.state.user_id = str(user.id)
    return CurrentSession(user=user, session=session)


# Signed-in user of the request, in an endpoint: current: CurrentUser (current.user, current.session)
CurrentUser = Annotated[CurrentSession, Depends(require_auth)]


# The signed-in user when it runs the library, or a 403: a reader can't touch the catalog, the loans or the accounts
async def require_librarian(current: CurrentUser, language: Language) -> CurrentSession:
    if current.user.role != UserRole.LIBRARIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=get_error_detail("LIBRARIANS_ONLY", language),
        )
    return current


# Signed-in librarian of the request, in an endpoint: current: CurrentLibrarian
CurrentLibrarian = Annotated[CurrentSession, Depends(require_librarian)]


# Key of a limit that counts per user and not per IP, for a route with a session: the limiter runs after require_auth.
# In a route: @limiter.limit(READ_LIMIT, key_func=get_session_user_id)
def get_session_user_id(request: Request) -> str:
    return request.state.user_id


# Lets through only requests without a valid session, in an endpoint: dependencies=[Depends(require_guest)]
# A cookie that no longer works (unknown token, revoked or expired) is deleted and the request goes on as a guest.
# The deletion goes in the response of the endpoint: if the endpoint raises an HTTPException it is lost,
# and the next request deletes it again
async def require_guest(request: Request, response: Response, language: Language, db: DbSession) -> None:
    session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token:
        return

    if await session_repository.get_valid_session(db, hash_token(session_token)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("ALREADY_AUTHENTICATED", language),
        )
    delete_session_cookie(response)
