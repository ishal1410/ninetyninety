"""Reconstruct real filed 990-EZ returns from their own components.

Runs the SAME formmath module that fills a user's form, so the accuracy rate
it publishes describes the real code path rather than a validation-only
reimplementation.
"""
from dataclasses import dataclass, field
from pathlib import Path

from ..formmath import check_identities
from .xmlparse import FiledReturn, iter_990ez

KEYS = ("line9", "line17", "line18")


def score_return(filed_return: FiledReturn) -> dict[str, bool]:
    return check_identities(filed_return.amounts, filed_return.filed)


@dataclass
class ValidationReport:
    total: int = 0
    matched: dict[str, int] = field(default_factory=lambda: {k: 0 for k in KEYS})
    checked: dict[str, int] = field(default_factory=lambda: {k: 0 for k in KEYS})
    mismatches: list[dict] = field(default_factory=list)

    def add(self, filed_return: FiledReturn, scores: dict[str, bool]) -> None:
        self.total += 1
        for key in KEYS:
            if key not in filed_return.filed:
                continue
            self.checked[key] += 1
            if scores[key]:
                self.matched[key] += 1
            else:
                self.mismatches.append({
                    "ein": filed_return.ein, "name": filed_return.name,
                    "key": key, "filed": filed_return.filed.get(key),
                    "components": filed_return.amounts,
                })

    def rate(self, key: str) -> float:
        if not self.checked[key]:
            return 0.0
        return 100.0 * self.matched[key] / self.checked[key]

    @property
    def line9(self) -> tuple[int, int]:
        return self.matched["line9"], self.checked["line9"]

    @property
    def line17(self) -> tuple[int, int]:
        return self.matched["line17"], self.checked["line17"]

    @property
    def line18(self) -> tuple[int, int]:
        return self.matched["line18"], self.checked["line18"]


def validate_batch(zip_path: Path, limit: int | None = None) -> ValidationReport:
    report = ValidationReport()
    for filed_return in iter_990ez(Path(zip_path)):
        report.add(filed_return, score_return(filed_return))
        if limit is not None and report.total >= limit:
            break
    return report
