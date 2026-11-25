from html import escape

# Colors of the light theme of the frontend (frontend/src/themes/themes.css):
# station signage, black ink on warm paper with signal yellow, and the dark departures board
PAPER = "#efece4"
INK = "#151513"
MUTED = "#5c5a53"
BORDER = "#c9c4b6"
SIGNAL = "#f5c400"
BOARD = "#1a1a18"
BOARD_CELL = "#262624"
BOARD_TEXT = "#f4f1e8"

# Email clients rarely load web fonts: Archivo if it's installed, a narrow system font otherwise
FONT = "Archivo, 'Arial Narrow', Arial, Helvetica, sans-serif"

# Email clients only render tables and inline styles reliably: every piece below is built with them


# The HTML of every email, with the texts of its translation (subject, title, text and footer).
# An email with another shape adds an option here, never a copy of the HTML. Everything is escaped here
def render_email(language: str, texts: dict[str, str]) -> str:
    safe = {key: escape(text) for key, text in texts.items()}
    return f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{safe["subject"]}</title>
</head>
<body style="margin:0;padding:0;background:{PAPER};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
<tr><td style="padding-bottom:18px;border-bottom:1px solid {BORDER};font:700 15px/1 {FONT};color:{INK};">
FastAPI <span style="font-weight:400;color:{MUTED};">&amp;</span> React
</td></tr>
<tr><td style="padding:36px 0 12px;font:800 44px/1 {FONT};letter-spacing:-1px;color:{INK};">{safe["title"]}</td></tr>
<tr><td style="padding-bottom:28px;font:400 16px/1.55 {FONT};color:{MUTED};">{safe["text"]}</td></tr>
<tr><td style="padding-top:18px;border-top:1px solid {BORDER};font:400 13px/1.5 {FONT};color:{MUTED};">
{safe["footer"]}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
