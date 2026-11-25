import hashlib
import logging

from fastapi import HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail, get_response
from src.core.limiter import clear_limit, hit_limit, limit_reached
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.auth.repositories import session_repository
from src.modules.auth.schemas.auth_schemas import LoginSchema
from src.modules.user.repositories import user_repository
from src.security.cookies import delete_session_cookie, set_session_cookie
from src.security.passwords import hash_password, password_needs_rehash, verify_password
from src.security.tokens import new_token
from src.shared.schemas import MessageResponse

logger = logging.getLogger(__name__)

# Failed logins of one email, whoever tries them: the limit per IP doesn't stop guessing the password of an account
# from many addresses. Only the failures count, so a shared classroom never reaches it by signing in
LOGIN_FAILURE_LIMIT = "5/minute;20/hour"

# The user agent is only kept for the logs of the sessions: a longer one is cut, nobody reads past this
USER_AGENT_MAX_LENGTH = 512


# Signs in with the email and the password, and the session goes to its cookie:
# - the same 401 for an unknown email, a wrong password and an account that hasn't chosen its password yet: the
#   response doesn't tell which emails have an account, and an unknown email takes as long (verify_password)
# - past LOGIN_FAILURE_LIMIT even the right password gets that error, and the unknown emails count the same
async def login(
    db: AsyncSession,
    body: LoginSchema,
    language: str,
    response: Response,
    ip: str,
    user_agent: str | None,
) -> MessageResponse:
    user = await user_repository.get_user_by_email(db, body.email)
    password_hash = user.password_hash if user else None
    valid = await verify_password(body.password, password_hash)

    # The counter is keyed by the hash of the email: the storage (Redis) never keeps the address
    email_key = hashlib.sha256(body.email.encode()).hexdigest()
    if limit_reached(LOGIN_FAILURE_LIMIT, "login-failure", email_key) or not user or not password_hash or not valid:
        hit_limit(LOGIN_FAILURE_LIMIT, "login-failure", email_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_error_detail("INVALID_CREDENTIALS", language),
        )

    # The only moment the app has the password: a hash with older parameters is replaced in the same commit
    if password_needs_rehash(password_hash):
        await user_repository.set_password_hash(db, user.id, await hash_password(body.password))
    token, token_hash = new_token()
    user_agent = user_agent[:USER_AGENT_MAX_LENGTH] if user_agent else None
    await session_repository.create_session(db, user.id, token_hash, user_agent, ip)
    await db.commit()
    logger.info("Signed in", extra={"account_id": user.id})

    clear_limit(LOGIN_FAILURE_LIMIT, "login-failure", email_key)
    set_session_cookie(response, token)
    return MessageResponse(**get_response("LOGIN_SUCCESS", language))


# Closes the session of this browser and deletes its cookie
async def logout(db: AsyncSession, language: str, response: Response, session: AuthSession) -> MessageResponse:
    await session_repository.revoke_session(db, session.id)
    await db.commit()
    logger.info("Signed out", extra={"session_id": session.id})

    delete_session_cookie(response)
    return MessageResponse(**get_response("LOGOUT_SUCCESS", language))
