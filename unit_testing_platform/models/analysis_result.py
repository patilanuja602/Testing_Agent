"""Shared data model. Every analysis path (source code or imported Excel)
is normalised into these structures so the dashboard and reports are
independent of where the numbers came from."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class Language(str, Enum):
    C = "C"
    CPP = "C++"
    # Defined but NOT enabled in this release (see core/language_detector.py for how to enable it).
    PYTHON = "Python"


class ThresholdStatus(str, Enum):
    WITHIN = "Within Threshold"
    EXCEEDS = "Exceeds Threshold"
    NOT_ANALYZED = "Not Analyzed"
    WARNING = "Analysis Warning"


class AnalysisStatus(str, Enum):
    """Quality of the analysis itself. Deliberately separate from the score."""
    SUCCESS = "Successful"
    WARNING = "Warning"
    FAILED = "Failed"


@dataclass(frozen=True)
class ThresholdConfig:
    """The one complexity threshold. The comparison is fixed: complexity >= value."""
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int) or self.value < 1:
            raise ValueError(f"The complexity threshold must be a positive integer, got {self.value!r}")

    def rule_text(self) -> str:
        return f"Exceeds Threshold when complexity >= {self.value}"


@dataclass
class FunctionResult:
    file: Optional[str]
    function: str
    ccn: Optional[int]
    language: Optional[str]
    engine: str
    analysis_status: AnalysisStatus = AnalysisStatus.SUCCESS
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    nloc: Optional[int] = None
    parameters: Optional[int] = None
    token_count: Optional[int] = None
    long_name: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    threshold_status: ThresholdStatus = ThresholdStatus.NOT_ANALYZED
    origin: str = "source"                      # "source" | "excel"
    # Excel only: untouched row as found in the report, and metrics imported
    # from it (kept apart from values we computed ourselves).
    original_data: Dict[str, Any] = field(default_factory=dict)
    imported_threshold: Optional[float] = None


@dataclass
class StagedFile:
    display_path: str        # relative path shown to the user
    disk_path: Path          # location inside the temporary workspace
    language: Language
    size: int
    warnings: List[str] = field(default_factory=list)
    # Ambiguous headers (.h): True when the project gives no reliable evidence whether the header
    # is C or C++. Such a header is then analysed in the language the user selected (see below).
    header_ambiguous: bool = False
    language_basis: str = ""             # how ``language`` was decided (shown to the user)

    def effective_language(self, selected) -> Language:
        """Language the file is analysed (and reported) as under the user's language selection.
        Only an ambiguous header depends on the selection: C++ when C++ alone is selected,
        otherwise C."""
        if not self.header_ambiguous:
            return self.language
        return Language.CPP if set(selected) == {Language.CPP} else Language.C

    def is_selectable(self, selected) -> bool:
        """Is the file offered for analysis under the user's language selection? An ambiguous
        header is offered whenever C or C++ is selected; any other file only for its language."""
        selected = set(selected)
        if self.header_ambiguous:
            return bool(selected & {Language.C, Language.CPP})
        return self.language in selected


@dataclass
class SkippedFile:
    path: str
    reason: str
    category: str            # unsupported | ignored | invalid | too_large | unsafe | not_selected


@dataclass
class FileResult:
    path: str
    language: Optional[str]
    status: AnalysisStatus
    function_count: int = 0
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_s: float = 0.0


@dataclass
class AnalysisRun:
    project_name: str
    origin: str                                   # "source" | "excel"
    engine: str
    engine_version: str
    created_at: datetime
    selected_languages: List[str] = field(default_factory=list)
    files_uploaded: int = 0
    file_results: List[FileResult] = field(default_factory=list)
    functions: List[FunctionResult] = field(default_factory=list)
    skipped: List[SkippedFile] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    duration_s: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)   # e.g. Excel sheet info

    @property
    def files_analyzed(self) -> int:
        return sum(1 for f in self.file_results if f.status != AnalysisStatus.FAILED)

    @property
    def files_failed(self) -> int:
        return sum(1 for f in self.file_results if f.status == AnalysisStatus.FAILED)
