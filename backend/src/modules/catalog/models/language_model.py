import uuid

from sqlalchemy import Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


# The language a work is in, the same list for books, films and board games
class ItemLanguage(Base):
    __tablename__ = "languages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(Text, unique=True)
