import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.models.item_model import Item
from src.modules.loan.models.loan_model import OPEN_STATUSES, Loan, LoanStatus

# No commit and no rollback here: the service commits once, at the end of its flow.
# On any error the request ends and closing the session (get_db) rolls it back


# Loans the reader has open, reserved or picked up
async def count_open_loans_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> int:
    query = select(func.count()).select_from(Loan).where(Loan.user_id == user_id, Loan.status.in_(OPEN_STATUSES))
    return await db.scalar(query) or 0


# Whether the reader already has this work reserved or picked up
async def is_item_open_for_user(db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID) -> bool:
    query = (
        select(Loan.id)
        .where(
            Loan.user_id == user_id,
            Loan.item_id == item_id,
            Loan.status.in_(OPEN_STATUSES),
        )
    )
    return bool(await db.scalar(query))


# Copies of each work held by an open loan, for the ones of these ids that have any
async def get_open_loan_counts_by_item_ids(db: AsyncSession, item_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    query = (
        select(Loan.item_id, func.count())
        .where(
            Loan.item_id.in_(item_ids),
            Loan.status.in_(OPEN_STATUSES),
        )
        .group_by(Loan.item_id)
    )
    return dict((await db.execute(query)).all())


# A reservation of the work. The flush gives it its id, and a second open loan of the same work fails here
async def create_loan(db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID) -> Loan:
    loan = Loan(user_id=user_id, item_id=item_id)
    db.add(loan)
    await db.flush()
    return loan


# The loans of the reader with their works, the newest first
async def get_loans_with_items_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> list[tuple[Loan, Item]]:
    query = (
        select(Loan, Item)
        .join(Item, Item.id == Loan.item_id)
        .where(Loan.user_id == user_id)
        .order_by(Loan.requested_at.desc(), Loan.id)
    )
    return [(row[0], row[1]) for row in (await db.execute(query)).all()]


# The loan of an id, None if there is none.
# lock: its row locked until the commit: a cancellation and a pick-up at the same moment wait for each other
async def get_loan_by_id(db: AsyncSession, loan_id: uuid.UUID, lock: bool) -> Loan | None:
    return await db.get(Loan, loan_id, with_for_update={"key_share": True} if lock else None, populate_existing=lock)


# Cancels the loan: its copy goes back to the shelf
async def cancel_loan(db: AsyncSession, loan_id: uuid.UUID) -> None:
    query = update(Loan).where(Loan.id == loan_id).values(status=LoanStatus.CANCELLED, cancelled_at=func.now())
    await db.execute(query)
