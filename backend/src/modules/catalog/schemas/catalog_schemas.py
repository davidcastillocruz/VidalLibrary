import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from src.modules.catalog.models.item_model import ItemKind

# Lengths of what the librarians write. Spaces around are removed, an empty text (or only spaces) is refused, and so
# is the NUL character: PostgreSQL can't store it, it would be a 500
TITLE_MAX_LENGTH = 300
CREATOR_MAX_LENGTH = 200
SYNOPSIS_MAX_LENGTH = 5000
NAME_MAX_LENGTH = 50
Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=TITLE_MAX_LENGTH, pattern=r"^[^\x00]*$"),
]
Creator = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=CREATOR_MAX_LENGTH, pattern=r"^[^\x00]*$"),
]
Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=NAME_MAX_LENGTH, pattern=r"^[^\x00]*$"),
]

# A year a work of a school library can have: the first printed books, and a little after now for the new ones
MIN_YEAR = 1450
MAX_YEAR = 2100

# Copies of one work: at least one, and more than this is a typo
MAX_COPIES = 100

# Genres one work can have
MAX_GENRES = 10

# Longest search: a title or a name, never a text
SEARCH_MAX_LENGTH = 100


# A genre in the answers: its kind says which works it belongs to
class GenreResponse(BaseModel):
    id: uuid.UUID
    kind: ItemKind
    name: str


# A language in the answers
class LanguageResponse(BaseModel):
    id: uuid.UUID
    name: str


# A work in a page of the catalog: what its card shows
class ItemSummary(BaseModel):
    id: uuid.UUID
    kind: ItemKind
    title: str
    creator: str
    year: int | None
    copies: int


# A work on its own page: the card and the rest of what the library knows of it
class ItemDetail(ItemSummary):
    synopsis: str | None
    language: LanguageResponse | None
    genres: list[GenreResponse]


# Answer of GET /catalog/items: one page of the works that match, and how many match in all
class CatalogPage(BaseModel):
    items: list[ItemSummary]
    total: int


# Query of GET /catalog/items. Every filter is optional: without any, the whole catalog sorted by title
class CatalogQuery(BaseModel):
    kind: ItemKind | None = None
    genre: uuid.UUID | None = None
    language: uuid.UUID | None = None
    # Looked for in the title and in the creator, whatever its capitals
    q: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    sort: Literal["title", "newest", "year"] = "title"
    # ?page=1 is the first one. le: a huge page would overflow the offset in Postgres (a 500)
    page: int = Field(default=1, ge=1, le=100_000)


# Body of POST /admin/catalog/items and PUT /admin/catalog/items/{item_id}: the whole work, the same for both
class ItemSchema(BaseModel):
    kind: ItemKind
    title: Title
    creator: Creator
    year: int | None = Field(default=None, ge=MIN_YEAR, le=MAX_YEAR)
    synopsis: str | None = Field(default=None, max_length=SYNOPSIS_MAX_LENGTH, pattern=r"^[^\x00]*$")
    language_id: uuid.UUID | None = None
    genre_ids: list[uuid.UUID] = Field(default=[], max_length=MAX_GENRES)
    copies: int = Field(ge=1, le=MAX_COPIES)

    # A synopsis of only spaces is no synopsis: saved as NULL, not as ""
    @field_validator("synopsis")
    @classmethod
    def empty_synopsis_is_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


# Body of POST /admin/catalog/genres
class GenreSchema(BaseModel):
    kind: ItemKind
    name: Name


# Body with only a name, like POST /admin/catalog/languages or renaming a genre
class NameSchema(BaseModel):
    name: Name


# Answer of POST /admin/catalog/items: the id of the new work, to open it
class ItemCreatedResponse(BaseModel):
    id: uuid.UUID
    message: str
