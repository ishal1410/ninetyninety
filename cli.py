"""NinetyNinety CLI -- draft a Form 990-EZ from a transaction ledger.

Usage: PYTHONPATH=src python cli.py fixtures/demo_ledger.csv
"""
import sys
from pathlib import Path

from ninetyninety.config import build_model
from ninetyninety.ledger import load_ledger
from ninetyninety.lines import line_by_number
from ninetyninety.prepare import prepare_ledger


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    transactions = load_ledger(Path(argv[1]))
    print(f"Loaded {len(transactions)} transactions. Classifying...")
    form = prepare_ledger(transactions, build_model())

    print("\nFORM 990-EZ PART I (DRAFT -- NOT A FILING)")
    for number in sorted(form.lines, key=lambda n: (len(n), n)):
        result = form.lines[number]
        print(f"  Line {number:<4} {line_by_number(number).label[:44]:<46}"
              f"{result.amount:>10,}  ({len(result.transactions)} txns)")
    print(f"\n  Line 9  total revenue   {form.totals['line9']:>10,}")
    print(f"  Line 17 total expenses  {form.totals['line17']:>10,}")
    print(f"  Line 18 excess/deficit  {form.totals['line18']:>10,}")
    print(f"\nDisagreements: {len(form.disagreements)}   "
          f"Low confidence: {len(form.low_confidence)}   "
          f"Unclassified: {len(form.unclassified)}")
    for item in form.disagreements:
        print(f"  row {item['source_row']}: {item['description'][:44]}")
        print(f"     preparer line {item['preparer']} "
              f"vs reviewer line {item['reviewer']}")
    for item in form.unclassified:
        print(f"  UNCLASSIFIED row {item['source_row']}: {item['description'][:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
