import uuid
from datetime import date, datetime
from typing import NamedTuple

from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.models.item_model import Item
from src.modules.loan.models.loan_model import OPEN_STATUSES, Loan, LoanStatus
from src.modules.loan.schemas.loan_schemas import AdminLoanQuery
from src.modules.user.models.user_model import User

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


# Open loans of each reader, for the ones of these ids that have any
async def get_open_loan_counts_by_user_ids(db: AsyncSession, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    query = (
        select(Loan.user_id, func.count())
        .where(
            Loan.user_id.in_(user_ids),
            Loan.status.in_(OPEN_STATUSES),
        )
        .group_by(Loan.user_id)
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


# One page of the loans that match the query with their works and readers, and how many match in all. The open ones
# by the day they need the desk: the reservations by when they were made, the loans by their due day
async def get_loans_for_librarians(
    db: AsyncSession, query: AdminLoanQuery, today: date, limit: int,
) -> tuple[list[tuple[Loan, Item, User]], int]:
    conditions = []
    if query.show == "open":
        conditions.append(Loan.status.in_(OPEN_STATUSES))
    elif query.show == "requested":
        conditions.append(Loan.status == LoanStatus.REQUESTED)
    elif query.show == "active":
        conditions.append(Loan.status == LoanStatus.ACTIVE)
    elif query.show == "overdue":
        conditions.append(Loan.status == LoanStatus.ACTIVE)
        conditions.append(Loan.due_on < today)
    if query.q and query.q.strip():
        # autoescape: a % or a _ in the search is looked for as it is, not as a wildcard
        search = query.q.strip().lower()
        conditions.append(or_(
            func.lower(User.name).contains(search, autoescape=True),
            func.lower(User.email).contains(search, autoescape=True),
            func.lower(Item.title).contains(search, autoescape=True),
        ))
    matching = (
        select(Loan, Item, User)
        .join(Item, Item.id == Loan.item_id)
        .join(User, User.id == Loan.user_id)
        .where(*conditions)
    )
    total = await db.scalar(select(func.count()).select_from(matching.subquery())) or 0
    # Everything at once: the newest first, like a history
    order = (
        (Loan.requested_at.desc(), Loan.id)
        if query.show == "all"
        else (Loan.due_on.asc().nulls_first(), Loan.requested_at, Loan.id)
    )
    page = matching.order_by(*order).offset((query.page - 1) * limit).limit(limit)
    return [(row[0], row[1], row[2]) for row in (await db.execute(page)).all()], total


# Hands over a reserved copy: the loan starts now and has to come back by due_on
async def pick_up_loan(db: AsyncSession, loan_id: uuid.UUID, due_on: date) -> None:
    query = (
        update(Loan)
        .where(Loan.id == loan_id)
        .values(status=LoanStatus.ACTIVE, picked_up_at=func.now(), due_on=due_on)
    )
    await db.execute(query)


# The copy came back: it is on the shelf again
async def return_loan(db: AsyncSession, loan_id: uuid.UUID) -> None:
    query = update(Loan).where(Loan.id == loan_id).values(status=LoanStatus.RETURNED, returned_at=func.now())
    await db.execute(query)


# A loan a warning is sent about, with what the email needs
class WarnedLoan(NamedTuple):
    loan_id: uuid.UUID
    item_id: uuid.UUID
    email: str
    name: str
    title: str
    due_on: date | None


# Changes up to limit loans that match where with values, and returns them with their readers and works. They are
# locked (FOR NO KEY UPDATE: no key changes) and the ones another process already has are skipped (SKIP LOCKED), so
# each row changes once: several processes running loan_job never take the same loan
async def _claim_loans(
    db: AsyncSession, where: list[ColumnElement[bool]], values: dict, limit: int,
) -> list[WarnedLoan]:
    ids = select(Loan.id).where(*where).order_by(Loan.id).limit(limit).with_for_update(skip_locked=True, key_share=True)
    query = (
        update(Loan)
        .where(Loan.id.in_(ids.scalar_subquery()), Loan.user_id == User.id, Loan.item_id == Item.id)
        .values(**values)
        .returning(Loan.id, Loan.item_id, User.email, User.name, Item.title, Loan.due_on)
    )
    return [WarnedLoan(*row) for row in (await db.execute(query)).all()]


# Cancels the reservations made before requested_before: nobody picked them up, their copies go back to the shelf
async def expire_reservations(db: AsyncSession, requested_before: datetime, limit: int) -> list[WarnedLoan]:
    where = [Loan.status == LoanStatus.REQUESTED, Loan.requested_at < requested_before]
    return await _claim_loans(db, where, {"status": LoanStatus.CANCELLED, "cancelled_at": func.now()}, limit)


# Marks as warned the loans due from today to last_day whose readers weren't told yet
async def claim_due_soon_loans(db: AsyncSession, today: date, last_day: date, limit: int) -> list[WarnedLoan]:
    where = [
        Loan.status == LoanStatus.ACTIVE,
        Loan.due_on >= today,
        Loan.due_on <= last_day,
        Loan.due_soon_warned_at.is_(None),
    ]
    return await _claim_loans(db, where, {"due_soon_warned_at": func.now()}, limit)


# Marks as warned the loans late (due before today) whose readers weren't told yet
async def claim_overdue_loans(db: AsyncSession, today: date, limit: int) -> list[WarnedLoan]:
    where = [Loan.status == LoanStatus.ACTIVE, Loan.due_on < today, Loan.overdue_warned_at.is_(None)]
    return await _claim_loans(db, where, {"overdue_warned_at": func.now()}, limit)
