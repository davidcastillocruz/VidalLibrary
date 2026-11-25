import inspect
import re

import pytest

from src.mail import emails
from src.mail.layout import render_email

TEXTS = {"subject": "S", "title": "T", "text": "x", "note": "N", "button": "B", "fallback": "F"}

# Every email with arguments for its gaps, to build it in every language
ARGS = {
    "token": "tok_en-1",
}
BUILDERS = [function for name, function in inspect.getmembers(emails, inspect.isfunction) if name.startswith("build_")]


# A text missing in a language would only show when that email is sent: every email is built in every language
@pytest.mark.parametrize("language", ["ca", "es", "en"])
@pytest.mark.parametrize("build", BUILDERS, ids=lambda build: build.__name__)
def test_every_email_is_built_in_every_language(build, language):
    gaps = [name for name in inspect.signature(build).parameters if name not in ("language", "name")]

    subject, html = build(language, "Laia", *(ARGS[name] for name in gaps))

    assert subject and f'<html lang="{language}">' in html and "Laia" in html


# The texts come from the translations with what the user or a provider gave (a name), and the link has a token:
# everything is escaped, nothing can become HTML
def test_the_texts_and_the_link_are_escaped():
    html = render_email("es", {**TEXTS, "text": "Laia <b>&"}, href="https://vidal.test/a?x=1&y=\"2\"")

    assert "Laia &lt;b&gt;&amp;" in html and "<b>" not in html
    assert 'href="https://vidal.test/a?x=1&amp;y=&quot;2&quot;"' in html


# A link goes in the button and written out below it, in case the button doesn't work
def test_a_link_is_a_button_and_is_written_out():
    html = render_email("es", TEXTS, href="https://vidal.test/login")

    assert len(re.findall(r'href="https://vidal.test/login"', html)) == 2 and ">B</a>" in html and "F<br>" in html
