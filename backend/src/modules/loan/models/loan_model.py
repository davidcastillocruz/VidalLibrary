import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


# Values of the loan_status enum of PostgreSQL
class LoanStatus(enum.StrEnum):
    # Reserved: a copy waits at the library for its reader
    REQUESTED = "requested"
    # Picked up: the reader has it until due_on
    ACTIVE = "active"
    RETURNED = "returned"
    # By its reader, by a librarian, or because nobody picked it up in time
    CANCELLED = "cancelled"


# The statuses that hold a copy: a requested or active loan isn't over
OPEN_STATUSES = (LoanStatus.REQUESTED, LoanStatus.ACTIVE)


# A loan of one copy of a work to one reader. The copies aren't told apart: a work lends at most as many as it has
class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        # One open loan of the same work per reader: a second reservation of it would hold a copy for nothing
        Index(
            "uq_loans_open_user_item",
            "user_id",
            "item_id",
            unique=True,
            postgresql_where=text("status IN ('requested', 'active')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    # Indexed: the loans of a reader are read on every visit to its page
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # Indexed: the copies left of a work are counted on every page of the catalog. A work with open loans can't be
    # deleted (the service checks it): the cascade only takes the finished ones
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    status: Mapped[LoanStatus] = mapped_column(
        Enum(LoanStatus, name="loan_status", values_callable=lambda e: [member.value for member in e]),
        server_default=LoanStatus.REQUESTED.value,
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set when a librarian hands it over
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The day of the library it has to come back by, set when it is picked up: a day, not a moment
    due_on: Mapped[date | None] = mapped_column(Date)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
