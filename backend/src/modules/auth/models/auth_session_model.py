import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


# A signed-in browser: the cookie keeps a random opaque token, the database only its SHA-256 hash.
# Valid while revoked_at is empty and expires_at is in the future; it lasts 30 days and is never renewed
class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    # Indexed: a new password closes every session of the user
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    user_agent: Mapped[str | None] = mapped_column(Text)
    # Text, not inet: enough for the logs. Always set: "unknown" when the server can't see it (get_client_ip)
    ip: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # created_at + 30 days, set by the app when the session is created
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set when the user signs out or chooses a new password
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
