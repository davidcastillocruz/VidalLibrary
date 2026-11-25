import logging

from limits import parse_many
from slowapi import Limiter

from src.api.dependencies import get_client_ip
from src.core.settings import settings

logger = logging.getLogger(__name__)

# Rate limiter, its counters are stored in RATE_LIMIT_STORAGE_URI (Redis in Docker)
# If Redis is down it keeps working with counters in memory until Redis is back
limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    in_memory_fallback_enabled=True,
    # The Redis calls block the event loop: a Redis that doesn't answer stops every request
    # for this long instead of redis-py's default 5 seconds (memory:// ignores these options)
    storage_options={"socket_timeout": 0.5, "socket_connect_timeout": 0.5},  # pyright: ignore[reportArgumentType]
)


# The limits of the routes, by how often a person repeats the action. Per IP the numbers are generous: a whole school
# shares one. A route with a session counts per user instead (key_func=get_session_user_id), so a student flooding it
# doesn't leave the rest of the school without it. They only stop a client that floods the API: what has to be stricter
# (the failures of a password, the emails to one address) has its own limit inside its service.
# Reads that come with every page of a session (who is signed in, the loans of a reader)
READ_LIMIT = "120/minute;5000/day"
# Browsing the public catalog without a session: every student of the school (around 1,600) arrives from its one IP
CATALOG_LIMIT = "600/minute;30000/day"
# Signing in and out, again and again in a shared classroom
SIGN_IN_LIMIT = "60/minute;2000/day"
# What is done once in a while: a reservation, opening the link of an email, a change in the catalog
OCCASIONAL_LIMIT = "30/minute;300/day"


# Counts one more use of a limit inside a service, for what the decorator can't key on (an email of the body...).
# limits is written like the decorator's, "1/minute;5/hour"; identifiers name the counter.
# False once any of the limits is reached. If the storage fails it lets it through: a counter is never worth an error.
# A limit written wrong does fail, it is parsed outside the try: otherwise it would look like a storage that failed
def hit_limit(limits: str, *identifiers: str) -> bool:
    items = parse_many(limits)
    try:
        return all(limiter.limiter.hit(item, *identifiers) for item in items)
    except Exception:
        logger.warning("Rate limit storage failed, the limit is skipped", extra={"limit": limits})
        return True


# Whether any of the limits is already reached, without counting a use: for what only counts when it fails.
# If the storage fails it answers False, like hit_limit lets it through
def limit_reached(limits: str, *identifiers: str) -> bool:
    items = parse_many(limits)
    try:
        return not all(limiter.limiter.test(item, *identifiers) for item in items)
    except Exception:
        logger.warning("Rate limit storage failed, the limit is skipped", extra={"limit": limits})
        return False


# Forgets the uses of a limit, for what stops counting (the failures of a password that no longer exists).
# If the storage fails the counter stays until it expires
def clear_limit(limits: str, *identifiers: str) -> None:
    items = parse_many(limits)
    try:
        for item in items:
            limiter.limiter.clear(item, *identifiers)
    except Exception:
        logger.warning("Rate limit storage failed, the limit is not cleared", extra={"limit": limits})
