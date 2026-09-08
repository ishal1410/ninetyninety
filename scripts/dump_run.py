"""Run the demo ledger through the Strands graph and save everything the
landing page and README quote: lines, totals, disagreements, trace.

    PYTHONPATH=src python scripts/dump_run.py [ledger.csv] [out.json]
"""
import dataclasses, json, sys, time
from pathlib import Path

from ninetyninety.ledger import load_ledger
from ninetyninety.prepare import prepare_ledger

ledger = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures/demo_ledger.csv")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "results/demo_run.json")
skipped: list[dict] = []
rows = load_ledger(ledger, skipped)
started = time.time()
form = prepare_ledger(rows, progress=lambda d, t: print(f"batch {d}/{t}", flush=True))
data = dataclasses.asdict(form)
data["lines"] = {k: dataclasses.asdict(v) for k, v in form.lines.items()}
data["meta"] = {"ledger": ledger.as_posix(), "rows": len(rows), "skipped": skipped,
                "seconds": round(time.time() - started, 1),
                "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "synthetic": False}
out.write_text(json.dumps(data, indent=1))
print("wrote", out, "disagreements", len(form.disagreements), "trace", len(form.trace))
