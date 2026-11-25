import uuid

from sqlalchemy import Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base
from src.modules.catalog.models.item_model import ITEM_KIND, ItemKind


# A genre of one kind of work: a novel is a genre of books, a strategy game one of board games
class Genre(Base):
    __tablename__ = "genres"
    # The same name twice in one kind would show twice in its filter
    __table_args__ = (UniqueConstraint("kind", "name", name="uq_genres_kind_name"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    kind: Mapped[ItemKind] = mapped_column(ITEM_KIND)
    name: Mapped[str] = mapped_column(Text)
