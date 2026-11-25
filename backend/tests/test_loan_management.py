import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from src.database.session import AsyncSessionLocal
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.catalog.models.item_model import Item, ItemKind
from src.modules.loan.loan_rules import library_today
from src.modules.loan.models.loan_model import Loan, LoanStatus
from src.modules.user.models.user_model import User, UserRole
from src.security.cookies import SESSION_DURATION
from src.security.tokens import new_token

HEADERS = {"Accept-Language": "ca"}


async def signed_in(client, role=UserRole.LIBRARIAN) -> None:
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        user = User(email="ana@vidal.cat", name="Ana Puig", role=role, password_hash="hash")
        db.add(user)
        await db.flush()
        db.add(AuthSession(user_id=user.id, token_hash=token_hash, ip="127.0.0.1",
                           expires_at=datetime.now(UTC) + SESSION_DURATION))
        await db.commit()
    client.cookies.set("session", token)


# A loan of a new reader and a new work
async def add_loan(
    status=LoanStatus.REQUESTED,
    title="Aloma",
    name="Marta Roig",
    due_on: date | None = None,
    requested_at: datetime | None = None,
) -> Loan:
    async with AsyncSessionLocal() as db:
        user = User(email=f"{uuid.uuid4().hex[:8]}@vidal.cat", name=name, role=UserRole.READER, password_hash="hash")
        item = Item(kind=ItemKind.BOOK, title=title, creator="Mercè Rodoreda", copies=1)
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


async def titles(client, **params) -> list[str]:
    response = await client.get("/admin/loans", params=params)
    assert response.status_code == 200
    return [loan["item"]["title"] for loan in response.json()["loans"]]


async def test_the_desk_shows_the_open_loans_reservations_first_then_by_due_day(client):
    await signed_in(client)
    today = library_today()
    await add_loan(LoanStatus.ACTIVE, "Tornar demà passat", due_on=today + timedelta(days=2))
    await add_loan(LoanStatus.ACTIVE, "Tornar demà", due_on=today + timedelta(days=1))
    await add_loan(LoanStatus.REQUESTED, "Reservat")
    await add_loan(LoanStatus.RETURNED, "Tornat")

    response = await client.get("/admin/loans")

    page = response.json()
    assert page["total"] == 3
    assert [loan["item"]["title"] for loan in page["loans"]] == ["Reservat", "Tornar demà", "Tornar demà passat"]
    assert page["loans"][0]["reader"]["name"] == "Marta Roig"


async def test_the_desk_filters_by_status_and_late_ones(client):
    await signed_in(client)
    today = library_today()
    await add_loan(LoanStatus.ACTIVE, "Endarrerit", due_on=today - timedelta(days=1))
    await add_loan(LoanStatus.ACTIVE, "Avui", due_on=today)
    await add_loan(LoanStatus.REQUESTED, "Reservat")
    await add_loan(LoanStatus.CANCELLED, "Anul·lat")

    assert await titles(client, show="requested") == ["Reservat"]
    assert await titles(client, show="active") == ["Endarrerit", "Avui"]
    assert await titles(client, show="overdue") == ["Endarrerit"]
    assert len(await titles(client, show="all")) == 4
    late = (await client.get("/admin/loans", params={"show": "active"})).json()["loans"]
    assert [loan["overdue"] for loan in late] == [True, False]


async def test_the_desk_searches_the_reader_and_the_title(client):
    await signed_in(client)
    await add_loan(title="Aloma", name="Marta Roig")
    await add_loan(title="Mirall trencat", name="Joan Pons")

    assert await titles(client, q="PONS") == ["Mirall trencat"]
    assert await titles(client, q="alom") == ["Aloma"]


