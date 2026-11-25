import asyncio
import uuid
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.database.session import AsyncSessionLocal
from src.main import app
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.catalog.models.item_model import Item, ItemKind
from src.modules.loan.models.loan_model import Loan, LoanStatus
from src.modules.loan.services import loan_service
from src.modules.user.models.user_model import User, UserRole
from src.security.cookies import SESSION_DURATION
from src.security.tokens import new_token

HEADERS = {"Accept-Language": "ca"}


# A browser signed in as a new user: a reader by default
async def signed_in(client, role=UserRole.READER, email="pau@vidal.cat") -> User:
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        user = User(email=email, name="Pau Vidal", role=role, password_hash="hash")
        db.add(user)
        await db.flush()
        db.add(AuthSession(user_id=user.id, token_hash=token_hash, ip="127.0.0.1",
                           expires_at=datetime.now(UTC) + SESSION_DURATION))
        await db.commit()
    client.cookies.set("session", token)
    return user


async def add_item(title="Aloma", copies=1) -> Item:
    async with AsyncSessionLocal() as db:
        item = Item(kind=ItemKind.BOOK, title=title, creator="Mercè Rodoreda", copies=copies)
        db.add(item)
        await db.commit()
        return item


# A loan of another reader, in any status
async def add_loan(item: Item, status=LoanStatus.REQUESTED, email="marta@vidal.cat") -> Loan:
    async with AsyncSessionLocal() as db:
        user = User(email=email, name="Marta Roig", role=UserRole.READER, password_hash="hash")
        db.add(user)
        await db.flush()
        loan = Loan(user_id=user.id, item_id=item.id, status=status)
        db.add(loan)
        await db.commit()
        return loan


async def loans() -> list[Loan]:
    async with AsyncSessionLocal() as db:
        return list(await db.scalars(select(Loan)))


async def reserve(client, item: Item):
    return await client.post("/loans", json={"item_id": str(item.id)}, headers=HEADERS)


async def test_a_reader_reserves_a_copy_and_sees_it_in_their_loans(client):
    user = await signed_in(client)
    item = await add_item()

    response = await reserve(client, item)

    assert response.status_code == 200
    assert response.json() == {"message": "Reservat. Passa a recollir-lo a la biblioteca en 3 dies"}
    [loan] = await loans()
    assert (loan.user_id, loan.item_id, loan.status) == (user.id, item.id, LoanStatus.REQUESTED)
    [mine] = (await client.get("/loans")).json()
    assert mine["status"] == "requested" and mine["item"]["title"] == "Aloma" and mine["item"]["cover"] is None
    pickup_until = datetime.fromisoformat(mine["pickup_until"]) - datetime.fromisoformat(mine["requested_at"])
    assert pickup_until == timedelta(days=3)


async def test_the_catalog_shows_the_copies_left(client):
    item = await add_item(copies=2)
    await add_loan(item)
    await add_loan(item, status=LoanStatus.RETURNED, email="joan@vidal.cat")

    listed = (await client.get("/catalog/items")).json()["items"][0]
    detail = (await client.get(f"/catalog/items/{item.id}")).json()

    assert listed["available"] == 1 and detail["available"] == 1


async def test_without_a_session_nothing_is_reserved(client):
    item = await add_item()

    response = await reserve(client, item)

    assert response.status_code == 401 and await loans() == []


async def test_a_work_with_every_copy_lent_is_409(client):
    await signed_in(client)
    item = await add_item()
    await add_loan(item, status=LoanStatus.ACTIVE)

    response = await reserve(client, item)

    assert response.status_code == 409 and response.json() == {"detail": "No en queda cap exemplar lliure"}


async def test_the_same_work_twice_is_409(client):
    await signed_in(client)
    item = await add_item(copies=3)
    await reserve(client, item)

    response = await reserve(client, item)

    assert response.status_code == 409 and response.json() == {"detail": "Ja tens aquesta obra reservada o en préstec"}


async def test_a_fourth_open_loan_is_409(client):
    await signed_in(client)
    for n in range(3):
        await reserve(client, await add_item(f"Obra {n}"))

    response = await reserve(client, await add_item("Obra 3"))

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Ja tens 3 préstecs oberts: torna'n un o anul·la una reserva per demanar-ne un altre",
    }


async def test_a_finished_loan_doesnt_count(client):
    await signed_in(client)
    item = await add_item()
    await reserve(client, item)
    [loan] = await loans()
    await client.delete(f"/loans/{loan.id}")

    response = await reserve(client, item)

    assert response.status_code == 200 and len(await loans()) == 2


# The account deleted while its reservation waited for its lock: the reservation answers like a session that ended
async def test_an_account_deleted_meanwhile_reserves_nothing(client, monkeypatch):
    await signed_in(client)
    item = await add_item()

    async def deleted(db, user_id, lock):
        return None

    monkeypatch.setattr(loan_service.user_repository, "get_user_by_id", deleted)

    response = await reserve(client, item)

    assert response.status_code == 401 and await loans() == []


