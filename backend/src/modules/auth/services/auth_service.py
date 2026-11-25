import hashlib
import logging

from fastapi import BackgroundTasks, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail, get_response
from src.core.limiter import clear_limit, hit_limit, limit_reached
from src.mail.emails import build_password_changed_email, build_password_reset_email
from src.mail.sender import send_email
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.auth.models.password_token_model import PasswordTokenPurpose
from src.modules.auth.repositories import password_token_repository, session_repository
from src.modules.auth.schemas.auth_schemas import EmailSchema, LoginSchema, TokenPasswordSchema
from src.modules.user.repositories import user_repository
from src.security.cookies import delete_session_cookie, set_session_cookie
from src.security.passwords import hash_password, password_needs_rehash, verify_password
from src.security.tokens import hash_token, new_token
from src.shared.schemas import MessageResponse

logger = logging.getLogger(__name__)

# Failed logins of one email, whoever tries them: the limit per IP doesn't stop guessing the password of an account
# from many addresses. Only the failures count, so a shared classroom never reaches it by signing in
LOGIN_FAILURE_LIMIT = "5/minute;20/hour"

# Recovery emails one address can get: enough to ask again if one didn't arrive, too few to flood the inbox
PASSWORD_RESET_EMAIL_LIMIT = "1/minute;5/hour"

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


# Sends the link to choose a new password. Same response whether the email has an account or not:
# - an account gets the link after the response, an unknown email gets nothing
# - past PASSWORD_RESET_EMAIL_LIMIT nothing is sent and nothing changes, with the same response (a 429 would tell too)
# An account whose invitation wasn't opened gets it too: the link chooses its first password the same way
async def forgot_password(
    db: AsyncSession,
    body: EmailSchema,
    language: str,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    message = get_response("PASSWORD_RESET_EMAIL_SENT", language)["message"]

    # The counter is keyed by the hash of the email: the storage (Redis) never keeps the address
    email_key = hashlib.sha256(body.email.encode()).hexdigest()
    if not hit_limit(PASSWORD_RESET_EMAIL_LIMIT, "password-reset-email", email_key):
        logger.info("Password reset email limit reached, nothing sent")
        return MessageResponse(message=message)

    user = await user_repository.get_user_by_email(db, body.email)
    if not user:
        return MessageResponse(message=message)

    token, token_hash = new_token()
    # Built before saving: if a text is missing the request fails without leaving a link behind
    subject, html = build_password_reset_email(language, user.name, token)

    # Only the newest link works: the pending ones of this user are revoked in the same commit
    await password_token_repository.revoke_password_tokens(db, user.id)
    password_token = await password_token_repository.create_password_token(
        db,
        user.id,
        PasswordTokenPurpose.PASSWORD_RESET,
        token_hash,
    )
    await db.commit()
    logger.info("Password reset link created", extra={"password_token_id": password_token.id})

    background_tasks.add_task(send_email, subject, [user.email], html)
    return MessageResponse(message=message)


# Opens the link of an email and saves the password the user chose, all in one commit. A wrong, used, revoked or expired
# link gets the same 400: it doesn't tell which one it was. What the login counted for the email is forgotten
async def reset_password(
    db: AsyncSession,
    body: TokenPasswordSchema,
    language: str,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    found = await password_token_repository.get_valid_password_token_with_user(db, hash_token(body.token))
    # An invitation only gives an account its first password. One that already has it changes it with a recovery
    # link, which closes its sessions and tells its owner: an old invitation never does it quietly
    if not found or (found[0].purpose == PasswordTokenPurpose.INVITATION and found[1].password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_detail("INVALID_PASSWORD_LINK", language),
        )
    password_token, user = found
    password_hash = await hash_password(body.password)

    if password_token.purpose == PasswordTokenPurpose.INVITATION:
        # Its first password: the account had no session nor anything to tell, it is ready to sign in
        await user_repository.set_password_hash(db, user.id, password_hash)
        await password_token_repository.use_password_token(db, password_token.id)
        await db.commit()
        logger.info("Invitation accepted", extra={"account_id": user.id})
        message = get_response("ACCOUNT_READY", language)["message"]
    else:
        # A new password: whoever knew the old one is out, every session is closed, and an email tells the owner.
        # Built before saving: if a text is missing the password doesn't change
        subject, html = build_password_changed_email(language, user.name)
        await user_repository.set_password_hash(db, user.id, password_hash)
        await session_repository.revoke_all_user_sessions(db, user.id)
        await password_token_repository.use_password_token(db, password_token.id)
        await db.commit()
        logger.info("Password reset", extra={"account_id": user.id})
        background_tasks.add_task(send_email, subject, [user.email], html)
        message = get_response("PASSWORD_RESET_SUCCESS", language)["message"]

    clear_limit(LOGIN_FAILURE_LIMIT, "login-failure", hashlib.sha256(user.email.encode()).hexdigest())
    return MessageResponse(message=message)
