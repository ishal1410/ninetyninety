"""Download a real IRS batch and publish the reconstruction accuracy rate."""
import json
from pathlib import Path

from ninetyninety.corpus.index import download_batch
from ninetyninety.corpus.validate import validate_batch

BATCH = "2026_TEOS_XML_01A"
LABELS = (("line9", "Line 9  total revenue "),
          ("line17", "Line 17 total expenses"),
          ("line18", "Line 18 excess/deficit"))


def main() -> None:
    report = validate_batch(download_batch(BATCH, Path("data")))
    print(f"990-EZ returns: {report.total}")
    for key, label in LABELS:
        print(f"  {label} {report.matched[key]}/{report.checked[key]}"
              f"  ({report.rate(key):.2f}%)")
    print(f"  filed returns whose own totals disagree: {len(report.mismatches)}")

    Path("results").mkdir(exist_ok=True)
    Path("results/validation.json").write_text(json.dumps({
        "batch": BATCH,
        "returns": report.total,
        "matched": report.matched,
        "checked": report.checked,
        "rates": {key: round(report.rate(key), 2) for key in report.matched},
        "mismatch_count": len(report.mismatches),
        "mismatches": report.mismatches[:20],
    }, indent=2), encoding="utf-8")
    print("wrote results/validation.json")


if __name__ == "__main__":
    main()
