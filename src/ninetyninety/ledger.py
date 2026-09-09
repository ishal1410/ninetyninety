"""The organisation's raw transaction ledger -- the messy input.

Whole dollars as integers. Positive is money in, negative is money out.
`source_row` is the 1-based CSV line number, so every form line can cite the
exact rows it came from.
"""
import codecs
import csv
import io
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
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"not a finite amount: {raw!r}")
    rounded = int(value + 0.5) if value >= 0 else -int(-value + 0.5)
    # "(50)" and "(-50)" are both accountant's negatives; never double-negate.
    return -abs(rounded) if parenthesised else rounded


# Control, bidi-override and zero-width code points: invisible on the page,
# but they reverse rendered text or smuggle prompt lines past the row format.
_DROP = dict.fromkeys(
    [c for c in range(0x20) if c not in (0x09, 0x0A, 0x0D)] + [0x7F]
    + list(range(0x200B, 0x2010)) + list(range(0x202A, 0x202F))
    + list(range(0x2066, 0x206A)) + [0xFEFF])
MAX_DESCRIPTION = 200


def clean_description(text: str) -> str:
    """One line, no '|' (the batch task's column separator), no invisible
    code points, at most MAX_DESCRIPTION characters."""
    text = text.translate(_DROP).replace("|", " ")
    return " ".join(text.split())[:MAX_DESCRIPTION]


def load_ledger(path: Path, skipped: list[dict] | None = None) -> list[Transaction]:
    """Read the CSV. Rows with a description but an unreadable amount are
    appended to `skipped` (if given) so they can be shown to the user."""
    raw = Path(path).read_bytes()
    if raw[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):  # Excel "Unicode Text"
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:  # Windows bank exports are often cp1252
            text = raw.decode("cp1252", errors="replace")
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    try:
        return _read_rows(text, delimiter, skipped)
    except csv.Error as error:  # e.g. a field over the 128 KB limit
        raise ValueError(f"CSV could not be parsed: {error}") from error


def _read_rows(text: str, delimiter: str, skipped: list[dict] | None) -> list[Transaction]:
    transactions: list[Transaction] = []
    with io.StringIO(text, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        # Bank exports capitalise headers ("Date,Description,Amount"): match
        # case- and space-insensitively, and refuse a file with no such columns
        # rather than silently drafting an empty form.
        columns = {(name or "").strip().lower(): name for name in reader.fieldnames or []}
        missing = [c for c in ("description", "amount") if c not in columns]
        if missing:
            raise ValueError(f"CSV is missing column(s) {', '.join(missing)}; "
                             f"expected headers: date, description, amount")
        for row_number, raw in enumerate(reader, start=2):
            row = {key: raw.get(name) for key, name in columns.items()}
            description = clean_description(row.get("description") or "")
            if not description:
                continue
            try:
                amount = parse_amount(row.get("amount") or "")
            except ValueError:
                if skipped is not None:
                    skipped.append({"source_row": row_number,
                                    "description": description,
                                    "amount_raw": row.get("amount") or ""})
                continue
            transactions.append(Transaction(
                date=(row.get("date") or "").strip(),
                description=description,
                amount=amount,
                source_row=row_number,
            ))
    return transactions
