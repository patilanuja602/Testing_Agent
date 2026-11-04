"""Flexible import of existing Excel complexity reports (.xlsx).

Reports from different tools use different sheet names, header rows and
column names, so the import is a pipeline the UI can drive step by step:

    read sheets -> read raw sheet -> detect header row -> suggest mapping
    -> (user adjusts mapping) -> validate -> normalise into FunctionResult

Imported complexity values follow the *originating tool's* counting
convention, which may differ from this application's analyzer. The original row is preserved in
``FunctionResult.original_data``; values taken from the report are never
mixed with values we compute.

.xls is intentionally not supported in Phase 1: it would need the 'xlrd'
dependency, which has not been included or tested.
"""
from __future__ import annotations

import io
import math
import re
import zipfile
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from config import Limits
from core.language_detector import detect_language
from core.result_normalizer import flag_duplicates
from models.analysis_result import AnalysisStatus, FunctionResult

ENGINE_LABEL = "Imported report"
SUPPORTED_EXTENSIONS = (".xlsx",)
CONVENTION_NOTE = ("Imported complexity values follow the counting convention of the tool that "
                   "produced the report, which may differ from this application's analyzer. They are not recalculated.")


class ExcelImportError(Exception):
    """Raised with a user-readable message."""


# --------------------------------------------------------------------------- headers
def _norm(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


# field -> (exact synonyms, partial-match synonyms)
_SYNONYMS: Dict[str, Tuple[List[str], List[str]]] = {
    "complexity": (["ccn", "cc", "complexity", "cyclomatic", "cyclomatic complexity", "cyclomatic number",
                    "v g", "vg", "mccabe", "mccabe complexity", "cyclomatic complexity ccn"],
                   ["cyclomatic complexity", "cyclomatic", "ccn", "mccabe", "v g"]),
    "function": (["function", "function name", "method", "method name", "name", "routine", "procedure",
                  "func", "function method", "function id", "identifier"],
                 ["function name", "method name", "function", "method", "routine"]),
    "file": (["file", "file name", "filename", "file path", "path", "source file", "source", "module",
              "unit", "translation unit", "location"],
             ["file name", "file path", "source file", "filename", "file"]),
    "start_line": (["start line", "start", "line", "first line", "begin line", "line start", "start row", "line number"],
                   ["start line", "first line", "begin line"]),
    "end_line": (["end line", "end", "last line", "line end", "stop line"], ["end line", "last line"]),
    "threshold": (["threshold", "limit", "max complexity", "allowed", "max", "maximum", "complexity threshold",
                   "ccn threshold", "max v g"],
                  ["threshold", "max complexity", "complexity limit", "max v g"]),
    "nloc": (["nloc", "loc", "lines of code", "code lines", "lines", "sloc"], ["nloc", "lines of code"]),
    "parameters": (["parameters", "params", "parameter count", "args", "arguments", "param count", "number of parameters"],
                   ["parameter count", "parameters", "param count"]),
}
_BLOCKERS = {"complexity": {"threshold", "limit", "max", "maximum", "allowed", "average", "avg"}}
_PRIORITY = ["complexity", "function", "file", "start_line", "end_line", "threshold", "nloc", "parameters"]
FIELD_LABELS = {
    "complexity": "Cyclomatic complexity", "function": "Function name", "file": "File name/path",
    "start_line": "Start line", "end_line": "End line", "threshold": "Report threshold",
    "nloc": "Lines of code", "parameters": "Parameters",
}


def header_score(header: Any, field_name: str) -> float:
    """1.0 exact synonym, 0.6 contains a distinctive phrase, 0 otherwise."""
    h = _norm(header)
    if not h:
        return 0.0
    tokens = set(h.split())
    if tokens & _BLOCKERS.get(field_name, set()):
        return 0.0
    exact, partial = _SYNONYMS[field_name]
    if h in {_norm(s) for s in exact}:
        return 1.0
    for phrase in partial:
        if set(_norm(phrase).split()) <= tokens:
            return 0.6
    return 0.0


@dataclass
class ColumnMapping:
    complexity: Optional[str] = None
    function: Optional[str] = None
    file: Optional[str] = None
    start_line: Optional[str] = None
    end_line: Optional[str] = None
    threshold: Optional[str] = None
    nloc: Optional[str] = None
    parameters: Optional[str] = None

    def used_columns(self) -> List[str]:
        return [getattr(self, f.name) for f in fields(self) if getattr(self, f.name)]


@dataclass
class HeaderDetection:
    row_index: int
    matches: int
    confident: bool


def validate_excel_upload(name: str, data: bytes, limits: Limits) -> None:
    ext = PurePosixPath(name.replace("\\", "/")).suffix.lower()
    if not data:
        raise ExcelImportError("The uploaded file is empty.")
    if ext == ".xls":
        raise ExcelImportError("Legacy .xls files are not supported in this version. "
                               "Open the report in Excel/LibreOffice and save it as .xlsx.")
    if ext not in SUPPORTED_EXTENSIONS:
        raise ExcelImportError(f"Unsupported report type '{ext or name}'. Upload an .xlsx file.")
    if len(data) > limits.max_excel_bytes:
        raise ExcelImportError(f"The report exceeds the size limit ({limits.max_excel_bytes // (1024 * 1024)} MB).")
    if not data.startswith(b"PK"):
        raise ExcelImportError("The file is not a valid .xlsx workbook (it may be corrupted, "
                               "password-protected or have a wrong extension).")


def read_sheet_names(data: bytes) -> List[str]:
    try:
        wb = load_workbook(io.BytesIO(data), read_only=True)
        try:
            return list(wb.sheetnames)
        finally:
            wb.close()
    except (zipfile.BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as exc:
        raise ExcelImportError("The workbook could not be read; it may be corrupted or not a real .xlsx file.") from exc


def read_raw_sheet(data: bytes, sheet: str) -> pd.DataFrame:
    """Whole sheet without header interpretation (all cells as objects)."""
    try:
        raw = pd.read_excel(io.BytesIO(data), sheet_name=sheet, header=None, dtype=object, engine="openpyxl")
    except (zipfile.BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as exc:
        raise ExcelImportError(f"Worksheet '{sheet}' could not be read.") from exc
    raw = raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    if raw.empty:
        raise ExcelImportError(f"Worksheet '{sheet}' is empty.")
    raw.columns = range(raw.shape[1])
    return raw


def detect_header_row(raw: pd.DataFrame, max_scan: int = 30) -> HeaderDetection:
    best_row, best_matches = 0, 0
    for i in range(min(max_scan, len(raw))):
        matches = 0
        for cell in raw.iloc[i].tolist():
            if isinstance(cell, str) and any(header_score(cell, f) >= 0.6 for f in _SYNONYMS):
                matches += 1
        if matches > best_matches:
            best_row, best_matches = i, matches
    return HeaderDetection(best_row, best_matches, confident=best_matches >= 2)


def apply_header(raw: pd.DataFrame, header_row: int) -> pd.DataFrame:
    """Use ``header_row`` as column names; rows above it are discarded."""
    names: List[str] = []
    seen: Dict[str, int] = {}
    for i, cell in enumerate(raw.iloc[header_row].tolist()):
        name = "" if _is_missing(cell) else str(cell).strip()
        name = name or f"Unnamed: {i + 1}"
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f"{name}.{seen[name] - 1}")
    df = raw.iloc[header_row + 1:].copy()
    df.columns = names
    return df.reset_index(drop=True)


def suggest_mapping(df: pd.DataFrame) -> ColumnMapping:
    mapping, taken = ColumnMapping(), set()
    for field_name in _PRIORITY:
        scored = [(header_score(c, field_name), c) for c in df.columns if c not in taken]
        scored = [s for s in scored if s[0] >= 0.6]
        if scored:
            best = max(scored, key=lambda s: s[0])      # first column wins ties
            setattr(mapping, field_name, best[1])
            taken.add(best[1])
    return mapping


@dataclass
class MappingValidation:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_mapping(df: pd.DataFrame, mapping: ColumnMapping) -> MappingValidation:
    result = MappingValidation()
    if not mapping.complexity:
        result.errors.append(
            "No complexity column is selected. Threshold analysis cannot be performed on this report "
            "unless you provide the original source code for analysis.")
    if not mapping.function:
        result.errors.append("No function-name column is selected.")
    for f in fields(mapping):
        col = getattr(mapping, f.name)
        if col and col not in df.columns:
            result.errors.append(f"Column '{col}' (for {FIELD_LABELS[f.name]}) does not exist in the sheet.")
    used = mapping.used_columns()
    dupes = {c for c in used if used.count(c) > 1}
    if dupes:
        result.errors.append("The same column is mapped to more than one field: " + ", ".join(sorted(map(str, dupes))))
    if result.errors:
        return result
    if not mapping.file:
        result.warnings.append("No file column selected: file names will be shown as unavailable.")
    numeric = pd.to_numeric(df[mapping.complexity], errors="coerce")
    if numeric.notna().sum() == 0:
        result.errors.append(f"Column '{mapping.complexity}' contains no numeric complexity values.")
    return result


# --------------------------------------------------------------------------- normalisation
def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        if value is pd.NaT or (not isinstance(value, (str, bytes)) and pd.isna(value)):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and not value.strip()


def _native(value: Any) -> Any:
    if _is_missing(value):
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _parse_int(value: Any, *, minimum: int) -> Tuple[Optional[int], Optional[str]]:
    """(value, problem). A missing value gives (None, None)."""
    if _is_missing(value):
        return None, None
    if isinstance(value, bool):
        return None, "not a number"
    try:
        number = float(str(value).strip().replace(",", ".")) if isinstance(value, str) else float(value)
    except (TypeError, ValueError):
        return None, f"'{str(value)[:30]}' is not a number"
    if math.isnan(number) or math.isinf(number) or number != int(number):
        return None, f"'{str(value)[:30]}' is not a whole number"
    if int(number) < minimum:
        return None, f"{int(number)} is below the minimum valid value ({minimum})"
    return int(number), None


@dataclass
class ImportOutcome:
    results: List[FunctionResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)          # run-level
    skipped_rows: List[Tuple[int, str]] = field(default_factory=list)   # (data row, reason)
    original_columns: List[str] = field(default_factory=list)


_SUMMARY_LABELS = {"total", "totals", "average", "avg", "sum", "summary", "maximum", "minimum", "max", "min", "mean"}


def import_records(df: pd.DataFrame, mapping: ColumnMapping, *, sheet: str, source_name: str) -> ImportOutcome:
    check = validate_mapping(df, mapping)
    if not check.ok:
        raise ExcelImportError(" ".join(check.errors))
    out = ImportOutcome(original_columns=[str(c) for c in df.columns], warnings=list(check.warnings))
    engine_label = f"{ENGINE_LABEL} ({sheet})"

    for i, row in df.iterrows():
        data_row = int(i) + 1
        func_raw = row[mapping.function]
        file_raw = row[mapping.file] if mapping.file else None
        ccn_raw = row[mapping.complexity]
        if all(_is_missing(v) for v in (func_raw, file_raw, ccn_raw)):
            if not all(_is_missing(v) for v in row.tolist()):
                out.skipped_rows.append((data_row, "No function, file or complexity value"))
            continue
        if (not _is_missing(func_raw) and _norm(func_raw) in _SUMMARY_LABELS and _is_missing(file_raw)):
            out.skipped_rows.append((data_row, f"Looks like a summary row ('{str(func_raw).strip()[:30]}')"))
            continue

        warnings: List[str] = []
        ccn, problem = _parse_int(ccn_raw, minimum=1)
        if problem:
            warnings.append(f"Complexity value ignored: {problem}")
        elif ccn is None:
            warnings.append("Complexity value is missing")
        function = "<unnamed>" if _is_missing(func_raw) else str(func_raw).strip()
        if function == "<unnamed>":
            warnings.append("Function name is missing")

        optional: Dict[str, Optional[int]] = {"start_line": None, "end_line": None, "nloc": None, "parameters": None}
        for key, minimum in (("start_line", 1), ("end_line", 1), ("nloc", 0), ("parameters", 0)):
            col = getattr(mapping, key)
            if not col:
                continue
            value, prob = _parse_int(row[col], minimum=minimum)
            if prob:
                warnings.append(f"{FIELD_LABELS[key]} ignored: {prob}")
            optional[key] = value

        imported_threshold = None
        if mapping.threshold and not _is_missing(row[mapping.threshold]):
            try:
                imported_threshold = float(str(row[mapping.threshold]).strip())
            except ValueError:
                warnings.append("Report threshold value is not numeric")

        file_name = None if _is_missing(file_raw) else str(file_raw).strip()
        language = detect_language(file_name).value if file_name and detect_language(file_name) else None
        out.results.append(FunctionResult(
            file=file_name, function=function, ccn=ccn, language=language, engine=engine_label,
            analysis_status=AnalysisStatus.WARNING if warnings else AnalysisStatus.SUCCESS,
            start_line=optional["start_line"], end_line=optional["end_line"], nloc=optional["nloc"],
            parameters=optional["parameters"], warnings=warnings,
            origin="excel", imported_threshold=imported_threshold,
            original_data={str(c): _native(row[c]) for c in df.columns},
        ))
    if flag_duplicates(out.results):
        out.warnings.append("Duplicate function entries were found in the report (flagged, not removed).")
    if not out.results:
        raise ExcelImportError("No usable records were found with the selected columns.")
    return out


def suggest_report_threshold(df: pd.DataFrame, mapping: ColumnMapping) -> Optional[int]:
    """If the report carries exactly one distinct whole-number threshold, return it."""
    if not mapping.threshold or mapping.threshold not in df.columns:
        return None
    values = pd.to_numeric(df[mapping.threshold], errors="coerce").dropna().unique()
    if len(values) == 1 and float(values[0]) == int(values[0]) and int(values[0]) >= 1:
        return int(values[0])
    return None
