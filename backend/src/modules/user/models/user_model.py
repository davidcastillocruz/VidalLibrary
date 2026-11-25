import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


# Values of the user_role enum of PostgreSQL
class UserRole(enum.StrEnum):
    # Borrows: a student or a teacher
    READER = "reader"
    # Runs the library: the catalog, the loans and the accounts
    LIBRARIAN = "librarian"


# An account of the library. Nobody signs up: a librarian creates it and the user chooses its password from the email
class User(Base):
    __tablename__ = "users"
    # The app lowercases the email before saving it; the database refuses it otherwise,
    # so "Ana@test.dev" and "ana@test.dev" can never be two accounts
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    # The database generates the id: rows created outside the app (a script, a seed) get one too
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    email: Mapped[str] = mapped_column(Text, unique=True)
    # The whole name as the librarian writes it, shown in the loans
    name: Mapped[str] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [member.value for member in e]),
        server_default=UserRole.READER.value,
    )
    # Argon2id. Empty until the user opens the invitation and chooses one: until then it can't sign in
    password_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
