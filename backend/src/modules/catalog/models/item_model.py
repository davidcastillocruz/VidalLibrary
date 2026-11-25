import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, Table, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


# Values of the item_kind enum of PostgreSQL. The three share everything but the word for who made them (author,
# director, designer): one table, and the frontend names creator after the kind
class ItemKind(enum.StrEnum):
    BOOK = "book"
    FILM = "film"
    BOARD_GAME = "board_game"


# The column type of a kind, shared by the works and their genres: one enum in PostgreSQL
ITEM_KIND = Enum(ItemKind, name="item_kind", values_callable=lambda e: [member.value for member in e])


# The genres of each work, any number of them
item_genres = Table(
    "item_genres",
    Base.metadata,
    Column("item_id", ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    # Indexed: the catalog filters by genre
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, index=True),
)


# A work of the catalog: a book, a film or a board game, with how many copies the library has of it
class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        # A work without copies isn't in the library: removing the last one is deleting the work
        CheckConstraint("copies >= 1", name="copies_at_least_one"),
        # The catalog is browsed by kind and sorted by title on every visit
        Index("ix_items_kind_title", "kind", "title"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    kind: Mapped[ItemKind] = mapped_column(ITEM_KIND)
    title: Mapped[str] = mapped_column(Text)
    # The author of a book, the director of a film, the designer of a board game
    creator: Mapped[str] = mapped_column(Text)
    # Empty when the library doesn't know it
    year: Mapped[int | None] = mapped_column(Integer)
    synopsis: Mapped[str | None] = mapped_column(Text)
    # Deleting a language leaves its works without one
    language_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("languages.id", ondelete="SET NULL"), index=True)
    copies: Mapped[int] = mapped_column(Integer)
    # The key of the cover in the storage, empty without one
    cover_key: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
