from pathlib import Path
import pytest

playwright = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parent.parent
DASHES = ("—", "–")


def render(name):
    with playwright.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto((ROOT / name).resolve().as_uri())
        pg.wait_for_timeout(500)
        text = pg.inner_text("body")
        html = pg.content()
        b.close()
    return text, html, errors


def test_technical_page_holds_the_engineering_material():
    text, html, errors = render("technical.html")
    assert errors == []
    assert "Preparer" in text and "Referee" in text
    assert "gemini-3.5-flash" in text
    assert "tool calls" in text.lower()
    assert 'href="index.html"' in html
    assert not any(d in text for d in DASHES)


def test_index_is_written_for_the_treasurer():
    text, html, errors = render("index.html")
    assert errors == []
    assert "Your bank export becomes a Form 990-EZ draft" in text
    assert "Run it on your computer" in text
    assert "What this is not" in text
    assert "sent to Google's Gemini API" in text
    assert text.count("Agents for Humans") == 1
    for banned in ("gemini-3.5", "tool calls", "twelve rows", "conditional node", "free Gemini tier"):
        assert banned not in text, banned
    assert 'href="technical.html"' in html
    assert not any(d in text for d in DASHES)
