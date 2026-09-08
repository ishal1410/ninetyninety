"""Inject the recorded demo run, the validation results and the Part I line
taxonomy into every page that carries the data tags, in place. Idempotent.

    PYTHONPATH=src python scripts/build_landing.py
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "technical.html"]


def _put(html: str, tag_id: str, payload) -> str:
    blob = json.dumps(payload, separators=(",", ":")).replace("</", "<\/")
    new, n = re.subn(rf'(<script id="{tag_id}" type="application/json">).*?(</script>)',
                     lambda m: m.group(1) + blob + m.group(2), html, count=1, flags=re.S)
    assert n == 1, f"{tag_id} tag missing"
    return new


def inject(page: Path, payload: dict, lines: list) -> str:
    html = page.read_text(encoding="utf-8")
    html = _put(html, "run", payload)
    html = _put(html, "lines", lines)
    page.write_text(html, encoding="utf-8", newline="\n")
    return html


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    from ninetyninety.lines import REVENUE_LINES, EXPENSE_LINES
    run = json.loads((ROOT / "results/demo_run.json").read_text())
    run["validation"] = json.loads((ROOT / "results/validation.json").read_text())
    run["validation"].pop("mismatches", None)
    lines = [{"number": l.number, "label": l.label, "kind": l.kind} for l in REVENUE_LINES + EXPENSE_LINES]
    for name in PAGES:
        page = ROOT / name
        if page.exists():
            inject(page, run, lines)
            print("injected", name, "synthetic =", run.get("meta", {}).get("synthetic"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
