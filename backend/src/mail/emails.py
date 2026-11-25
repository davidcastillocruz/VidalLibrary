import uuid

from src.core.languages import get_response
from src.core.settings import settings
from src.mail.layout import render_email

# Each email: its texts (mail/translations), what fills their gaps and where its button goes. The HTML is the same for
# all of them (layout.py). Each returns (subject, html): the subject goes as it is, it's a header and not HTML


# --- The account ---

# A librarian created the account: the link lets its owner choose the password and sign in for the first time
def build_invitation_email(language: str, name: str, token: str) -> tuple[str, str]:
    texts = get_response("INVITATION_EMAIL", language, {"text": (name,)})
    return texts["subject"], render_email(language, texts, href=f"{settings.FRONTEND_URL}/invitation?token={token}")


# Link to choose a new password: the frontend opens it, asks for the password and sends it with the token to the API
def build_password_reset_email(language: str, name: str, token: str) -> tuple[str, str]:
    texts = get_response("PASSWORD_RESET_EMAIL", language, {"text": (name,)})
    return texts["subject"], render_email(language, texts, href=f"{settings.FRONTEND_URL}/password/reset?token={token}")


# Sent once the password has changed with the recovery link: if it wasn't the owner, they learn it here
def build_password_changed_email(language: str, name: str) -> tuple[str, str]:
    texts = get_response("PASSWORD_CHANGED_EMAIL", language, {"text": (name,)})
    return texts["subject"], render_email(language, texts, href=f"{settings.FRONTEND_URL}/login")


# --- The loans (loan_job) ---


# Nobody picked the reserved copy up in time: the reservation is cancelled, and the button reserves the work again
def build_reservation_expired_email(language: str, name: str, title: str, item_id: uuid.UUID) -> tuple[str, str]:
    texts = get_response("RESERVATION_EXPIRED_EMAIL", language, {"text": (name, title)})
    return texts["subject"], render_email(language, texts, href=f"{settings.FRONTEND_URL}/items/{item_id}")


# A loan due in the next days, with its due day written for people: the button opens the reader's loans
def build_due_soon_email(language: str, name: str, title: str, due_on: str) -> tuple[str, str]:
    texts = get_response("DUE_SOON_EMAIL", language, {"subject": (title,), "text": (name, title, due_on)})
    return texts["subject"], render_email(language, texts, href=f"{settings.FRONTEND_URL}/loans")


# A loan past its due day: it says which day it was, and that other readers wait for the copy
def build_overdue_email(language: str, name: str, title: str, due_on: str) -> tuple[str, str]:
    texts = get_response("OVERDUE_EMAIL", language, {"subject": (title,), "text": (name, title, due_on)})
    return texts["subject"], render_email(language, texts, href=f"{settings.FRONTEND_URL}/loans")