async def test_an_unknown_work_is_404(client):
    await signed_in(client)

    response = await client.post("/loans", json={"item_id": str(uuid.uuid4())}, headers=HEADERS)

    assert response.status_code == 404 and response.json() == {"detail": "Aquesta obra no és al catàleg"}


# Three readers after the last copy at once: one gets it, never two
async def test_the_last_copy_goes_to_one_reader_only(client):
    item = await add_item()
    async with AsyncExitStack() as stack:
        readers = [
            await stack.enter_async_context(AsyncClient(transport=ASGITransport(app=app), base_url="http://test"))
            for _ in range(3)
        ]
        for n, reader in enumerate(readers):
            await signed_in(reader, email=f"lector{n}@vidal.cat")

        responses = await asyncio.gather(*(reserve(reader, item) for reader in readers))

    assert sorted(response.status_code for response in responses) == [200, 409, 409]
    assert len(await loans()) == 1


# One reader double-clicking several works at once: never more than 3 open
async def test_reservations_at_once_never_pass_the_limit(client):
    await signed_in(client)
    items = [await add_item(f"Obra {n}") for n in range(5)]

    responses = await asyncio.gather(*(reserve(client, item) for item in items))

    assert sorted(response.status_code for response in responses) == [200, 200, 200, 409, 409]


async def test_the_same_work_at_once_is_reserved_once(client):
    await signed_in(client)
    item = await add_item(copies=5)

    responses = await asyncio.gather(*(reserve(client, item) for _ in range(3)))

    assert sorted(response.status_code for response in responses) == [200, 409, 409]


async def test_a_reader_cancels_their_reservation(client):
    await signed_in(client)
    item = await add_item()
    await reserve(client, item)
    [loan] = await loans()

    response = await client.delete(f"/loans/{loan.id}", headers=HEADERS)

    assert response.json() == {"message": "Reserva anul·lada"}
    [cancelled] = await loans()
    assert cancelled.status == LoanStatus.CANCELLED and cancelled.cancelled_at


@pytest.mark.parametrize("status", [LoanStatus.ACTIVE, LoanStatus.RETURNED, LoanStatus.CANCELLED])
async def test_only_a_reservation_can_be_cancelled(client, status):
    user = await signed_in(client)
    item = await add_item()
    async with AsyncSessionLocal() as db:
        loan = Loan(user_id=user.id, item_id=item.id, status=status)
        db.add(loan)
        await db.commit()

    response = await client.delete(f"/loans/{loan.id}", headers=HEADERS)

    assert response.status_code == 409
    assert response.json() == {"detail": "Només es pot anul·lar una reserva que encara no s'ha recollit"}


# The loan of another reader is a 404, like one that doesn't exist
async def test_a_reader_cant_cancel_the_loan_of_another(client):
    await signed_in(client)
    other = await add_loan(await add_item())

    response = await client.delete(f"/loans/{other.id}", headers=HEADERS)
    missing = await client.delete(f"/loans/{uuid.uuid4()}", headers=HEADERS)

    assert response.status_code == 404 and response.json() == {"detail": "Aquest préstec no existeix"}
    assert missing.status_code == 404
    [loan] = await loans()
    assert loan.status == LoanStatus.REQUESTED


async def test_my_loans_are_only_mine_and_the_newest_first(client):
    await signed_in(client)
    await add_loan(await add_item("D'una altra"))
    await reserve(client, await add_item("Primera"))
    await reserve(client, await add_item("Segona"))

    response = await client.get("/loans")

    assert [loan["item"]["title"] for loan in response.json()] == ["Segona", "Primera"]


async def test_a_work_with_open_loans_cant_be_deleted_or_lose_copies(client):
    await signed_in(client, role=UserRole.LIBRARIAN, email="ana@vidal.cat")
    item = await add_item(copies=2)
    await add_loan(item)
    await add_loan(item, status=LoanStatus.ACTIVE, email="joan@vidal.cat")
    body = {"kind": "book", "title": "Aloma", "creator": "Mercè Rodoreda", "copies": 1}

    deleted = await client.delete(f"/admin/catalog/items/{item.id}", headers=HEADERS)
    fewer = await client.put(f"/admin/catalog/items/{item.id}", json=body, headers=HEADERS)
    same = await client.put(f"/admin/catalog/items/{item.id}", json={**body, "copies": 2})

    assert deleted.status_code == 409
    assert deleted.json() == {
        "detail": "Aquesta obra té préstecs oberts: s'han de tornar o anul·lar abans d'eliminar-la",
    }
    assert fewer.status_code == 409
    assert fewer.json() == {"detail": "Aquesta obra té 2 préstecs oberts: no pot tenir menys exemplars"}
    assert same.status_code == 200


async def test_a_work_with_only_finished_loans_can_be_deleted(client):
    await signed_in(client, role=UserRole.LIBRARIAN, email="ana@vidal.cat")
    item = await add_item()
    await add_loan(item, status=LoanStatus.RETURNED)

    response = await client.delete(f"/admin/catalog/items/{item.id}")

    assert response.status_code == 200 and await loans() == []
