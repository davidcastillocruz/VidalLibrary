import hashlib

from argon2 import PasswordHasher
from sqlalchemy import select

from src.database.session import AsyncSessionLocal
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.auth.services import auth_service
from src.modules.user.models.user_model import User
from src.security.passwords import hash_password, verify_password
from src.security.tokens import hash_token

PASSWORD = "contrasenya-llarga"
BODY = {"email": "laia@test.dev", "password": PASSWORD}
HEADERS = {"user-agent": "Firefox", "Accept-Language": "ca"}
SIGNED_IN = "Has iniciat la sessió"
INVALID = "El correu o la contrasenya no són correctes"


async def create_user(email="laia@test.dev", password: str | None = PASSWORD, password_hash: str | None = None) -> User:
    async with AsyncSessionLocal() as db:
        hashed = password_hash or (await hash_password(password) if password else None)
        user = User(email=email, name="Laia Puig", password_hash=hashed)
        db.add(user)
        await db.commit()
        return user


async def rows(model) -> list:
    async with AsyncSessionLocal() as db:
        return list(await db.scalars(select(model)))


def assert_refused(response, status_code: int, detail: str) -> None:
    assert response.status_code == status_code and response.json() == {"detail": detail}
    assert "session" not in response.cookies


async def test_the_right_password_starts_a_session(client):
    user = await create_user()

    response = await client.post("/auth/login", json=BODY, headers=HEADERS)

    assert response.status_code == 200 and response.json() == {"message": SIGNED_IN}
    [session] = await rows(AuthSession)
    assert session.token_hash == hash_token(response.cookies["session"]) and session.user_id == user.id
    assert session.user_agent == "Firefox" and session.ip == "127.0.0.1"


async def test_the_email_is_found_whatever_its_capitals(client):
    await create_user()

    response = await client.post("/auth/login", json={**BODY, "email": "Laia@Test.DEV"}, headers=HEADERS)

    assert response.status_code == 200


async def test_a_wrong_password_is_refused(client):
    await create_user()

    response = await client.post("/auth/login", json={**BODY, "password": "una-altra-cosa"}, headers=HEADERS)

    assert_refused(response, 401, INVALID)
    assert await rows(AuthSession) == []


async def test_an_unknown_email_gets_the_same_error(client):
    response = await client.post("/auth/login", json=BODY, headers=HEADERS)

    assert_refused(response, 401, INVALID)


# An account the librarian created whose invitation wasn't opened yet: it has no password to check
async def test_an_account_without_a_password_yet_gets_the_same_error(client):
    await create_user(password=None)

    response = await client.post("/auth/login", json=BODY, headers=HEADERS)

    assert_refused(response, 401, INVALID)


async def test_the_failure_limit_refuses_even_the_right_password(client):
    await create_user()
    for _ in range(5):
        await client.post("/auth/login", json={**BODY, "password": "una-altra-cosa"}, headers=HEADERS)

    response = await client.post("/auth/login", json=BODY, headers=HEADERS)

    assert_refused(response, 401, INVALID)


# The failures of one email don't block another one, and the counter keeps the hash of the email, not the email
async def test_the_failure_limit_is_per_email(client, monkeypatch):
    await create_user()
    await create_user(email="pau@test.dev")
    counted = []
    hit = auth_service.hit_limit

    def spy(limits, *identifiers):
        counted.append(identifiers)
        return hit(limits, *identifiers)

    monkeypatch.setattr(auth_service, "hit_limit", spy)
    for _ in range(5):
        await client.post("/auth/login", json={**BODY, "password": "una-altra-cosa"}, headers=HEADERS)

    response = await client.post("/auth/login", json={**BODY, "email": "pau@test.dev"}, headers=HEADERS)

    assert response.status_code == 200
    assert counted[0] == ("login-failure", hashlib.sha256(b"laia@test.dev").hexdigest())


async def test_signing_in_forgets_the_failures(client):
    await create_user()
    for _ in range(4):
        await client.post("/auth/login", json={**BODY, "password": "una-altra-cosa"}, headers=HEADERS)
    await client.post("/auth/login", json=BODY, headers=HEADERS)
    client.cookies.clear()

    for _ in range(4):
        await client.post("/auth/login", json={**BODY, "password": "una-altra-cosa"}, headers=HEADERS)
    response = await client.post("/auth/login", json=BODY, headers=HEADERS)

    assert response.status_code == 200


async def test_a_hash_with_older_parameters_is_replaced(client):
    old = PasswordHasher(time_cost=1, memory_cost=8192).hash(PASSWORD)
    await create_user(password_hash=old)

    await client.post("/auth/login", json=BODY, headers=HEADERS)

    [user] = await rows(User)
    assert user.password_hash != old and await verify_password(PASSWORD, user.password_hash)


async def test_a_long_user_agent_is_cut(client):
    await create_user()

    await client.post("/auth/login", json=BODY, headers={**HEADERS, "user-agent": "a" * 2000})

    [session] = await rows(AuthSession)
    assert session.user_agent == "a" * 512


async def test_signed_in_is_409(client):
    await create_user()
    await client.post("/auth/login", json=BODY, headers=HEADERS)

    response = await client.post("/auth/login", json=BODY, headers=HEADERS)

    assert response.status_code == 409 and response.json() == {"detail": "Ja has iniciat la sessió"}


async def test_the_sign_in_is_logged_with_the_account(client, caplog):
    user = await create_user()

    with caplog.at_level("INFO", logger="src.modules.auth.services.auth_service"):
        await client.post("/auth/login", json=BODY, headers=HEADERS)

    [record] = [record for record in caplog.records if record.getMessage() == "Signed in"]
    assert record.account_id == user.id
