"""How many real 990-EZ filers paid someone to prepare the return?

Counts the paid-preparer block in the ReturnHeader of every Form 990-EZ in the
same public IRS e-file batch the accuracy harness uses. A return with no
PreparerPersonGrp and no PreparerFirmGrp had nobody paid to prepare it.

    PYTHONPATH=src python scripts/preparers.py
"""
import re
import zipfile
from pathlib import Path

from ninetyninety.corpus.index import download_batch

BATCH = "2026_TEOS_XML_01A"
# ponytail: substring test on the header, not a full parse. The two elements
# are only ever emitted inside ReturnHeader, and the header is cut at its own
# closing tag, so a body element cannot be mistaken for one.
PAID = ("<PreparerPersonGrp>", "<PreparerFirmGrp>")
_TYPE = re.compile(r"<ReturnTypeCd>(.*?)</ReturnTypeCd>")


def main() -> None:
    total = paid = 0
    with zipfile.ZipFile(download_batch(BATCH, Path("data"))) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".xml"):
                continue
            text = archive.read(name).decode("utf-8", "replace")
            end = text.find("</ReturnHeader>")
            header = text[:end] if end > 0 else text[:4000]
            kind = _TYPE.search(header)
            if not kind or kind.group(1) != "990EZ":
                continue
            total += 1
            paid += any(element in header for element in PAID)

    print(f"batch {BATCH}")
    print(f"  990-EZ returns:        {total}")
    print(f"  paid preparer signed:  {paid} ({100 * paid / total:.1f}%)")
    print(f"  no paid preparer:      {total - paid} "
          f"({100 * (total - paid) / total:.1f}%)")


if __name__ == "__main__":
    main()
