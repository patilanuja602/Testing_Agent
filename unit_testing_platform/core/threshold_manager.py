"""The single place where threshold comparison is implemented.

The rule is fixed and not user-selectable:  complexity >= threshold  ->  Exceeds Threshold.
Source-code analysis, Excel import, the dashboard and the exports all classify through
``apply_threshold`` below, so they cannot disagree."""
from __future__ import annotations

import dataclasses
from typing import Dict, Iterable, List, Optional

from models.analysis_result import AnalysisStatus, FunctionResult, ThresholdConfig, ThresholdStatus


def exceeds(ccn: int, cfg: ThresholdConfig) -> bool:
    return ccn >= cfg.value


def classify(
    ccn: Optional[int], analysis_status: AnalysisStatus, cfg: ThresholdConfig
) -> ThresholdStatus:
    """Classify one function.

    * a complexity value exists -> Within / Exceeds (the analysis status is
      reported separately, never folded into the score);
    * no value and the entry carries an analysis warning (e.g. an imported row
      with an unreadable value) -> Analysis Warning;
    * no value otherwise -> Not Analyzed.
    """
    if ccn is not None:
        return ThresholdStatus.EXCEEDS if exceeds(ccn, cfg) else ThresholdStatus.WITHIN
    if analysis_status is AnalysisStatus.WARNING:
        return ThresholdStatus.WARNING
    return ThresholdStatus.NOT_ANALYZED


def apply_threshold(results: Iterable[FunctionResult], cfg: ThresholdConfig) -> List[FunctionResult]:
    """Return copies with ``threshold_status`` set. Inputs are not mutated, so
    changing the threshold never requires re-running the analysis."""
    return [
        dataclasses.replace(r, threshold_status=classify(r.ccn, r.analysis_status, cfg))
        for r in results
    ]


def count_by_status(results: Iterable[FunctionResult]) -> Dict[ThresholdStatus, int]:
    counts = {s: 0 for s in ThresholdStatus}
    for r in results:
        counts[r.threshold_status] += 1
    return counts
