from datetime import timedelta
from typing import Literal

from starlette.responses import Response

from src.core.settings import settings

# A session lasts 30 days from sign-in and is never renewed
SESSION_DURATION = timedelta(days=30)

# The same attributes to set the cookie and to delete it: a browser only deletes a cookie whose name, path
# and flags match the ones it was set with (a __Host- cookie also needs Secure and Path=/, and no Domain)
# HttpOnly: JavaScript can't read it. SameSite=Lax: other sites can't send it with their forms or fetches
_PATH = "/"
_SAMESITE: Literal["lax"] = "lax"


# Puts the session token in the cookie of the response
def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        token,
        max_age=int(SESSION_DURATION.total_seconds()),
        path=_PATH,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=_SAMESITE,
    )


# Removes the session cookie from the browser
def delete_session_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.SESSION_COOKIE_NAME,
        path=_PATH,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=_SAMESITE,
    )


# The Set-Cookie header that removes the session cookie, for an HTTPException:
# the response it builds doesn't keep the cookies set on any other response
def delete_session_cookie_header() -> dict[str, str]:
    response = Response()
    delete_session_cookie(response)
    return {"set-cookie": response.headers["set-cookie"]}

