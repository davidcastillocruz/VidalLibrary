import argparse
import asyncio
import logging
import sys
from typing import Literal

from pydantic import ValidationError

from src.core.languages import setup_language_system
from src.core.logger import setup_logging
from src.core.settings import settings
from src.database.session import AsyncSessionLocal, engine
from src.mail.emails import build_invitation_email
from src.mail.sender import send_email
from src.modules.auth.models.password_token_model import PasswordTokenPurpose
from src.modules.auth.repositories import password_token_repository
from src.modules.user.models.user_model import UserRole
from src.modules.user.repositories import user_repository
from src.modules.user.schemas.user_schemas import NewUserSchema
from src.security.tokens import new_token

logger = logging.getLogger(__name__)


# What came of creating a librarian: invited, the email already had an account (nothing changed), or created but
# the invitation couldn't be sent (the mail server: its error is in the logs)
Outcome = Literal["invited", "taken", "not_sent"]


# Creates a librarian and sends its invitation, in the main language: nobody can sign in to invite the first one
async def create_librarian(body: NewUserSchema) -> Outcome:
    async with AsyncSessionLocal() as db:
        if await user_repository.get_user_by_email(db, body.email):
            return "taken"
        token, token_hash = new_token()
        # Built before saving: if a text is missing nothing is created
        subject, html = build_invitation_email(settings.MAIN_LANGUAGE, body.name, token)
        user = await user_repository.create_user(db, body.email, body.name, UserRole.LIBRARIAN)
        await password_token_repository.create_password_token(db, user.id, PasswordTokenPurpose.INVITATION, token_hash)
        await db.commit()
        logger.info("Librarian created", extra={"account_id": user.id})
    return "invited" if await send_email(subject, [body.email], html) else "not_sent"


# The first librarian of a new library, from the terminal:
#   docker compose exec backend python -m src.commands.create_librarian ana@vidal.cat "Ana Puig"
# The other accounts are created from the app, by a librarian. Returns the exit code
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Creates a librarian and emails its invitation")
    parser.add_argument("email")
    parser.add_argument("name")
    args = parser.parse_args(argv)
    try:
        body = NewUserSchema(email=args.email, name=args.name, role=UserRole.LIBRARIAN)
    except ValidationError as exc:
        print(f"Not a valid email or name: {exc.errors()[0]['msg']}", file=sys.stderr)
        return 1

    setup_logging()
    setup_language_system()

    # One event loop for the command and for closing the connections of the pool
    async def run() -> Outcome:
        try:
            return await create_librarian(body)
        finally:
            await engine.dispose()

    outcome = asyncio.run(run())
    if outcome == "taken":
        print(f"{body.email} already has an account", file=sys.stderr)
        return 1
    if outcome == "not_sent":
        print(
            f"{body.email} was created, but the invitation couldn't be sent: check the mail settings (the error is in "
            "the logs above), then ask for a link from the sign-in page, under the password",
            file=sys.stderr,
        )
        return 1
    print(f"Invitation sent to {body.email}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
