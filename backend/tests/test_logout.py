from datetime import UTC, datetime

from sqlalchemy import select

from src.database.session import AsyncSessionLocal
from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.user.models.user_model import User
from src.security.cookies import SESSION_DURATION
from src.security.tokens import new_token


# A user with two signed-in browsers: returns the token of the first one and both sessions
async def signed_in() -> tuple[str, AuthSession, AuthSession]:
    token, token_hash = new_token()
    async with AsyncSessionLocal() as db:
        user = User(email="laia@test.dev", name="Laia Puig", password_hash="hash")
        db.add(user)
        await db.flush()
        expires_at = datetime.now(UTC) + SESSION_DURATION
        this = AuthSession(user_id=user.id, token_hash=token_hash, ip="127.0.0.1", expires_at=expires_at)
        other = AuthSession(user_id=user.id, token_hash=new_token()[1], ip="127.0.0.1", expires_at=expires_at)
        db.add_all([this, other])
        await db.commit()
    return token, this, other


async def logout(client):
    return await client.post("/auth/logout", headers={"Accept-Language": "ca"})


async def rows(model) -> list:
    async with AsyncSessionLocal() as db:
        return list(await db.scalars(select(model)))


async def test_logout_closes_this_session_and_deletes_the_cookie(client):
    token, this, other = await signed_in()
    client.cookies.set("session", token)

    response = await logout(client)

    assert response.status_code == 200 and response.json() == {"message": "Has tancat la sessió"}
    deleted = response.headers["set-cookie"]
    assert deleted.startswith('session="";') and "Max-Age=0" in deleted
    closed = {session.id: session.revoked_at for session in await rows(AuthSession)}
    assert closed[this.id] and not closed[other.id]


async def test_the_token_stops_working(client):
    token, _, _ = await signed_in()
    client.cookies.set("session", token)
    await logout(client)
    client.cookies.set("session", token)

    response = await client.get("/user/me")

    assert response.status_code == 401


async def test_without_a_session_it_is_401(client):
    response = await logout(client)

    assert response.status_code == 401 and response.json() == {"detail": "Inicia la sessió per continuar"}
