import uuid

from fastapi import APIRouter, Request

from src.api.dependencies import CurrentUser, Language, get_session_user_id
from src.core.limiter import OCCASIONAL_LIMIT, READ_LIMIT, limiter
from src.database.session import DbSession
from src.modules.loan.schemas.loan_schemas import LoanResponse, ReservationSchema
from src.modules.loan.services import loan_service
from src.shared.schemas import MessageResponse

router = APIRouter(prefix="/loans", tags=["Loans"])


# Reserves a copy of a work, to pick it up at the library
@router.post("")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def reserve(
    request: Request,
    body: ReservationSchema,
    db: DbSession,
    language: Language,
    current: CurrentUser,
) -> MessageResponse:
    return await loan_service.reserve(db, body, language, current.user)


# The loans of the signed-in reader
@router.get("")
@limiter.limit(READ_LIMIT, key_func=get_session_user_id)
async def get_my_loans(request: Request, db: DbSession, current: CurrentUser) -> list[LoanResponse]:
    return await loan_service.get_my_loans(db, current.user)


# Cancels a reservation of the signed-in reader that wasn't picked up
@router.delete("/{loan_id}")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def cancel_my_loan(
    request: Request,
    loan_id: uuid.UUID,
    db: DbSession,
    language: Language,
    current: CurrentUser,
) -> MessageResponse:
    return await loan_service.cancel_my_loan(db, loan_id, language, current.user)
