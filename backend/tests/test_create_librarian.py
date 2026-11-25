import pytest
from sqlalchemy import select

from src.commands import create_librarian
from src.database.session import AsyncSessionLocal
from src.modules.auth.models.password_token_model import PasswordToken, PasswordTokenPurpose
from src.modules.user.models.user_model import User, UserRole
from src.modules.user.schemas.user_schemas import NewUserSchema

BODY = NewUserSchema(email="Ana@Vidal.cat", name=" Ana Puig ", role=UserRole.LIBRARIAN)


# The emails the command would send: (subject, recipients, html)
@pytest.fixture
def sent(monkeypatch):
    emails: list[tuple[str, list[str], str]] = []

    async def fake_send_email(subject: str, recipients: list[str], body: str) -> bool:
        emails.append((subject, recipients, body))
        return True

    monkeypatch.setattr(create_librarian, "send_email", fake_send_email)
    return emails


async def rows(model) -> list:
    async with AsyncSessionLocal() as db:
        return list(await db.scalars(select(model)))


async def test_it_creates_a_librarian_without_a_password_and_invites_it(clean_state, sent):
    assert await create_librarian.create_librarian(BODY) == "invited"

    [user] = await rows(User)
    assert (user.email, user.name, user.role, user.password_hash) == ("ana@vidal.cat", "Ana Puig", "librarian", None)
    [link] = await rows(PasswordToken)
    assert link.user_id == user.id and link.purpose == PasswordTokenPurpose.INVITATION
    [(subject, recipients, html)] = sent
    assert subject == "Ja tens compte a la Biblioteca Vidal i Barraquer" and recipients == ["ana@vidal.cat"]
    assert "http://localhost:5173/invitation?token=" in html


async def test_an_email_with_an_account_changes_nothing(clean_state, sent):
    await create_librarian.create_librarian(BODY)

    assert await create_librarian.create_librarian(BODY) == "taken"

    assert len(await rows(User)) == 1 and len(sent) == 1


def test_a_wrong_email_stops_before_touching_anything(capsys):
    assert create_librarian.main(["not-an-email", "Ana Puig"]) == 1
    assert "Not a valid email or name" in capsys.readouterr().err


# The mail server failed: the account is there, and the command knows the invitation didn't go out
async def test_an_invitation_that_couldnt_be_sent_is_known(clean_state, monkeypatch):
    async def failing_send_email(subject: str, recipients: list[str], body: str) -> bool:
        return False

    monkeypatch.setattr(create_librarian, "send_email", failing_send_email)

    assert await create_librarian.create_librarian(BODY) == "not_sent"
    assert len(await rows(User)) == 1


# Whoever ran the command is told, and how to get a link anyway
def test_the_command_tells_an_invitation_that_couldnt_be_sent(monkeypatch, capsys):
    async def not_sent(body) -> str:
        return "not_sent"

    monkeypatch.setattr(create_librarian, "create_librarian", not_sent)

    assert create_librarian.main(["ana@vidal.cat", "Ana Puig"]) == 1
    assert "the invitation couldn't be sent" in capsys.readouterr().err
