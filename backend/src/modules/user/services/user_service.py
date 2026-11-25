from src.modules.user.models.user_model import User
from src.modules.user.schemas.user_schemas import UserResponse


# Who is signed in: require_auth already read the user with its session, nothing else is asked
def me(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, name=user.name, role=user.role)
