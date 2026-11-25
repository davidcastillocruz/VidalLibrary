import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from src.modules.user.models.user_model import UserRole

# Spaces around a name are removed, and an empty name (or only spaces) is refused.
# So is the NUL character: PostgreSQL can't store it, it would be a 500
NAME_MAX_LENGTH = 100
# Longest search of the accounts, in characters
SEARCH_MAX_LENGTH = 100
Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH, pattern=r"^[^\x00]*$"),
]


# A new account: who it is and what it can do. The first librarian comes from src/commands/create_librarian.py
class NewUserSchema(BaseModel):
    email: EmailStr
    name: Name
    role: UserRole

    # EmailStr only lowercases the domain: the database refuses an email with capitals (CHECK email = lower(email))
    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


# Answer of GET /user/me: who is signed in, and whether it runs the library
class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: UserRole


# Body of PUT /admin/users/{id}: what a librarian can change of an account. Its email is who it is: it doesn't change
class UserUpdateSchema(BaseModel):
    name: Name
    role: UserRole


# Query of GET /admin/users
class AdminUserQuery(BaseModel):
    role: UserRole | None = None
    # Looked for in the name and the email
    q: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    # ?page=1 is the first one. le: a huge page would overflow the offset in Postgres (a 500)
    page: int = Field(default=1, ge=1, le=100_000)


# An account as the librarians see it. invited: its owner hasn't chosen a password yet
class AdminUserResponse(UserResponse):
    created_at: datetime
    invited: bool
    open_loans: int


# One page of the accounts, and how many match in all
class AdminUserPage(BaseModel):
    users: list[AdminUserResponse]
    total: int


# Answer of POST /admin/users: the new account and what to show
class UserCreatedResponse(BaseModel):
    id: uuid.UUID
    message: str
