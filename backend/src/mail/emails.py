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
