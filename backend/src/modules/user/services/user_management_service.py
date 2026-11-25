import logging
import uuid

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail, get_response
from src.mail.emails import build_invitation_email
from src.mail.sender import send_email
from src.modules.auth.models.password_token_model import PasswordTokenPurpose
from src.modules.auth.repositories import password_token_repository
from src.modules.loan.repositories import loan_repository
from src.modules.user.models.user_model import User, UserRole
from src.modules.user.repositories import user_repository
from src.modules.user.schemas.user_schemas import (
    AdminUserPage,
    AdminUserQuery,
    AdminUserResponse,
    NewUserSchema,
    UserCreatedResponse,
    UserUpdateSchema,
)
from src.security.tokens import new_token
from src.shared.schemas import MessageResponse

logger = logging.getLogger(__name__)

# Accounts in each page of the panel
PAGE_SIZE = 30


# 409 when the email already has an account: checked first, and caught from the database when two librarians add it
# at once
def _email_taken(language: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=get_error_detail("EMAIL_TAKEN", language),
    )


# The account of an id with its row locked until the commit: a reservation of its owner at this same moment waits, so
# an account is never deleted with a loan just opened. 404 when there is none
async def _get_user(db: AsyncSession, user_id: uuid.UUID, language: str) -> User:
    user = await user_repository.get_user_by_id(db, user_id, lock=True)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_error_detail("USER_NOT_FOUND", language),
        )
    return user


# 409 when the change would leave the library without librarians: user_id is one and no other one is left. Every
# librarian is locked first (see get_librarian_ids_locked)
async def _check_other_librarians(db: AsyncSession, user_id: uuid.UUID, language: str) -> None:
    librarian_ids = await user_repository.get_librarian_ids_locked(db)
    if user_id in librarian_ids and len(librarian_ids) == 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("LAST_LIBRARIAN", language),
        )


# A new invitation link for the account. Built before saving: if a text is missing nothing changes
async def _invite(db: AsyncSession, user: User, language: str) -> tuple[str, str]:
    token, token_hash = new_token()
    subject, html = build_invitation_email(language, user.name, token)
    await password_token_repository.create_password_token(db, user.id, PasswordTokenPurpose.INVITATION, token_hash)
    return subject, html


# One page of the accounts, with their open loans
async def get_users(db: AsyncSession, query: AdminUserQuery) -> AdminUserPage:
    users, total = await user_repository.get_users(db, query, PAGE_SIZE)
    open_loans = await loan_repository.get_open_loan_counts_by_user_ids(db, [user.id for user in users])
    return AdminUserPage(
        users=[
            AdminUserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                created_at=user.created_at,
                invited=not user.password_hash,
                open_loans=open_loans.get(user.id, 0),
            )
            for user in users
        ],
        total=total,
    )


# Creates an account and emails its invitation, in the language of the librarian: its owner chooses the password from
# the link. The email is checked first, and caught from the database when two librarians add it at once
async def create_user(
    db: AsyncSession,
    body: NewUserSchema,
    language: str,
    background_tasks: BackgroundTasks,
) -> UserCreatedResponse:
    if await user_repository.get_user_by_email(db, body.email):
        raise _email_taken(language)
    try:
        user = await user_repository.create_user(db, body.email, body.name, body.role)
    except IntegrityError:
        raise _email_taken(language) from None
    subject, html = await _invite(db, user, language)
    await db.commit()
    logger.info("Account created", extra={"account_id": user.id})

    background_tasks.add_task(send_email, subject, [body.email], html)
    return UserCreatedResponse(id=user.id, **get_response("USER_CREATED", language))


# Sends the invitation again, to an account whose owner hasn't chosen a password: the old link stops working.
# Its pending links are revoked first and only then the account is read under its lock, in the same order as accepting
# an invitation (its link, then its account): an invitation accepted at this moment is seen here, or the one being
# accepted stops working, never both, and the two never wait for each other in a circle
async def resend_invitation(
    db: AsyncSession,
    user_id: uuid.UUID,
    language: str,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    await password_token_repository.revoke_password_tokens(db, user_id)
    user = await _get_user(db, user_id, language)
    if user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("ALREADY_ACTIVE", language),
        )
    subject, html = await _invite(db, user, language)
    await db.commit()
    logger.info("Invitation sent again", extra={"account_id": user.id})

    background_tasks.add_task(send_email, subject, [user.email], html)
    return MessageResponse(**get_response("INVITATION_SENT", language))


# Saves the name and the role of an account. A librarian can't take away its own role, nor the one of the last other
# librarian: the library would end up with nobody to run it. Another librarian's role takes effect on its next request
async def update_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    body: UserUpdateSchema,
    language: str,
    librarian: User,
) -> MessageResponse:
    if user_id == librarian.id and body.role != UserRole.LIBRARIAN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("CANT_CHANGE_OWN_ROLE", language),
        )
    if body.role != UserRole.LIBRARIAN:
        await _check_other_librarians(db, user_id, language)
    await _get_user(db, user_id, language)
    await user_repository.update_user(db, user_id, body.name, body.role)
    await db.commit()
    logger.info("Account saved", extra={"account_id": user_id})

    return MessageResponse(**get_response("USER_SAVED", language))


# Deletes an account, never the own one, the last other librarian nor one with open loans: its finished loans,
# sessions and links go with it. Its pending links are revoked before any account is locked, in the order of opening
# a link (the link, then its account): a deletion and a password chosen at that moment wait for each other instead of
# each holding what the other needs
async def delete_user(db: AsyncSession, user_id: uuid.UUID, language: str, librarian: User) -> MessageResponse:
    if user_id == librarian.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("CANT_DELETE_SELF", language),
        )
    await password_token_repository.revoke_password_tokens(db, user_id)
    await _check_other_librarians(db, user_id, language)
    await _get_user(db, user_id, language)
    if await loan_repository.get_open_loan_counts_by_user_ids(db, [user_id]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("USER_HAS_OPEN_LOANS", language),
        )
    await user_repository.delete_user(db, user_id)
    await db.commit()
    logger.info("Account deleted", extra={"account_id": user_id})

    return MessageResponse(**get_response("USER_DELETED", language))
