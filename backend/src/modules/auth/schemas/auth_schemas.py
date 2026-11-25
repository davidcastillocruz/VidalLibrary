from pydantic import BaseModel, EmailStr, Field, field_validator

from src.security.passwords import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


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


# Body with only an email, like POST /auth/password/forgot
class EmailSchema(BaseModel):
    email: EmailStr

    # Lowercased like in the login: the emails are saved like that
    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


# Body of POST /auth/password/reset: the token of the link (an invitation or a recovery) and the password the user
# chooses. Only the shape of generate_token is accepted (43 URL-safe characters): anything else can't be a token,
# and it is refused before hashing it or looking it up
class TokenPasswordSchema(BaseModel):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    # Not stripped: spaces are part of a password
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
