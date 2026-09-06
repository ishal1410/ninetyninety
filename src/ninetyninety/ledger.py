"""The organisation's raw transaction ledger -- the messy input.

Whole dollars as integers. Positive is money in, negative is money out.
`source_row` is the 1-based CSV line number, so every form line can cite the
exact rows it came from.
"""
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Transaction:
    date: str
    description: str
    amount: int
    source_row: int


def parse_amount(raw: str) -> int:
    text = str(raw).strip().replace("$", "").replace(",", "").replace(" ", "")
    if not text:
        raise ValueError("empty amount")
    parenthesised = text.startswith("(") and text.endswith(")")
    if parenthesised:
        text = text[1:-1]
    value = float(text)
    rounded = int(value + 0.5) if value >= 0 else -int(-value + 0.5)
    return -rounded if parenthesised else rounded


def load_ledger(path: Path) -> list[Transaction]:
    transactions: list[Transaction] = []
    with open(Path(path), newline="", encoding="utf-8-sig") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            description = (row.get("description") or "").strip()
            if not description:
                continue
            try:
                amount = parse_amount(row.get("amount") or "")
            except ValueError:
                continue
            transactions.append(Transaction(
                date=(row.get("date") or "").strip(),
                description=description,
                amount=amount,
                source_row=row_number,
            ))
    return transactions
