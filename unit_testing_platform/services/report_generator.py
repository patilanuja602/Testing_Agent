"""Excel and CSV report generation.

Reports are snapshots: values are written as computed by the application
(not live formulas) so they open identically in any spreadsheet program.
Unavailable values are written as 'N/A'."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, Iterable, List, Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from core.result_normalizer import average_complexity, fmt_optional
from core.threshold_manager import apply_threshold, count_by_status
from models.analysis_result import AnalysisRun, AnalysisStatus, FunctionResult, ThresholdConfig, ThresholdStatus

FONT = "Arial"
_HEADER_FILL = PatternFill("solid", start_color="1F3A5F")
_VIOLATION_FILL = PatternFill("solid", start_color="FDE9E7")
DETAIL_COLUMNS = ["File", "Function", "Start Line", "End Line", "Complexity", "Lines of Code", "Parameters",
                  "Token Count", "Status", "Language", "Engine", "Analysis Status", "Warnings"]


def sanitize_cell(value: Any) -> Any:
    """CSV only: neutralise formula injection when the file is opened in a spreadsheet.
    (In .xlsx, string cells are stored as text, so only the data type is forced.)"""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def function_rows(results: Iterable[FunctionResult]) -> List[List[Any]]:
    return [[
        fmt_optional(r.file), r.function, fmt_optional(r.start_line), fmt_optional(r.end_line),
        fmt_optional(r.ccn), fmt_optional(r.nloc), fmt_optional(r.parameters), fmt_optional(r.token_count),
        r.threshold_status.value, fmt_optional(r.language), r.engine, r.analysis_status.value,
        "; ".join(r.warnings),
    ] for r in results]


def build_csv(run: AnalysisRun, cfg: ThresholdConfig) -> bytes:
    """UTF-8 (with BOM, so Excel detects the encoding) function-level CSV."""
    results = apply_threshold(run.functions, cfg)
    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(DETAIL_COLUMNS + ["Threshold"])
    for row in function_rows(results):
        writer.writerow([sanitize_cell(v) for v in row] + [cfg.value])
    return buf.getvalue().encode("utf-8-sig")


def _write_table(ws, headers: Sequence[str], rows: Sequence[Sequence[Any]], *, widths: Dict[int, int] = None,
                 highlight_col: int = 0) -> None:
    ws.append(list(headers))
    for cell in ws[1]:
        cell.font = Font(name=FONT, bold=True, color="FFFFFF")
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for row in rows:
        ws.append(list(row))
        for cell in ws[ws.max_row]:
            cell.font = Font(name=FONT)
            if cell.data_type == "f":                 # never keep a user string as a formula
                cell.data_type = "s"
        if highlight_col and row[highlight_col - 1] == ThresholdStatus.EXCEEDS.value:
            for cell in ws[ws.max_row]:
                cell.fill = _VIOLATION_FILL
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws.max_row}"
    for i, header in enumerate(headers, start=1):
        longest = max([len(str(header))] + [len(str(r[i - 1])) for r in rows[:300] if i - 1 < len(r)])
        ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(i, min(max(longest + 2, 10), 60))


def _key_values(ws, pairs: Sequence[Sequence[Any]]) -> None:
    for key, value in pairs:
        ws.append([key, value])
        ws.cell(ws.max_row, 1).font = Font(name=FONT, bold=True)
        ws.cell(ws.max_row, 2).font = Font(name=FONT)
        ws.cell(ws.max_row, 2).alignment = Alignment(wrap_text=True, vertical="top")
        if ws.cell(ws.max_row, 2).data_type == "f":
            ws.cell(ws.max_row, 2).data_type = "s"
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 90


def build_workbook(run: AnalysisRun, cfg: ThresholdConfig) -> bytes:
    results = apply_threshold(run.functions, cfg)
    counts = count_by_status(results)
    avg = average_complexity(results)
    violations = [r for r in results if r.threshold_status is ThresholdStatus.EXCEEDS]
    warned = [r for r in results if r.warnings]
    failed_or_warned_files = [f for f in run.file_results if f.status is not AnalysisStatus.SUCCESS]
    is_source = run.origin == "source"

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Cyclomatic Complexity Report"])
    ws["A1"].font = Font(name=FONT, bold=True, size=14)
    pairs: List[Sequence[Any]] = [
        ("Project name", run.project_name),
        ("Analysis date and time", run.created_at.strftime("%Y-%m-%d %H:%M:%S")),
        ("Input type", "Source code analysis" if is_source else "Imported Excel report"),
        ("Analysis engine", f"{run.engine} {run.engine_version}".strip()),
        ("Selected languages", ", ".join(run.selected_languages) or "N/A"),
        ("Threshold", cfg.value),
        ("Rule", cfg.rule_text()),
        ("Files uploaded", run.files_uploaded if is_source else "N/A"),
        ("Files analysed", run.files_analyzed if is_source else "N/A"),
        ("Files failed", run.files_failed if is_source else "N/A"),
        ("Files skipped", len(run.skipped) if is_source else "N/A"),
        ("Functions detected" if is_source else "Functions imported", len(results)),
        ("Functions exceeding threshold", counts[ThresholdStatus.EXCEEDS]),
        ("Functions within threshold", counts[ThresholdStatus.WITHIN]),
        ("Functions not analysed / with analysis warning", f"{counts[ThresholdStatus.NOT_ANALYZED]} / {counts[ThresholdStatus.WARNING]}"),
        ("Average complexity", round(avg, 2) if avg is not None else "N/A"),
        ("Analysis duration (s)", round(run.duration_s, 3)),
    ]
    ws.append([])
    _key_values(ws, pairs)
    ws.append([])
    _key_values(ws, [("Notes", " | ".join(run.notes + run.errors) or "None"),
                     ("N/A", "Value unavailable from the analysis engine or the imported report.")])

    ws = wb.create_sheet("Function Details")
    _write_table(ws, DETAIL_COLUMNS, function_rows(results), highlight_col=9)

    ws = wb.create_sheet("Threshold Violations")
    _write_table(ws, DETAIL_COLUMNS, function_rows(sorted(violations, key=lambda r: -(r.ccn or 0))), highlight_col=9)

    ws = wb.create_sheet("Analysis Warnings")
    warning_rows: List[List[Any]] = [[f.path, "(file)", "File failed" if f.status is AnalysisStatus.FAILED else "File warning",
                                      f.error or "; ".join(f.warnings)] for f in failed_or_warned_files]
    warning_rows += [[fmt_optional(r.file), r.function, "Function warning", "; ".join(r.warnings)] for r in warned]
    warning_rows += [["(run)", "", "Error", e] for e in run.errors]
    _write_table(ws, ["File", "Function", "Type", "Message"], warning_rows)

    ws = wb.create_sheet("Skipped Files")
    _write_table(ws, ["File", "Category", "Reason"], [[s.path, s.category, s.reason] for s in run.skipped])

    ws = wb.create_sheet("Configuration")
    _key_values(ws, [
        ("Threshold value", cfg.value), ("Rule", cfg.rule_text()),
        ("Engine", run.engine), ("Engine version", run.engine_version),
        ("Selected languages", ", ".join(run.selected_languages) or "N/A"),
        *[(str(k), v) for k, v in run.details.items() if not str(k).startswith("_")],
    ])

    if not is_source:
        ws = wb.create_sheet("Imported Original Data")
        columns = list(run.details.get("_original_columns", []))
        rows = [[r.original_data.get(c) for c in columns] for r in run.functions]
        _write_table(ws, columns or ["(no columns)"], rows)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
