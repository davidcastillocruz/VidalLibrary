import asyncio
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from src.database.session import AsyncSessionLocal
from src.main import app
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.auth.models.password_token_model import PasswordToken, PasswordTokenPurpose
from src.modules.auth.repositories import password_token_repository
from src.modules.catalog.models.item_model import Item, ItemKind
from src.modules.loan.models.loan_model import Loan, LoanStatus
from src.modules.user.models.user_model import User, UserRole
from src.modules.user.repositories import user_repository
from src.modules.user.services import user_management_service
from src.security.cookies import SESSION_DURATION
from src.security.tokens import hash_token, new_token

HEADERS = {"Accept-Language": "ca"}
NEW = {"email": " Pau@Vidal.cat ", "name": " Pau Vidal ", "role": "reader"}


@pytest.fixture(autouse=True)
def sent(monkeypatch):
    emails: list[tuple[str, list[str], str]] = []

    async def fake_send_email(subject: str, recipients: list[str], body: str) -> bool:
        emails.append((subject, recipients, body))
        return True

    monkeypatch.setattr(user_management_service, "send_email", fake_send_email)
    return emails


async def add_user(email: str, name="Marta Roig", role=UserRole.READER, password_hash: str | None = "hash") -> User:
    async with AsyncSessionLocal() as db:
        user = User(email=email, name=name, role=role, password_hash=password_hash)
        db.add(user)
        await db.commit()
        return user


# A browser signed in as a librarian, or as a reader
async def signed_in(client, role=UserRole.LIBRARIAN, email="ana@vidal.cat") -> User:
    user = await add_user(email, name="Ana Puig", role=role)
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        db.add(AuthSession(user_id=user.id, token_hash=token_hash, ip="127.0.0.1",
                           expires_at=datetime.now(UTC) + SESSION_DURATION))
        await db.commit()
    client.cookies.set("session", token)
    return user


async def add_loan(user: User, status=LoanStatus.ACTIVE) -> None:
    async with AsyncSessionLocal() as db:
        item = Item(kind=ItemKind.BOOK, title="Aloma", creator="Mercè Rodoreda", copies=1)
        db.add(item)
        await db.flush()
        db.add(Loan(user_id=user.id, item_id=item.id, status=status))
        await db.commit()


async def get_user(email: str) -> User | None:
    async with AsyncSessionLocal() as db:
        return await db.scalar(select(User).where(User.email == email))


async def test_the_accounts_are_listed_by_name_with_their_loans(client):
    await signed_in(client)
    reader = await add_user("marta@vidal.cat")
    await add_user("biel@vidal.cat", name="biel Ferrer", password_hash=None)
    await add_loan(reader)
    await add_loan(reader, status=LoanStatus.RETURNED)

    response = await client.get("/admin/users")

    page = response.json()
    assert page["total"] == 3
    assert [user["name"] for user in page["users"]] == ["Ana Puig", "biel Ferrer", "Marta Roig"]
    assert [user["invited"] for user in page["users"]] == [False, True, False]
    assert [user["open_loans"] for user in page["users"]] == [0, 0, 1]


async def test_the_accounts_are_filtered_by_role_and_searched(client):
    await signed_in(client)
    await add_user("marta@vidal.cat")
    await add_user("joan@escola.cat", name="Joan Pons")

    by_role = (await client.get("/admin/users", params={"role": "librarian"})).json()["users"]
    by_email = (await client.get("/admin/users", params={"q": "ESCOLA"})).json()["users"]

    assert [user["name"] for user in by_role] == ["Ana Puig"]
    assert [user["name"] for user in by_email] == ["Joan Pons"]


async def test_a_librarian_creates_an_account_and_its_owner_is_invited(client, sent):
    await signed_in(client)

    response = await client.post("/admin/users", json=NEW, headers=HEADERS)

    assert response.status_code == 201
    assert response.json()["message"] == "Compte creat: hem enviat la invitació per correu"
    user = await get_user("pau@vidal.cat")
    assert user and str(user.id) == response.json()["id"]
    assert (user.name, user.role, user.password_hash) == ("Pau Vidal", UserRole.READER, None)
    [(_, recipients, html)] = sent
    assert recipients == ["pau@vidal.cat"] and '<html lang="ca">' in html and "/invitation?token=" in html


