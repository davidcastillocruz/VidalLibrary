import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


# Values of the password_token_purpose enum of PostgreSQL
class PasswordTokenPurpose(enum.StrEnum):
    # A new account chooses its first password
    INVITATION = "invitation"
    # A forgotten password is replaced
    PASSWORD_RESET = "password_reset"


# Single-use link sent by email to choose a password. The email keeps the random token, the database only its SHA-256
# hash. Valid while it isn't used, revoked or expired
class PasswordToken(Base):
    __tablename__ = "password_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    # Indexed: a new link revokes the pending ones of the user
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[PasswordTokenPurpose] = mapped_column(
        Enum(PasswordTokenPurpose, name="password_token_purpose", values_callable=lambda e: [m.value for m in e]),
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # created_at + the duration of its purpose (security/tokens.py), set by the app
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Set when a newer link of the user replaces it
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
