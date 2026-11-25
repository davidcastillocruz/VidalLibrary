# Every model of the app, imported here so SQLAlchemy and Alembic know all the tables

from src.modules.auth.models.auth_session_model import AuthSession
from src.modules.auth.models.password_token_model import PasswordToken
from src.modules.catalog.models.genre_model import Genre
from src.modules.catalog.models.item_model import Item
from src.modules.catalog.models.language_model import ItemLanguage
from src.modules.user.models.user_model import User