async def test_an_email_with_an_account_is_409(client, sent):
    await signed_in(client)
    await add_user("pau@vidal.cat")

    response = await client.post("/admin/users", json=NEW, headers=HEADERS)

    assert response.status_code == 409 and response.json() == {"detail": "Ja hi ha un compte amb aquest correu"}
    assert sent == []


# Two librarians adding the same email at once: the database stops the second one, never a 500
async def test_the_same_account_at_once_is_created_once(client):
    await signed_in(client)

    responses = await asyncio.gather(*(client.post("/admin/users", json=NEW) for _ in range(3)))

    assert sorted(response.status_code for response in responses) == [201, 409, 409]


async def test_the_invitation_is_sent_again_and_only_the_new_link_works(client, sent):
    await signed_in(client)
    created = await client.post("/admin/users", json=NEW)
    user_id = created.json()["id"]

    response = await client.post(f"/admin/users/{user_id}/invitation", headers=HEADERS)

    assert response.json() == {"message": "Invitació enviada de nou"}
    tokens = [match[1] for _, _, html in sent if (match := re.search(r"token=([\w-]+)", html))]
    client.cookies.clear()
    first = await client.post("/auth/password/reset", json={"token": tokens[0], "password": "una-contrasenya-llarga"})
    second = await client.post("/auth/password/reset", json={"token": tokens[1], "password": "una-contrasenya-llarga"})
    assert first.status_code == 400 and second.status_code == 200


async def test_an_account_with_a_password_isnt_invited_again(client, sent):
    await signed_in(client)
    user = await add_user("marta@vidal.cat")

    response = await client.post(f"/admin/users/{user.id}/invitation", headers=HEADERS)

    assert response.status_code == 409 and sent == []
    async with AsyncSessionLocal() as db:
        assert list(await db.scalars(select(PasswordToken))) == []


async def test_a_librarian_renames_an_account_and_changes_its_role(client):
    await signed_in(client)
    user = await add_user("marta@vidal.cat")

    response = await client.put(f"/admin/users/{user.id}", json={"name": "Marta Roig i Pla", "role": "librarian"},
                                headers=HEADERS)

    assert response.json() == {"message": "Compte desat"}
    saved = await get_user("marta@vidal.cat")
    assert saved and (saved.name, saved.role) == ("Marta Roig i Pla", UserRole.LIBRARIAN)


# A demoted librarian loses the panel on its next request, with the same session
async def test_a_new_role_takes_effect_at_once(client):
    librarian = await signed_in(client)
    async with AsyncSessionLocal() as db:
        stored = await db.get(User, librarian.id)
        assert stored
        stored.role = UserRole.READER
        await db.commit()

    response = await client.get("/admin/users")

    assert response.status_code == 403


async def test_a_librarian_cant_take_away_its_own_role(client):
    librarian = await signed_in(client)

    response = await client.put(f"/admin/users/{librarian.id}", json={"name": "Ana", "role": "reader"},
                                headers=HEADERS)

    assert response.status_code == 409
    saved = await get_user("ana@vidal.cat")
    assert saved and saved.role == UserRole.LIBRARIAN


async def test_a_librarian_deletes_an_account_with_its_finished_loans(client):
    await signed_in(client)
    user = await add_user("marta@vidal.cat")
    await add_loan(user, status=LoanStatus.RETURNED)

    response = await client.delete(f"/admin/users/{user.id}", headers=HEADERS)

    assert response.json() == {"message": "Compte eliminat"} and not await get_user("marta@vidal.cat")
    async with AsyncSessionLocal() as db:
        assert list(await db.scalars(select(Loan))) == []


async def test_an_account_with_open_loans_isnt_deleted(client):
    await signed_in(client)
    user = await add_user("marta@vidal.cat")
    await add_loan(user, status=LoanStatus.REQUESTED)

    response = await client.delete(f"/admin/users/{user.id}", headers=HEADERS)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Aquest compte té préstecs oberts: s'han de tornar o anul·lar abans d'eliminar-lo",
    }


async def test_a_librarian_cant_delete_its_own_account(client):
    librarian = await signed_in(client)

    response = await client.delete(f"/admin/users/{librarian.id}", headers=HEADERS)

    assert response.status_code == 409 and await get_user("ana@vidal.cat")


