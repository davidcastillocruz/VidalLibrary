from pydantic import BaseModel, EmailStr, Field, field_validator

from src.security.passwords import PASSWORD_MAX_LENGTH


# Body of POST /auth/login
class LoginSchema(BaseModel):
    email: EmailStr
    # Only a maximum, it stops a huge password from keeping the server busy hashing it. Not the minimum of a new one:
    # a short password is just a wrong one, and it gets the same error. Not stripped: spaces are part of a password
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

    # EmailStr only lowercases the domain: "Ana@Test.dev" -> "Ana@test.dev". The emails are saved in lowercase,
    # "Ana@test.dev" has to find its account
    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()
