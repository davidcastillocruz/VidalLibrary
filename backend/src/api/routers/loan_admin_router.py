import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request

from src.api.dependencies import CurrentLibrarian, Language, get_session_user_id
from src.core.limiter import OCCASIONAL_LIMIT, READ_LIMIT, limiter
from src.database.session import DbSession
from src.modules.loan.schemas.loan_schemas import AdminLoanPage, AdminLoanQuery, PickupSchema
from src.modules.loan.services import loan_management_service
from src.shared.schemas import MessageResponse

router = APIRouter(prefix="/admin/loans", tags=["Loans management"])


# One page of the loans for the desk, with their readers
@router.get("")
@limiter.limit(READ_LIMIT, key_func=get_session_user_id)
async def get_loans(
    request: Request,
    db: DbSession,
    query: Annotated[AdminLoanQuery, Query()],
    current: CurrentLibrarian,
) -> AdminLoanPage:
    return await loan_management_service.get_loans(db, query)


# Hands a reserved copy over to its reader
@router.post("/{loan_id}/pickup")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def pick_up(
    request: Request,
    loan_id: uuid.UUID,
    body: PickupSchema,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await loan_management_service.pick_up(db, loan_id, body, language)


# The reader brought the copy back
@router.post("/{loan_id}/return")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def return_loan(
    request: Request,
    loan_id: uuid.UUID,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await loan_management_service.return_loan(db, loan_id, language)


# Cancels a reservation for its reader
@router.post("/{loan_id}/cancel")
@limiter.limit(OCCASIONAL_LIMIT, key_func=get_session_user_id)
async def cancel(
    request: Request,
    loan_id: uuid.UUID,
    db: DbSession,
    language: Language,
    current: CurrentLibrarian,
) -> MessageResponse:
    return await loan_management_service.cancel(db, loan_id, language)
