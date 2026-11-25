import uuid
from datetime import date, datetime

from pydantic import BaseModel

from src.modules.catalog.models.item_model import ItemKind
from src.modules.loan.models.loan_model import LoanStatus


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
