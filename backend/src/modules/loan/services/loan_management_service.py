import logging
import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail, get_response
from src.modules.loan.loan_rules import MAX_LOAN_DAYS, library_today
from src.modules.loan.models.loan_model import Loan, LoanStatus
from src.modules.loan.repositories import loan_repository
from src.modules.loan.schemas.loan_schemas import (
    AdminLoanPage,
    AdminLoanQuery,
    AdminLoanResponse,
    LoanReader,
    PickupSchema,
)
from src.modules.loan.services.loan_service import loan_response
from src.shared.schemas import MessageResponse

logger = logging.getLogger(__name__)

# Loans in each page of the desk
PAGE_SIZE = 30


# The loan of an id with its row locked until the commit: two librarians on the same loan wait for each other, and so
# do a librarian and its reader cancelling. 404 when there is none, 409 when it isn't in the status the change needs
async def _get_loan_in_status(db: AsyncSession, loan_id: uuid.UUID, wanted: LoanStatus, language: str) -> Loan:
    loan = await loan_repository.get_loan_by_id(db, loan_id, lock=True)
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_error_detail("LOAN_NOT_FOUND", language),
        )
    if loan.status != wanted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("LOAN_STATUS_CHANGED", language),
        )
    return loan


# One page of the loans for the desk, with their readers
async def get_loans(db: AsyncSession, query: AdminLoanQuery) -> AdminLoanPage:
    today = library_today()
    rows, total = await loan_repository.get_loans_for_librarians(db, query, today, PAGE_SIZE)
    return AdminLoanPage(
        loans=[
            AdminLoanResponse(
                **loan_response(loan, item).model_dump(),
                reader=LoanReader(id=user.id, name=user.name, email=user.email),
                overdue=loan.status == LoanStatus.ACTIVE and bool(loan.due_on) and loan.due_on < today,
            )
            for loan, item, user in rows
        ],
        total=total,
    )


# Hands a reserved copy over to its reader, who has to bring it back by due_on: from tomorrow to MAX_LOAN_DAYS away
async def pick_up(db: AsyncSession, loan_id: uuid.UUID, body: PickupSchema, language: str) -> MessageResponse:
    today = library_today()
    if not today < body.due_on <= today + timedelta(days=MAX_LOAN_DAYS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_detail("DUE_DATE_INVALID", language, {"detail": (MAX_LOAN_DAYS,)}),
        )
    loan = await _get_loan_in_status(db, loan_id, LoanStatus.REQUESTED, language)
    await loan_repository.pick_up_loan(db, loan.id, body.due_on)
    await db.commit()
    logger.info("Loan picked up", extra={"loan_id": loan.id})

    return MessageResponse(**get_response("LOAN_PICKED_UP", language))


# The reader brought the copy back
async def return_loan(db: AsyncSession, loan_id: uuid.UUID, language: str) -> MessageResponse:
    loan = await _get_loan_in_status(db, loan_id, LoanStatus.ACTIVE, language)
    await loan_repository.return_loan(db, loan.id)
    await db.commit()
    logger.info("Loan returned", extra={"loan_id": loan.id})

    return MessageResponse(**get_response("LOAN_RETURNED", language))


# Cancels a reservation for its reader: the copy goes back to the shelf
async def cancel(db: AsyncSession, loan_id: uuid.UUID, language: str) -> MessageResponse:
    loan = await _get_loan_in_status(db, loan_id, LoanStatus.REQUESTED, language)
    await loan_repository.cancel_loan(db, loan.id)
    await db.commit()
    logger.info("Loan cancelled by a librarian", extra={"loan_id": loan.id})

    return MessageResponse(**get_response("LOAN_CANCELLED", language))
