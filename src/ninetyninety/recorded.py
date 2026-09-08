"""Replay the recorded demo run (results/demo_run.json, written by
scripts/dump_run.py) so the hosted app still shows a full draft when the
free-tier quota for the day is gone."""
import json
from pathlib import Path

from .prepare import Form990EZ, LineResult

KEEP = ("totals", "disagreements", "low_confidence", "unclassified",
        "unreviewed", "ungrounded", "trace")


def load_recorded_run(path: Path) -> Form990EZ:
    data = json.loads(path.read_text(encoding="utf-8"))
    form = Form990EZ(**{k: data[k] for k in KEEP if k in data})
    form.lines = {k: LineResult(**v) for k, v in data["lines"].items()}
    return form
