"""NinetyNinety CLI -- draft a Form 990-EZ from a transaction ledger.

Usage: PYTHONPATH=src python cli.py fixtures/demo_ledger.csv
"""
import sys
from pathlib import Path

from ninetyninety.ledger import load_ledger
from ninetyninety.lines import line_by_number
from ninetyninety.prepare import prepare_ledger


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    skipped: list[dict] = []
    transactions = load_ledger(Path(argv[1]), skipped)
    note = f", skipped {len(skipped)} with unreadable amounts" if skipped else ""
    print(f"Loaded {len(transactions)} transactions{note}. Classifying through the Strands graph...")
    form = prepare_ledger(
        transactions, progress=lambda done, total: print(f"  batch {done}/{total} done"))

    print("\nFORM 990-EZ PART I (DRAFT -- NOT A FILING)")
    for number in sorted(form.lines, key=lambda n: (len(n), n)):
        result = form.lines[number]
        print(f"  Line {number:<4} {line_by_number(number).label[:44]:<46}"
              f"{result.amount:>10,}  ({len(result.transactions)} txns)")
    print(f"\n  Line 9  total revenue   {form.totals['line9']:>10,}")
    print(f"  Line 17 total expenses  {form.totals['line17']:>10,}")
    print(f"  Line 18 excess/deficit  {form.totals['line18']:>10,}")
    print(f"\nDisagreements: {len(form.disagreements)}   Low confidence: {len(form.low_confidence)}   "
          f"Unclassified: {len(form.unclassified)}   Unreviewed: {len(form.unreviewed)}   "
          f"Ungrounded rules: {len(form.ungrounded)}")
    for item in form.disagreements:
        print(f"  row {item['source_row']}: {item['description'][:44]}")
        print(f"     preparer {item['preparer']} vs reviewer {item['reviewer']}"
              f" -> referee {item['referee'] or 'did not rule'}; used line {item['used']}")
        if item["referee_reason"]:
            print(f"     {item['referee_reason'][:140]}")
    for item in form.ungrounded:
        print(f"  UNGROUNDED row {item['source_row']} line {item['line']}: {item['rule'][:80]!r}")
    for item in form.unclassified:
        print(f"  UNCLASSIFIED row {item['source_row']}: {item['description'][:44]} ({item['error'][:60]})")
    for item in skipped:
        print(f"  SKIPPED row {item['source_row']}: {item['description'][:44]}  amount {item['amount_raw']!r}")

    print("\nSTRANDS TRACE")
    for t in form.trace:
        if t.get("error"):
            print(f"  batch {t['batch']}: {t['error']}")
        else:
            print(f"  batch {t['batch']}: {t['rows']} rows via {t['provider']} in {t['seconds']}s; "
                  f"nodes {'->'.join(t['nodes'])}; tool calls {t['tool_calls']}; "
                  f"referee {'ran' if t['referee_ran'] else 'skipped'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