@pytest.mark.parametrize("call", ["put", "delete", "invite"])
async def test_an_account_that_doesnt_exist_is_404(client, call):
    await signed_in(client)
    path = f"/admin/users/{uuid.uuid4()}"

    if call == "put":
        response = await client.put(path, json={"name": "X", "role": "reader"}, headers=HEADERS)
    elif call == "delete":
        response = await client.delete(path, headers=HEADERS)
    else:
        response = await client.post(f"{path}/invitation", headers=HEADERS)

    assert response.status_code == 404 and response.json() == {"detail": "Aquest compte no existeix"}


@pytest.mark.parametrize("role", [UserRole.READER, None], ids=["reader", "signed out"])
async def test_only_a_librarian_manages_the_accounts(client, role):
    if role:
        await signed_in(client, role=role)

    listed = await client.get("/admin/users")
    created = await client.post("/admin/users", json=NEW)

    assert listed.status_code == created.status_code == (403 if role else 401)
    assert not await get_user("pau@vidal.cat")


# Two librarians taking each other away at once: the second one finds the first change done, and the library keeps one
@pytest.mark.parametrize("change", ["role", "delete"])
async def test_two_librarians_never_take_each_other_away_at_once(client, change):
    ana = await signed_in(client)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
        joan = await signed_in(other, email="joan@vidal.cat")

        def take_away(browser, user):
            if change == "role":
                body = {"name": user.name, "role": "reader"}
                return browser.put(f"/admin/users/{user.id}", json=body, headers=HEADERS)
            return browser.delete(f"/admin/users/{user.id}", headers=HEADERS)

        responses = await asyncio.gather(take_away(client, joan), take_away(other, ana))

    assert sorted(response.status_code for response in responses) == [200, 409]
    refused = next(response for response in responses if response.status_code == 409)
    assert refused.json() == {"detail": "La biblioteca no es pot quedar sense cap bibliotecari"}
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.LIBRARIAN)) == 1


# Accepting an invitation and sending it again at the same moment: either the account got its password and nothing is
# sent, or the new link is the only one that works. Never a second link that could change the password later
async def test_an_invitation_accepted_while_it_is_sent_again_leaves_no_link_behind(client, sent):
    await signed_in(client)
    created = await client.post("/admin/users", json=NEW)
    user_id = created.json()["id"]
    [token] = [match[1] for _, _, html in sent if (match := re.search(r"token=([\w-]+)", html))]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as guest:
        accepted, resent = await asyncio.gather(
            guest.post("/auth/password/reset", json={"token": token, "password": "una-contrasenya-llarga"}),
            client.post(f"/admin/users/{user_id}/invitation", headers=HEADERS),
        )

    async with AsyncSessionLocal() as db:
        user = await db.get(User, uuid.UUID(user_id))
        pending = list(await db.scalars(select(PasswordToken).where(
            PasswordToken.user_id == uuid.UUID(user_id),
            PasswordToken.used_at.is_(None),
            PasswordToken.revoked_at.is_(None),
        )))
    if accepted.status_code == 200:
        assert resent.status_code == 409 and user and user.password_hash and pending == []
    else:
        assert resent.status_code == 200 and user and not user.password_hash and len(pending) == 1


# Deleting an account while its owner chooses a password from a link: the deletion takes the links first, in the order
# of opening one (the link, then the account), so it waits instead of both waiting for each other (a deadlock, a 500)
async def test_deleting_an_account_waits_for_a_password_being_chosen(client):
    librarian = await add_user("ana@vidal.cat", name="Ana Puig", role=UserRole.LIBRARIAN)
    user = await add_user("marta@vidal.cat", password_hash=None)
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        db.add(PasswordToken(user_id=user.id, purpose=PasswordTokenPurpose.INVITATION, token_hash=token_hash,
                             expires_at=datetime.now(UTC) + timedelta(days=7)))
        await db.commit()

    async with AsyncSessionLocal() as choosing, AsyncSessionLocal() as deleting:
        assert await password_token_repository.get_valid_password_token_with_user(choosing, hash_token(token))
        await deleting.execute(text("SET LOCAL lock_timeout = '5s'"))
        deletion = asyncio.create_task(user_management_service.delete_user(deleting, user.id, "ca", librarian))
        await asyncio.sleep(0.3)

        # The deletion waits for the link, and hasn't locked the account: the password can be saved
        await choosing.execute(text("SET LOCAL lock_timeout = '300ms'"))
        await user_repository.set_password_hash(choosing, user.id, "hash")
        assert not deletion.done()
        await choosing.commit()
        await deletion

    assert not await get_user("marta@vidal.cat")
