import uuid

from pydantic import BaseModel

from src.modules.user.models.user_model import UserRole


# Answer of GET /user/me: who is signed in, and whether it runs the library
class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: UserRole
