import csv
import io
from datetime import datetime

from openpyxl import load_workbook

from models.analysis_result import AnalysisRun, AnalysisStatus, FileResult, SkippedFile, ThresholdConfig
from services.report_generator import build_csv, build_workbook
from tests.helpers import fn


def make_run(origin="source"):
    run = AnalysisRun(project_name="Demo", origin=origin, engine="Built-in complexity analyzer" if origin == "source" else "Imported report",
                      engine_version="1.0.0 (core 1.24.3)" if origin == "source" else "", created_at=datetime(2026, 1, 2, 3, 4, 5),
                      selected_languages=["C", "C++"], files_uploaded=4, notes=["a note"], duration_s=0.5)
    run.functions = [
        fn("low", 3, "a.c", start_line=1, end_line=5, nloc=4, parameters=1),
        fn("edge", 10, "a.c", start_line=7, end_line=30, nloc=20, parameters=2),
        fn("high", 25, "b.c", start_line=1, end_line=90, warnings=["Conditional compilation (#if) ..."],
           analysis_status=AnalysisStatus.WARNING),
        fn("=HYPERLINK(\"http://x\")", 2, "c.c"),
        fn("nocc", None, "d.c", analysis_status=AnalysisStatus.WARNING, warnings=["Complexity value is missing"]),
    ]
    run.file_results = [FileResult("a.c", "C", AnalysisStatus.SUCCESS, 2),
                        FileResult("bad.c", "C", AnalysisStatus.FAILED, error="ValueError: boom")]
    run.skipped = [SkippedFile("notes.txt", "Unsupported file type '.txt'", "unsupported")]
    if origin == "excel":
        run.details = {"Worksheet": "S", "_original_columns": ["Module", "V(G)"]}
        for r, v in zip(run.functions, range(5)):
            r.original_data = {"Module": r.file, "V(G)": r.ccn}
    return run


def cfg(value=10):
    return ThresholdConfig(value)


def read(book_bytes):
    return load_workbook(io.BytesIO(book_bytes))


def test_workbook_has_required_sheets():
    wb = read(build_workbook(make_run(), cfg()))
    assert wb.sheetnames == ["Summary", "Function Details", "Threshold Violations", "Analysis Warnings",
                             "Skipped Files", "Configuration"]


def test_summary_values_match_classification_at_each_threshold():
    # make_run() complexities: 3, 10, 25, 2 (+ one unavailable). Rule is fixed: complexity >= threshold.
    for threshold, expected in ((1, 4), (3, 3), (10, 2), (11, 1), (25, 1), (26, 0)):
        wb = read(build_workbook(make_run(), cfg(threshold)))
        summary = {r[0].value: r[1].value for r in wb["Summary"].iter_rows(min_row=3) if r[0].value}
        assert summary["Functions exceeding threshold"] == expected, threshold
        assert summary["Threshold"] == threshold and "Comparison mode" not in summary
        assert summary["Rule"] == f"Exceeds Threshold when complexity >= {threshold}"
        assert wb["Threshold Violations"].max_row - 1 == expected
    summary = {r[0].value: r[1].value for r in read(build_workbook(make_run(), cfg()))["Summary"].iter_rows(min_row=3) if r[0].value}
    assert summary["Analysis engine"] == "Built-in complexity analyzer 1.0.0 (core 1.24.3)"
    assert summary["Functions detected"] == 5 and summary["Files skipped"] == 1 and summary["Files failed"] == 1
    assert summary["Average complexity"] == round((3 + 10 + 25 + 2) / 4, 2)
    assert summary["Project name"] == "Demo" and summary["Analysis date and time"] == "2026-01-02 03:04:05"


def test_a_value_equal_to_the_threshold_is_flagged_in_every_export():
    run = make_run()                                   # contains a function with complexity exactly 10
    wb = read(build_workbook(run, cfg(10)))
    flagged = [r[1] for r in wb["Threshold Violations"].iter_rows(min_row=2, values_only=True)]
    assert "edge" in flagged
    rows = list(csv.reader(io.StringIO(build_csv(run, cfg(10)).decode("utf-8-sig"))))
    status = {r[1]: r[rows[0].index("Status")] for r in rows[1:]}
    assert status["edge"] == "Exceeds Threshold" and status["low"] == "Within Threshold"
    wb = read(build_workbook(run, cfg(11)))
    assert "edge" not in [r[1] for r in wb["Threshold Violations"].iter_rows(min_row=2, values_only=True)]


def test_violations_sorted_and_unavailable_values_marked():
    wb = read(build_workbook(make_run(), cfg()))
    rows = list(wb["Threshold Violations"].iter_rows(min_row=2, values_only=True))
    assert [r[1] for r in rows] == ["high", "edge"]
    details = {r[1]: r for r in wb["Function Details"].iter_rows(min_row=2, values_only=True)}
    assert details["nocc"][4] == "N/A" and details["nocc"][8] == "Analysis Warning"
    assert details["low"][2] == 1 and details["low"][5] == 4


def test_warnings_skipped_and_configuration_sheets():
    wb = read(build_workbook(make_run(), cfg()))
    types = [r[2] for r in wb["Analysis Warnings"].iter_rows(min_row=2, values_only=True)]
    assert "File failed" in types and "Function warning" in types
    assert [r[0] for r in wb["Skipped Files"].iter_rows(min_row=2, values_only=True)] == ["notes.txt"]
    config = {r[0].value: r[1].value for r in wb["Configuration"].iter_rows() if r[0].value}
    assert config["Threshold value"] == 10 and config["Rule"] == "Exceeds Threshold when complexity >= 10"
    assert not {"Threshold source", "Threshold note", "Comparison mode"} & set(config)


def test_formula_strings_stay_text_in_excel_and_are_neutralised_in_csv():
    data = build_workbook(make_run(), cfg())
    ws = read(data)["Function Details"]
    cell = [c for row in ws.iter_rows(min_row=2) for c in row if isinstance(c.value, str) and "HYPERLINK" in c.value][0]
    assert cell.data_type != "f"
    rows = list(csv.reader(io.StringIO(build_csv(make_run(), cfg()).decode("utf-8-sig"))))
    assert any(r[1].startswith("'=HYPERLINK") for r in rows[1:])


def test_csv_contents():
    text = build_csv(make_run(), cfg(11)).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0]
    assert header[:5] == ["File", "Function", "Start Line", "End Line", "Complexity"]
    assert header[-1] == "Threshold" and "Comparison Rule" not in header
    assert len(rows) == 6 and rows[1][-1] == "11"
    status_idx = header.index("Status")
    assert [r[status_idx] for r in rows[1:]].count("Exceeds Threshold") == 1      # only the 25


def test_excel_origin_includes_original_data_sheet():
    run = make_run("excel")
    wb = read(build_workbook(run, cfg()))
    assert "Imported Original Data" in wb.sheetnames
    rows = list(wb["Imported Original Data"].iter_rows(values_only=True))
    assert rows[0] == ("Module", "V(G)") and rows[1] == ("a.c", 3)
    summary = {r[0].value: r[1].value for r in wb["Summary"].iter_rows(min_row=3) if r[0].value}
    assert summary["Input type"] == "Imported Excel report"


def test_empty_run_exports_without_error():
    run = AnalysisRun("Empty", "source", "Built-in complexity analyzer", "1.0.0", datetime.now())
    assert read(build_workbook(run, cfg()))["Function Details"].max_row == 1
    assert build_csv(run, cfg()).startswith(b"\xef\xbb\xbfFile")
