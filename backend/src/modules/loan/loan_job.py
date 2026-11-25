import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import settings
from src.database.session import AsyncSessionLocal
from src.mail.emails import build_due_soon_email, build_overdue_email, build_reservation_expired_email
from src.mail.sender import send_email
from src.modules.loan.loan_rules import DUE_SOON_DAYS, PICKUP_TIME, format_day, library_today
from src.modules.loan.repositories import loan_repository

logger = logging.getLogger(__name__)

# How often the loans are looked at, in seconds: a reservation expires to the hour, and a warning about a day can come
# at any hour of it
LOAN_JOB_INTERVAL = 60 * 60

# Loans taken in one go: the next ones wait for the next go of the same round
LOAN_JOB_BATCH = 100


# Sends the warnings of a batch already committed. A failed email is only logged (send_email): the loan stays warned,
# it is never sent twice
async def _send(emails: list[tuple[str, str, str]]) -> None:
    for subject, recipient, html in emails:
        await send_email(subject, [recipient], html)


# Cancels the reservations nobody picked up in PICKUP_TIME and tells their readers, in the main language: readers have
# none of their own. The emails are built before the commit: one that can't be built (a text missing) rolls the batch
# back instead of leaving it cancelled with nobody told. Returns how many
async def expire_reservations(db: AsyncSession) -> int:
    expired = await loan_repository.expire_reservations(db, datetime.now(UTC) - PICKUP_TIME, LOAN_JOB_BATCH)
    emails = []
    for loan in expired:
        subject, html = build_reservation_expired_email(settings.MAIN_LANGUAGE, loan.name, loan.title, loan.item_id)
        emails.append((subject, loan.email, html))
    await db.commit()
    for loan in expired:
        logger.info("Reservation expired", extra={"loan_id": loan.loan_id})
    await _send(emails)
    return len(expired)


# Tells the readers whose loans are due in the next DUE_SOON_DAYS days, once per loan, like expire_reservations.
# Returns how many
async def warn_due_soon(db: AsyncSession) -> int:
    today = library_today()
    due = await loan_repository.claim_due_soon_loans(db, today, today + timedelta(days=DUE_SOON_DAYS), LOAN_JOB_BATCH)
    emails = []
    for loan in due:
        day = format_day(loan.due_on) if loan.due_on else ""
        subject, html = build_due_soon_email(settings.MAIN_LANGUAGE, loan.name, loan.title, day)
        emails.append((subject, loan.email, html))
    await db.commit()
    for loan in due:
        logger.info("Due soon warning sent", extra={"loan_id": loan.loan_id})
    await _send(emails)
    return len(due)


# Tells the readers whose loans are late, once per loan, like expire_reservations. Returns how many
async def warn_overdue(db: AsyncSession) -> int:
    late = await loan_repository.claim_overdue_loans(db, library_today(), LOAN_JOB_BATCH)
    emails = []
    for loan in late:
        day = format_day(loan.due_on) if loan.due_on else ""
        subject, html = build_overdue_email(settings.MAIN_LANGUAGE, loan.name, loan.title, day)
        emails.append((subject, loan.email, html))
    await db.commit()
    for loan in late:
        logger.info("Overdue warning sent", extra={"loan_id": loan.loan_id})
    await _send(emails)
    return len(late)


# One round: each step in batches until a batch isn't full
async def run_loan_round(db: AsyncSession) -> None:
    for step in (expire_reservations, warn_due_soon, warn_overdue):
        while await step(db) == LOAN_JOB_BATCH:
            pass


# Runs while the app runs (lifespan): a round every LOAN_JOB_INTERVAL. A failure is logged and tried again in the next
# round: it never stops the task. Several processes of the app can run it at once: each takes only the loans no other
# one has locked
async def run_loan_job() -> None:
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await run_loan_round(db)
        except Exception:
            logger.exception("The round of the loans failed")
        await asyncio.sleep(LOAN_JOB_INTERVAL)
