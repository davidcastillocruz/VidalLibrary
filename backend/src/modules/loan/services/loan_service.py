import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.languages import get_error_detail, get_response
from src.modules.catalog.cover import cover_files
from src.modules.catalog.models.item_model import Item
from src.modules.catalog.repositories import item_repository
from src.modules.loan.loan_rules import MAX_OPEN_LOANS, PICKUP_TIME
from src.modules.loan.models.loan_model import Loan, LoanStatus
from src.modules.loan.repositories import loan_repository
from src.modules.loan.schemas.loan_schemas import LoanItem, LoanResponse, ReservationSchema
from src.modules.user.models.user_model import User
from src.modules.user.repositories import user_repository
from src.shared.schemas import MessageResponse

logger = logging.getLogger(__name__)


# 409 when the reader already has the work reserved or picked up: checked first, and caught from the database when
# two reservations of it arrive at once
def _already_borrowed(language: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=get_error_detail("ALREADY_BORROWED", language),
    )


# A loan as the page of the reader shows it
def _loan_response(loan: Loan, item: Item) -> LoanResponse:
    return LoanResponse(
        id=loan.id,
        status=loan.status,
        item=LoanItem(
            id=item.id,
            kind=item.kind,
            title=item.title,
            creator=item.creator,
            cover=cover_files.cover_version(item.cover_key) if item.cover_key else None,
        ),
        requested_at=loan.requested_at,
        pickup_until=loan.requested_at + PICKUP_TIME if loan.status == LoanStatus.REQUESTED else None,
        picked_up_at=loan.picked_up_at,
        due_on=loan.due_on,
        returned_at=loan.returned_at,
        cancelled_at=loan.cancelled_at,
    )


# Reserves a copy of the work for the signed-in reader, who picks it up at the library within PICKUP_TIME:
# - at most MAX_OPEN_LOANS open loans, and one of each work
# - never more open loans of a work than its copies
# The reader is locked first: two reservations of the same reader wait for each other and the second one counts the
# first. The work after it: two readers can't take its last copy at once
async def reserve(db: AsyncSession, body: ReservationSchema, language: str, user: User) -> MessageResponse:
    # Read again under its lock: an account deleted at this same moment has no session any more
    if not await user_repository.get_user_by_id(db, user.id, lock=True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=get_error_detail("NOT_AUTHENTICATED", language),
        )
    if await loan_repository.count_open_loans_by_user_id(db, user.id) >= MAX_OPEN_LOANS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("LOAN_LIMIT_REACHED", language, {"detail": (MAX_OPEN_LOANS,)}),
        )
    if await loan_repository.is_item_open_for_user(db, user.id, body.item_id):
        raise _already_borrowed(language)

    item = await item_repository.get_item_by_id(db, body.item_id, lock=True)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_error_detail("ITEM_NOT_FOUND", language),
        )
    open_loans = await loan_repository.get_open_loan_counts_by_item_ids(db, [item.id])
    if open_loans.get(item.id, 0) >= item.copies:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("NO_COPIES_LEFT", language),
        )

    try:
        loan = await loan_repository.create_loan(db, user.id, item.id)
    except IntegrityError:
        raise _already_borrowed(language) from None
    await db.commit()
    logger.info("Loan requested", extra={"loan_id": loan.id, "item_id": item.id})

    return MessageResponse(**get_response("LOAN_REQUESTED", language))


# The loans of the signed-in reader, the newest first
async def get_my_loans(db: AsyncSession, user: User) -> list[LoanResponse]:
    loans = await loan_repository.get_loans_with_items_by_user_id(db, user.id)
    return [_loan_response(loan, item) for loan, item in loans]


# Cancels a reservation of the signed-in reader that wasn't picked up: its copy goes back to the shelf. The loan of
# another reader is a 404, like one that doesn't exist. Locked: a librarian may be handing it over right now
async def cancel_my_loan(db: AsyncSession, loan_id: uuid.UUID, language: str, user: User) -> MessageResponse:
    loan = await loan_repository.get_loan_by_id(db, loan_id, lock=True)
    if not loan or loan.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_error_detail("LOAN_NOT_FOUND", language),
        )
    if loan.status != LoanStatus.REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=get_error_detail("LOAN_NOT_CANCELLABLE", language),
        )
    await loan_repository.cancel_loan(db, loan.id)
    await db.commit()
    logger.info("Loan cancelled by its reader", extra={"loan_id": loan.id})

    return MessageResponse(**get_response("LOAN_CANCELLED", language))