async def test_a_reservation_is_picked_up_with_its_due_day(client):
    await signed_in(client)
    loan = await add_loan()
    due_on = library_today() + timedelta(days=21)

    response = await client.post(f"/admin/loans/{loan.id}/pickup", json={"due_on": due_on.isoformat()}, headers=HEADERS)

    assert response.json() == {"message": "Préstec lliurat"}
    picked = await get_loan(loan.id)
    assert (picked.status, picked.due_on) == (LoanStatus.ACTIVE, due_on) and picked.picked_up_at


@pytest.mark.parametrize("days", [0, -1, 91], ids=["today", "yesterday", "too far"])
async def test_a_due_day_outside_tomorrow_to_90_days_is_400(client, days):
    await signed_in(client)
    loan = await add_loan()
    due_on = library_today() + timedelta(days=days)

    response = await client.post(f"/admin/loans/{loan.id}/pickup", json={"due_on": due_on.isoformat()}, headers=HEADERS)

    assert response.status_code == 400
    assert response.json() == {"detail": "La data de retorn ha de ser entre demà i d'aquí a 90 dies"}
    assert (await get_loan(loan.id)).status == LoanStatus.REQUESTED


async def test_a_loan_is_returned(client):
    await signed_in(client)
    loan = await add_loan(LoanStatus.ACTIVE, due_on=library_today())

    response = await client.post(f"/admin/loans/{loan.id}/return", headers=HEADERS)

    assert response.json() == {"message": "Préstec retornat"}
    returned = await get_loan(loan.id)
    assert returned.status == LoanStatus.RETURNED and returned.returned_at


async def test_a_librarian_cancels_a_reservation(client):
    await signed_in(client)
    loan = await add_loan()

    response = await client.post(f"/admin/loans/{loan.id}/cancel", headers=HEADERS)

    assert response.json() == {"message": "Reserva anul·lada"}
    assert (await get_loan(loan.id)).status == LoanStatus.CANCELLED


# Each change only from the status it needs: a stale list gets a 409, never a second change
@pytest.mark.parametrize(("action", "status"), [
    ("pickup", LoanStatus.ACTIVE),
    ("return", LoanStatus.REQUESTED),
    ("return", LoanStatus.RETURNED),
    ("cancel", LoanStatus.ACTIVE),
])
async def test_a_change_from_the_wrong_status_is_409(client, action, status):
    await signed_in(client)
    loan = await add_loan(status, due_on=library_today())
    body = {"due_on": (library_today() + timedelta(days=7)).isoformat()} if action == "pickup" else None

    response = await client.post(f"/admin/loans/{loan.id}/{action}", json=body, headers=HEADERS)

    assert response.status_code == 409
    assert response.json() == {"detail": "Aquest préstec ja ha canviat: torna a carregar la llista"}
    assert (await get_loan(loan.id)).status == status


async def test_a_loan_that_doesnt_exist_is_404(client):
    await signed_in(client)

    response = await client.post(f"/admin/loans/{uuid.uuid4()}/return", headers=HEADERS)

    assert response.status_code == 404


# A reader cancelling while the desk hands it over: only one of them goes through
async def test_a_pickup_and_a_cancel_at_once_change_the_loan_once(client):
    await signed_in(client)
    loan = await add_loan()
    due = {"due_on": (library_today() + timedelta(days=7)).isoformat()}

    responses = await asyncio.gather(
        client.post(f"/admin/loans/{loan.id}/pickup", json=due),
        client.post(f"/admin/loans/{loan.id}/cancel"),
    )

    assert sorted(response.status_code for response in responses) == [200, 409]


@pytest.mark.parametrize("role", [UserRole.READER, None], ids=["reader", "signed out"])
async def test_only_a_librarian_works_the_desk(client, role):
    if role:
        await signed_in(client, role=role)
    loan = await add_loan()

    listed = await client.get("/admin/loans")
    cancelled = await client.post(f"/admin/loans/{loan.id}/cancel")

    assert listed.status_code == cancelled.status_code == (403 if role else 401)
    assert (await get_loan(loan.id)).status == LoanStatus.REQUESTED
