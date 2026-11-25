from sqlalchemy import func, select

from src.commands import seed_demo
from src.database.session import AsyncSessionLocal
from src.modules.catalog.models.item_model import Item
from src.modules.loan.models.loan_model import Loan, LoanStatus
from src.modules.user.models.user_model import User, UserRole
from src.security.passwords import verify_password


async def count(model) -> int:
    async with AsyncSessionLocal() as db:
        return await db.scalar(select(func.count()).select_from(model)) or 0


async def test_the_demo_fills_an_empty_library(clean_state):
    assert await seed_demo.seed() == 0

    assert await count(Item) == len(seed_demo.WORKS)
    async with AsyncSessionLocal() as db:
        librarian = await db.scalar(select(User).where(User.email == "biblioteca@vidal.example"))
        statuses = set(await db.scalars(select(Loan.status)))
    assert librarian and librarian.role == UserRole.LIBRARIAN and librarian.password_hash
    assert await verify_password(seed_demo.DEMO_PASSWORD, librarian.password_hash)
    assert statuses == set(LoanStatus)


async def test_the_demo_goes_only_into_an_empty_catalog(clean_state, capsys):
    await seed_demo.seed()

    assert await seed_demo.seed() == 1
    assert await count(Item) == len(seed_demo.WORKS)
    assert "already has works" in capsys.readouterr().err


async def test_the_demo_never_runs_in_production(clean_state, monkeypatch):
    monkeypatch.setattr(seed_demo.settings, "APP_MODE", "production")

    assert await seed_demo.seed() == 1
    assert await count(User) == 0


# Every loan of the demo happens in order: requested, then picked up or cancelled, then returned
async def test_the_demo_loans_have_their_dates_in_order(clean_state):
    await seed_demo.seed()

    async with AsyncSessionLocal() as db:
        for loan in await db.scalars(select(Loan)):
            later = [moment for moment in (loan.picked_up_at, loan.cancelled_at) if moment]
            assert all(loan.requested_at < moment for moment in later)
            if loan.returned_at:
                assert loan.picked_up_at and loan.due_on and loan.picked_up_at < loan.returned_at
