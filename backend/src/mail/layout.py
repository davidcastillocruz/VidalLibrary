from html import escape

# Colors of the light theme of the frontend (frontend/src/themes/themes.css): emails are read on white,
# and many clients ignore dark mode or invert the colors on their own
BG = "#F4F6FA"
CARD = "#FFFFFF"
BORDER = "#DBE3EE"
TEXT = "#1B2A3F"
MUTED = "#4A5A70"
ACCENT = "#20447D"
ACCENT_INK = "#FFFFFF"
# The burnt orange of the institute, for the rule that opens the card, as on the panels of the web
SIGNAL = "#9C420E"

# Email clients rarely load web fonts: the ones of the web if they're installed, the system's otherwise
FONT = "Lato, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
TITLE_FONT = "Poppins, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


# The HTML of every email, with the texts of its translation (subject, title, text, note, button and fallback).
# Email clients only render tables and inline styles reliably: the whole email is built with them. Under the text it
# shows the button of href, with the link written out below in case the button doesn't work. Everything is escaped here
def render_email(language: str, texts: dict[str, str], href: str) -> str:
    safe = {key: escape(text) for key, text in texts.items()}
    link = escape(href, quote=True)
    action = f"""<tr><td style="padding-bottom:28px;">
<a href="{link}" style="display:inline-block;padding:12px 22px;background:{ACCENT};border-radius:8px;
font:700 15px/1 {FONT};color:{ACCENT_INK};text-decoration:none;">{safe["button"]}</a>
</td></tr>"""
    fallback = f"""
<tr><td style="padding-top:20px;border-top:1px solid {BORDER};font:400 12px/1.5 {FONT};color:{MUTED};">
{safe["fallback"]}<br><a href="{link}" style="color:{MUTED};word-break:break-all;">{link}</a>
</td></tr>"""
    return f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{safe["subject"]}</title>
</head>
<body style="margin:0;padding:0;background:{BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG};">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">
<tr><td style="padding:0 4px 16px;font:700 18px/1.2 {TITLE_FONT};color:{ACCENT};">Biblioteca Vidal i Barraquer</td></tr>
<tr><td style="padding:32px;background:{CARD};border:1px solid {BORDER};border-top:4px solid {SIGNAL};
border-radius:12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr><td style="padding-bottom:12px;font:700 26px/1.2 {TITLE_FONT};color:{ACCENT};">{safe["title"]}</td></tr>
<tr><td style="padding-bottom:28px;font:400 15px/1.6 {FONT};color:{TEXT};">{safe["text"]}</td></tr>
{action}
<tr><td style="padding-bottom:20px;font:400 13px/1.5 {FONT};color:{MUTED};">{safe["note"]}</td></tr>{fallback}
</table>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
