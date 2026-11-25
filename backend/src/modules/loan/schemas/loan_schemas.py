import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.modules.catalog.models.item_model import ItemKind
from src.modules.loan.models.loan_model import LoanStatus

# Longest search of the loans, in characters
SEARCH_MAX_LENGTH = 100


# Body of POST /loans: the work to reserve. Any of its copies, they aren't told apart
class ReservationSchema(BaseModel):
    item_id: uuid.UUID


# The work of a loan, as its line shows it
class LoanItem(BaseModel):
    id: uuid.UUID
    kind: ItemKind
    title: str
    creator: str
    # The version of its cover, as in the catalog: None without one
    cover: str | None


# A loan of the signed-in reader. pickup_until: until when a reserved copy waits at the library, empty once picked up
class LoanResponse(BaseModel):
    id: uuid.UUID
    status: LoanStatus
    item: LoanItem
    requested_at: datetime
    pickup_until: datetime | None
    picked_up_at: datetime | None
    due_on: date | None
    returned_at: datetime | None
    cancelled_at: datetime | None


# Who has a loan, as the librarians see it
class LoanReader(BaseModel):
    id: uuid.UUID
    name: str
    email: str


# A loan as the librarians see it: with its reader, and whether its due day has passed
class AdminLoanResponse(LoanResponse):
    reader: LoanReader
    overdue: bool


# One page of the loans, and how many match in all
class AdminLoanPage(BaseModel):
    loans: list[AdminLoanResponse]
    total: int


# Query of GET /admin/loans. show:
# - open: reserved or picked up, the ones the desk works with
# - requested, active, overdue (picked up and late), or all of them
class AdminLoanQuery(BaseModel):
    show: Literal["open", "requested", "active", "overdue", "all"] = "open"
    # Looked for in the name and the email of the reader and in the title of the work
    q: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    # ?page=1 is the first one. le: a huge page would overflow the offset in Postgres (a 500)
    page: int = Field(default=1, ge=1, le=100_000)


# Body of POST /admin/loans/{id}/pickup: the day of the library it has to come back by
class PickupSchema(BaseModel):
    due_on: date
