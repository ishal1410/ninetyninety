"""Make `python -m pytest` work without PYTHONPATH=src."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
