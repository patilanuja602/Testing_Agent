"""Helpers shared by every result source: duplicate flagging and conversion
to tabular form."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from models.analysis_result import AnalysisStatus, FunctionResult


def flag_duplicates(results: List[FunctionResult]) -> int:
    """Mark entries that repeat the same (file, function, start line).

    When start lines are unknown (typical for Excel reports) the key is
    (file, function) and the message says it may be a legitimate overload.
    Entries are flagged, never removed. Returns number of flagged entries."""
    def key(r: FunctionResult):
        return (r.file, r.function, r.start_line)

    counts = Counter(key(r) for r in results)
    flagged = 0
    for r in results:
        if counts[key(r)] > 1:
            hint = ("" if r.start_line is not None else
                    " (no start line available: this may be an overload or a repeated row)")
            msg = f"Duplicate entry for this file/function{hint}"
            if msg not in r.warnings:
                r.warnings.append(msg)
            if r.analysis_status is AnalysisStatus.SUCCESS:
                r.analysis_status = AnalysisStatus.WARNING
            flagged += 1
    return flagged


def fmt_optional(value: Any) -> Any:
    """Export representation of an unavailable value."""
    return "N/A" if value is None else value


def results_to_dataframe(results: Iterable[FunctionResult]) -> pd.DataFrame:
    """UI-facing table. Unavailable numbers stay as missing values (None) so
    sorting and range filtering keep working; exports show them as 'N/A'."""
    rows: List[Dict[str, Any]] = []
    for r in results:
        rows.append({
            "File": r.file,
            "Function": r.function,
            "Start Line": r.start_line,
            "End Line": r.end_line,
            "Complexity": r.ccn,
            "Lines of Code": r.nloc,
            "Parameters": r.parameters,
            "Status": r.threshold_status.value,
            "Language": r.language,
            "Analysis Status": r.analysis_status.value,
            "Warnings": "; ".join(r.warnings),
        })
    cols = ["File", "Function", "Start Line", "End Line", "Complexity", "Lines of Code",
            "Parameters", "Status", "Language", "Analysis Status", "Warnings"]
    df = pd.DataFrame(rows, columns=cols)
    for c in ("Start Line", "End Line", "Complexity", "Lines of Code", "Parameters"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    return df


def average_complexity(results: Iterable[FunctionResult]) -> Optional[float]:
    values = [r.ccn for r in results if r.ccn is not None]
    return sum(values) / len(values) if values else None
