from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.database.session import AsyncSessionLocal
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.auth.models.password_token_model import PasswordToken, PasswordTokenPurpose
from src.modules.auth.services import auth_service
from src.modules.user.models.user_model import User
from src.security.cookies import SESSION_DURATION
from src.security.passwords import hash_password, verify_password
from src.security.tokens import hash_token, new_token

OLD_PASSWORD = "contrasenya-vella"
NEW_PASSWORD = "contrasenya-nova-llarga"
HEADERS = {"Accept-Language": "ca"}
EMAIL_SENT = {"message": "Si aquest correu té compte, t'hem enviat un enllaç per canviar la contrasenya"}
INVALID = {"detail": "Aquest enllaç no és vàlid o ha caducat. Demana'n un de nou"}


# The emails the service would send: (subject, recipients, html)
@pytest.fixture(autouse=True)
def sent(monkeypatch):
    emails: list[tuple[str, list[str], str]] = []

    async def fake_send_email(subject: str, recipients: list[str], body: str) -> bool:
        emails.append((subject, recipients, body))
        return True

    monkeypatch.setattr(auth_service, "send_email", fake_send_email)
    return emails


async def create_user(email="laia@test.dev", password: str | None = OLD_PASSWORD) -> User:
    async with AsyncSessionLocal() as db:
        user = User(email=email, name="Laia Puig", password_hash=await hash_password(password) if password else None)
        db.add(user)
        await db.commit()
        return user


# A link of the user: returns its token
async def create_link(user: User, purpose=PasswordTokenPurpose.PASSWORD_RESET, expires_in=timedelta(minutes=30)) -> str:
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        db.add(PasswordToken(user_id=user.id, purpose=purpose, token_hash=token_hash,
                             expires_at=datetime.now(UTC) + expires_in))
        await db.commit()
    return token


async def rows(model) -> list:
    async with AsyncSessionLocal() as db:
        return list(await db.scalars(select(model)))


async def forgot(client, email="laia@test.dev"):
    return await client.post("/auth/password/forgot", json={"email": email}, headers=HEADERS)


async def reset(client, token: str, password: str = NEW_PASSWORD):
    return await client.post("/auth/password/reset", json={"token": token, "password": password}, headers=HEADERS)


async def test_an_account_gets_the_link(client, sent):
    user = await create_user()

    response = await forgot(client, "Laia@Test.dev")

    assert response.status_code == 200 and response.json() == EMAIL_SENT
    [link] = await rows(PasswordToken)
    assert link.user_id == user.id and link.purpose == PasswordTokenPurpose.PASSWORD_RESET
    [(subject, recipients, html)] = sent
    assert subject == "Canvia la contrasenya de la biblioteca" and recipients == ["laia@test.dev"]
    assert "http://localhost:5173/password/reset?token=" in html


async def test_an_unknown_email_gets_the_same_answer_and_nothing(client, sent):
    response = await forgot(client)

    assert response.status_code == 200 and response.json() == EMAIL_SENT
    assert sent == [] and await rows(PasswordToken) == []


async def test_a_new_link_revokes_the_pending_one(client, sent):
    user = await create_user()
    old = await create_link(user)

    await forgot(client)

    assert (await reset(client, old)).json() == INVALID


async def test_past_the_limit_nothing_is_sent_and_the_answer_is_the_same(client, sent):
    await create_user()
    await forgot(client)

    response = await forgot(client)

    assert response.status_code == 200 and response.json() == EMAIL_SENT and len(sent) == 1


async def test_the_link_changes_the_password_and_closes_every_session(client, sent):
    user = await create_user()
    async with AsyncSessionLocal() as db:
        db.add(AuthSession(user_id=user.id, token_hash=new_token()[1], ip="127.0.0.1",
                           expires_at=datetime.now(UTC) + SESSION_DURATION))
        await db.commit()
    token = await create_link(user)

    response = await reset(client, token)

    assert response.status_code == 200
    assert response.json() == {"message": "Contrasenya canviada. Ja pots iniciar la sessió"}
    [saved] = await rows(User)
    assert await verify_password(NEW_PASSWORD, saved.password_hash)
    assert all(session.revoked_at for session in await rows(AuthSession))
    [(subject, _, _)] = sent
    assert subject == "Has canviat la contrasenya de la biblioteca"


async def test_an_invitation_chooses_the_first_password_without_an_email(client, sent):
    user = await create_user(password=None)
    token = await create_link(user, PasswordTokenPurpose.INVITATION, timedelta(days=7))

    response = await reset(client, token)

    assert response.json() == {"message": "El teu compte està a punt. Ja pots iniciar la sessió"}
    assert sent == []
    login = await client.post("/auth/login", json={"email": "laia@test.dev", "password": NEW_PASSWORD})
    assert login.status_code == 200


# An invitation still pending on an account that already chose its password (sent again at the wrong moment) never
# changes it: that is a recovery, which closes the sessions and tells the owner
async def test_an_invitation_never_changes_a_password_already_chosen(client, sent):
    user = await create_user()
    token = await create_link(user, PasswordTokenPurpose.INVITATION, timedelta(days=7))

    response = await reset(client, token)

    assert response.status_code == 400 and sent == []
    async with AsyncSessionLocal() as db:
        saved = await db.get(User, user.id)
    assert saved and await verify_password(OLD_PASSWORD, saved.password_hash)


async def test_a_link_works_once(client):
    token = await create_link(await create_user())
    await reset(client, token)
    client.cookies.clear()

    response = await reset(client, token, "una-altra-contrasenya")

    assert response.status_code == 400 and response.json() == INVALID


async def test_an_expired_link_is_refused(client):
    token = await create_link(await create_user(), expires_in=timedelta(seconds=-1))

    response = await reset(client, token)

    assert response.status_code == 400 and response.json() == INVALID


async def test_a_made_up_token_is_refused_before_looking_it_up(client):
    response = await reset(client, "x" * 42)

    assert response.status_code == 422


async def test_a_short_password_is_refused(client):
    token = await create_link(await create_user())

    response = await reset(client, token, "curta")

    assert response.status_code == 422


# A recovery forgets what the login counted for the email: the new password works at once
async def test_the_failures_of_the_login_are_forgotten(client):
    token = await create_link(await create_user())
    for _ in range(5):
        await client.post("/auth/login", json={"email": "laia@test.dev", "password": "una-altra-cosa"})

    await reset(client, token)

    login = await client.post("/auth/login", json={"email": "laia@test.dev", "password": NEW_PASSWORD})
    assert login.status_code == 200


# Only the hash is saved: the token of the email can't be read from the database
async def test_only_the_hash_of_the_token_is_saved(client, sent):
    await create_user()

    await forgot(client)

    [link] = await rows(PasswordToken)
    [(_, _, html)] = sent
    token = html.split("token=")[1].split('"')[0]
    assert link.token_hash == hash_token(token)


async def test_the_link_of_another_user_doesnt_touch_this_one(client):
    laia = await create_user()
    pau = await create_user(email="pau@test.dev")
    token = await create_link(pau)

    await reset(client, token)

    async with AsyncSessionLocal() as db:
        saved = await db.get(User, laia.id)
    assert saved and await verify_password(OLD_PASSWORD, saved.password_hash)
