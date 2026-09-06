"""Print every AcroForm field in the blank IRS Form 990-EZ."""
from pathlib import Path

from pypdf import PdfReader

from ninetyninety.pdffill import download_form


def main() -> None:
    fields = PdfReader(str(download_form(Path("data/f990ez.pdf")))).get_fields() or {}
    print(f"{len(fields)} fields")
    for name, spec in fields.items():
        print(f"  {name}\t{spec.get('/FT')}\t{str(spec.get('/TU'))[:70]}")


if __name__ == "__main__":
    main()
