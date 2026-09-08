import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("build_landing", Path("scripts/build_landing.py"))
TAGS = ('<script id="run" type="application/json">{}</script>'
        '<script id="lines" type="application/json">[]</script>')


def load():
    mod = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(mod)
    return mod


def test_inject_replaces_both_tags_and_escapes_script_close(tmp_path):
    mod = load()
    page = tmp_path / "p.html"
    page.write_text(TAGS, encoding="utf-8")
    html = mod.inject(page, {"a": "</script>"}, [{"number": "1"}])
    assert '"a":"<\/script>"' in html
    assert '<script id="lines" type="application/json">[{"number":"1"}]</script>' in html
    assert page.read_text(encoding="utf-8") == html


def test_inject_is_idempotent(tmp_path):
    mod = load()
    page = tmp_path / "p.html"
    page.write_text(TAGS, encoding="utf-8")
    assert mod.inject(page, {"n": 1}, []) == mod.inject(page, {"n": 1}, [])
