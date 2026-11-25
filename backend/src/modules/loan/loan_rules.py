from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# The rules of the loans of the library, read by the reservations and the task that watches them

# Loans a reader can have open at once, reserved or picked up
MAX_OPEN_LOANS = 3

# How long a reserved copy waits at the library: then the reservation is cancelled and the copy goes back
PICKUP_TIME = timedelta(days=3)

# Days before its due day a reader is told a loan is due soon
DUE_SOON_DAYS = 2

# Longest loan a librarian can give, in days from the pick-up: a due date further away is a typo
MAX_LOAN_DAYS = 90

# Where the library is: its days (a due date, "today") are the ones of Barcelona, whatever the clock of the server
LIBRARY_TIME_ZONE = ZoneInfo("Europe/Madrid")


# Today at the library
def library_today() -> date:
    return datetime.now(LIBRARY_TIME_ZONE).date()


# A day as the emails write it: 27/11/2026
def format_day(day: date) -> str:
    return f"{day.day}/{day.month}/{day.year}"
