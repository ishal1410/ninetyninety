"""Client for the IRS Form 990 e-file XML corpus.

Measured 2026-09-06: the 2026 index holds 385,890 returns of which 121,299 are
990-EZ. Directory listing at this path 404s -- files are reachable only by
exact filename, and a batch's filename is its XML_BATCH_ID plus '.zip'.
"""
import csv
import os
from pathlib import Path

import requests

BASE = "https://apps.irs.gov/pub/epostcard/990/xml/2026"
INDEX_URL = f"{BASE}/index_2026.csv"
TIMEOUT = 300


def batch_url(batch_id: str) -> str:
    return f"{BASE}/{batch_id}.zip"


def _download(url: str, dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    response = requests.get(url, timeout=TIMEOUT, stream=True)
    response.raise_for_status()
    # Stream to a sidecar and rename only once complete, so an interrupted
    # 70MB download is never mistaken for a finished one by the size check.
    partial = dest.with_name(dest.name + ".part")
    with open(partial, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1 << 20):
            handle.write(chunk)
    os.replace(partial, dest)
    return dest


def download_index(dest: Path) -> Path:
    return _download(INDEX_URL, dest)


def download_batch(batch_id: str, dest_dir: Path) -> Path:
    return _download(batch_url(batch_id), Path(dest_dir) / f"{batch_id}.zip")


def read_index(path: Path, return_type: str = "990EZ") -> list[dict]:
    with open(path, newline="", encoding="latin-1") as handle:
        return [row for row in csv.DictReader(handle)
                if row.get("RETURN_TYPE") == return_type]
