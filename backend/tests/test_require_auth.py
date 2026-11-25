from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Depends
from sqlalchemy import select

from src.api.dependencies import require_librarian
from src.database.session import AsyncSessionLocal
from src.main import app
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.user.models.user_model import User, UserRole
from src.security.cookies import SESSION_DURATION
from src.security.tokens import new_token
from src.shared.schemas import MessageResponse


# A user with a session: returns the token of its cookie. expires_at and revoked_at set the state of the session
async def signed_in(
    role: UserRole = UserRole.READER,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> tuple[User, str]:
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        user = User(email="laia@test.dev", name="Laia Puig", role=role, password_hash="hash")
        db.add(user)
        await db.flush()
        db.add(AuthSession(
            user_id=user.id,
            token_hash=token_hash,
            ip="127.0.0.1",
            expires_at=expires_at or datetime.now(UTC) + SESSION_DURATION,
            revoked_at=revoked_at,
        ))
        await db.commit()
    return user, token


# A route only for librarians, apart from the real ones
@pytest.fixture
def librarian_route():
    async def manage() -> MessageResponse:
        return MessageResponse(message="ok")

    app.add_api_route("/test-librarian", manage, dependencies=[Depends(require_librarian)])
    yield
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/test-librarian"]
    app.openapi_schema = None


async def test_a_valid_session_says_who_is_signed_in(client):
    user, token = await signed_in()
    client.cookies.set("session", token)

    response = await client.get("/user/me")

    assert response.status_code == 200
    assert response.json() == {"id": str(user.id), "email": "laia@test.dev", "name": "Laia Puig", "role": "reader"}


async def test_without_a_cookie_it_is_401_and_nothing_is_deleted(client):
    response = await client.get("/user/me", headers={"Accept-Language": "ca"})

    assert response.status_code == 401 and response.json() == {"detail": "Inicia la sessió per continuar"}
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("state", [
    {"expires_at": datetime.now(UTC) - timedelta(seconds=1)},
    {"revoked_at": datetime.now(UTC)},
], ids=["expired", "revoked"])
async def test_a_session_that_no_longer_works_is_401_and_its_cookie_deleted(client, state):
    _, token = await signed_in(**state)
    client.cookies.set("session", token)

    response = await client.get("/user/me")

    assert response.status_code == 401 and response.headers["set-cookie"].startswith('session="";')


async def test_an_unknown_token_is_401(client):
    client.cookies.set("session", "made-up")

    response = await client.get("/user/me")

    assert response.status_code == 401


async def test_a_reader_cant_do_what_only_librarians_do(client, librarian_route):
    _, token = await signed_in()
    client.cookies.set("session", token)

    response = await client.get("/test-librarian", headers={"Accept-Language": "ca"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Només el personal de la biblioteca pot fer això"}


async def test_a_librarian_can(client, librarian_route):
    _, token = await signed_in(role=UserRole.LIBRARIAN)
    client.cookies.set("session", token)

    response = await client.get("/test-librarian")

    assert response.status_code == 200


async def test_using_it_marks_the_session_used(client):
    _, token = await signed_in()
    client.cookies.set("session", token)
    async with AsyncSessionLocal() as db:
        before = await db.scalar(select(AuthSession.last_used_at))

    await client.get("/user/me")

    async with AsyncSessionLocal() as db:
        after = await db.scalar(select(AuthSession.last_used_at))
    assert before and after and after > before
