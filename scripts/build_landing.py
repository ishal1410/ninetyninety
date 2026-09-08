"""Inject the recorded demo run, the validation results and the Part I line
taxonomy into index.html, in place. Idempotent.

    PYTHONPATH=src python scripts/build_landing.py
"""
import json, re
from pathlib import Path
from ninetyninety.lines import REVENUE_LINES, EXPENSE_LINES

root = Path(__file__).resolve().parent.parent
page = root / "index.html"
run = json.loads((root / "results/demo_run.json").read_text())
run["validation"] = json.loads((root / "results/validation.json").read_text())
run["validation"].pop("mismatches", None)
lines = [{"number": l.number, "label": l.label, "kind": l.kind} for l in REVENUE_LINES + EXPENSE_LINES]
html = page.read_text(encoding="utf-8")
def put(html, tag_id, payload):
    blob = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    new, n = re.subn(rf'(<script id="{tag_id}" type="application/json">).*?(</script>)',
                     lambda m: m.group(1) + blob + m.group(2), html, count=1, flags=re.S)
    assert n == 1, tag_id
    return new
html = put(html, "run", run)
html = put(html, "lines", lines)
page.write_text(html, encoding="utf-8", newline="\n")
print("injected", len(run["lines"]), "lines,", len(run["trace"]), "trace rows, synthetic =", run.get("meta", {}).get("synthetic"))
