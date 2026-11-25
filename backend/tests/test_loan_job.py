import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from src.database.session import AsyncSessionLocal
from src.modules.catalog.models.item_model import Item, ItemKind
from src.modules.loan import loan_job
from src.modules.loan.loan_rules import library_today
from src.modules.loan.models.loan_model import Loan, LoanStatus
from src.modules.user.models.user_model import User, UserRole


# The emails the job would send: (subject, recipient, html)
@pytest.fixture
def sent(monkeypatch, clean_state):
    emails: list[tuple[str, str, str]] = []

    async def send(subject: str, recipients: list[str], body: str) -> None:
        emails.extend((subject, recipient, body) for recipient in recipients)

    monkeypatch.setattr(loan_job, "send_email", send)
    return emails


async def add_loan(
    status=LoanStatus.ACTIVE,
    due_on: date | None = None,
    requested_at: datetime | None = None,
    email="marta@vidal.cat",
) -> Loan:
    async with AsyncSessionLocal() as db:
        user = User(email=email, name="Marta", role=UserRole.READER, password_hash="hash")
        item = Item(kind=ItemKind.BOOK, title="Aloma", creator="Mercè Rodoreda", copies=1)
        db.add_all([user, item])
        await db.flush()
        loan = Loan(user_id=user.id, item_id=item.id, status=status, due_on=due_on,
                    requested_at=requested_at or datetime.now(UTC))
        db.add(loan)
        await db.commit()
        return loan


async def get_loan(loan_id) -> Loan:
    async with AsyncSessionLocal() as db:
        loan = await db.scalar(select(Loan).where(Loan.id == loan_id))
        assert loan
        return loan


async def run_round() -> None:
    async with AsyncSessionLocal() as db:
        await loan_job.run_loan_round(db)


async def test_a_reservation_not_picked_up_in_3_days_expires_and_its_reader_is_told(sent):
    now = datetime.now(UTC)
    old = await add_loan(LoanStatus.REQUESTED, requested_at=now - timedelta(days=3, minutes=1))
    recent = await add_loan(LoanStatus.REQUESTED, requested_at=now - timedelta(days=2), email="joan@vidal.cat")

    await run_round()

    expired = await get_loan(old.id)
    assert expired.status == LoanStatus.CANCELLED and expired.cancelled_at
    assert (await get_loan(recent.id)).status == LoanStatus.REQUESTED
    [(subject, recipient, html)] = sent
    assert subject == "La teva reserva ha caducat" and recipient == "marta@vidal.cat"
    assert "«Aloma»" in html and f"/items/{old.item_id}" in html


@pytest.mark.parametrize("days", [0, 1, 2])
async def test_a_loan_due_in_the_next_2_days_is_warned_once(sent, days):
    due_on = library_today() + timedelta(days=days)
    loan = await add_loan(due_on=due_on)

    await run_round()
    await run_round()

    [(subject, _, html)] = sent
    assert subject == "«Aloma» s'ha de tornar aviat"
    assert f"com a tard el {due_on.day}/{due_on.month}/{due_on.year}" in html and "/loans" in html
    assert (await get_loan(loan.id)).due_soon_warned_at


async def test_a_loan_due_later_isnt_warned_yet(sent):
    await add_loan(due_on=library_today() + timedelta(days=3))

    await run_round()

    assert sent == []


# Warned that it was due soon, and then that it is late: two warnings, each once
async def test_a_late_loan_is_warned_once_more(sent):
    loan = await add_loan(due_on=library_today() - timedelta(days=1))
    async with AsyncSessionLocal() as db:
        stored = await db.get(Loan, loan.id)
        assert stored
        stored.due_soon_warned_at = datetime.now(UTC) - timedelta(days=2)
        await db.commit()

    await run_round()
    await run_round()

    assert [subject for subject, _, _ in sent] == ["«Aloma» s'havia de tornar"]
    assert (await get_loan(loan.id)).overdue_warned_at


@pytest.mark.parametrize("status", [LoanStatus.RETURNED, LoanStatus.CANCELLED])
async def test_a_finished_loan_is_never_warned(sent, status):
    await add_loan(status, due_on=library_today() - timedelta(days=5),
                   requested_at=datetime.now(UTC) - timedelta(days=30))

    await run_round()

    assert sent == []


# More than one batch: the round goes on until a batch isn't full
async def test_a_round_takes_every_batch(sent, monkeypatch):
    monkeypatch.setattr(loan_job, "LOAN_JOB_BATCH", 2)
    for n in range(5):
        await add_loan(due_on=library_today(), email=f"lector{n}@vidal.cat")

    await run_round()

    assert len(sent) == 5


# Two processes running the job at once: each loan is warned once
async def test_two_rounds_at_once_warn_each_loan_once(sent):
    for n in range(10):
        await add_loan(due_on=library_today(), email=f"lector{n}@vidal.cat")

    await asyncio.gather(run_round(), run_round())

    assert sorted(recipient for _, recipient, _ in sent) == sorted(f"lector{n}@vidal.cat" for n in range(10))


# A failing round is logged and the task goes on to the next one
async def test_a_failed_round_doesnt_stop_the_job(monkeypatch, caplog):
    rounds = 0

    async def failing_round(db) -> None:
        nonlocal rounds
        rounds += 1
        raise RuntimeError("database down")

    async def stop_after_two(seconds: float) -> None:
        if rounds == 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(loan_job, "run_loan_round", failing_round)
    monkeypatch.setattr(loan_job.asyncio, "sleep", stop_after_two)

    with pytest.raises(asyncio.CancelledError):
        await loan_job.run_loan_job()

    assert rounds == 2 and "The round of the loans failed" in caplog.text


# An email that can't be built (a text missing in the main language) rolls its batch back: no reservation is left
# cancelled, and no loan warned, with nobody told
async def test_a_batch_whose_email_cant_be_built_is_rolled_back(sent, monkeypatch):
    loan = await add_loan(LoanStatus.REQUESTED, requested_at=datetime.now(UTC) - timedelta(days=4))

    def broken(*args):
        raise KeyError("RESERVATION_EXPIRED_EMAIL")

    monkeypatch.setattr(loan_job, "build_reservation_expired_email", broken)

    with pytest.raises(KeyError):
        await run_round()

    assert (await get_loan(loan.id)).status == LoanStatus.REQUESTED and sent == []
