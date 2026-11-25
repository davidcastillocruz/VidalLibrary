import uuid
from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints, field_validator

from src.modules.user.models.user_model import UserRole

# Spaces around a name are removed, and an empty name (or only spaces) is refused.
# So is the NUL character: PostgreSQL can't store it, it would be a 500
NAME_MAX_LENGTH = 100
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
