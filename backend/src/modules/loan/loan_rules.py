from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# The rules of the loans of the library, read by the reservations and the task that watches them

# Loans a reader can have open at once, reserved or picked up
MAX_OPEN_LOANS = 3

# How long a reserved copy waits at the library: then the reservation is cancelled and the copy goes back
PICKUP_TIME = timedelta(days=3)

# Where the library is: its days (a due date, "today") are the ones of Barcelona, whatever the clock of the server
LIBRARY_TIME_ZONE = ZoneInfo("Europe/Madrid")


# Today at the library
def library_today() -> date:
    return datetime.now(LIBRARY_TIME_ZONE).date()
