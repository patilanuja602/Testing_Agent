"""End-to-end workflow tests: staging -> analysis -> thresholds -> export."""
import pytest

from core.analyzer import analyze_files
from core.threshold_manager import apply_threshold
from models.analysis_result import AnalysisStatus, Language, ThresholdConfig, ThresholdStatus
from services.project_processor import run_source_analysis
from services.report_generator import build_csv, build_workbook
from services.source_upload import UploadedItem, stage_uploads
from tests.helpers import FIXTURES, SMALL_LIMITS, FakeEngine, make_zip

SRC = b"int f(int a){ if (a) { return 1; } return 0; }\n"
ALL_LANGS = [Language.C, Language.CPP]


def staged(entries):
    return stage_uploads([UploadedItem("p.zip", make_zip(entries))], SMALL_LIMITS)


def test_one_failing_file_does_not_stop_the_others():
    project = staged({"a.c": SRC, "bad.c": SRC, "z.c": SRC})
    try:
        run = run_source_analysis(project, project_name="P", selected_paths={f.display_path for f in project.files},
                                  selected_languages=ALL_LANGS, engine=FakeEngine(fail_for={"bad.c"}))
        assert run.files_failed == 1 and run.files_analyzed == 2
        assert {f.file for f in run.functions} == {"a.c", "z.c"}
        failed = [f for f in run.file_results if f.status is AnalysisStatus.FAILED][0]
        assert failed.path == "bad.c" and failed.error                 # visible, not silent
    finally:
        project.cleanup()


def test_engine_exception_is_contained_by_orchestrator():
    class Exploding(FakeEngine):
        def analyze_file(self, *a, **k):
            raise RuntimeError("secret /internal/path")
    project = staged({"a.c": SRC})
    try:
        run = analyze_files(project.files, Exploding(), project_name="P", selected_languages=ALL_LANGS,
                            files_uploaded=1)
        assert run.files_failed == 1 and "/internal/path" not in run.file_results[0].error
    finally:
        project.cleanup()


def test_selection_filters_and_skipped_reporting():
    project = staged({"a.c": SRC, "b.cpp": SRC, "c.py": b"def f():\n    return 1\n", "x.txt": b"hi"})
    try:
        run = run_source_analysis(project, project_name="P", selected_paths={"a.c"},
                                  selected_languages=[Language.C], engine=FakeEngine())
        assert sorted(f.path for f in run.file_results) == ["a.c"]
        cats = {s.path: s.category for s in run.skipped}
        assert cats["b.cpp"] == "not_selected" and cats["x.txt"] == "unsupported"
        assert run.files_uploaded == 4
    finally:
        project.cleanup()


def test_python_files_are_not_a_supported_source_language():
    project = staged({"a.c": SRC, "tool.py": b"def f():\n    return 1\n"})
    try:
        assert [f.display_path for f in project.files] == ["a.c"]
        skipped = {s.path: s for s in project.skipped}
        assert skipped["tool.py"].category == "unsupported" and ".py" in skipped["tool.py"].reason
    finally:
        project.cleanup()


def test_nothing_selected_gives_error_not_empty_success():
    project = staged({"a.c": SRC})
    try:
        run = run_source_analysis(project, project_name="P", selected_paths=set(), selected_languages=ALL_LANGS,
                                  engine=FakeEngine())
        assert run.errors and not run.functions
    finally:
        project.cleanup()


def test_staging_warnings_make_file_status_warning():
    project = staged({"hdr.h": b"int f(int a);\n", "ok.c": SRC})
    try:
        run = run_source_analysis(project, project_name="P", selected_paths={"hdr.h", "ok.c"},
                                  selected_languages=ALL_LANGS, engine=FakeEngine())
        status = {f.path: f.status for f in run.file_results}
        assert status["hdr.h"] is AnalysisStatus.WARNING and status["ok.c"] is AnalysisStatus.SUCCESS
    finally:
        project.cleanup()


def test_threshold_change_reclassifies_without_reanalysis():
    project = staged({"a.c": SRC})
    try:
        engine = FakeEngine(ccn=10)
        run = run_source_analysis(project, project_name="P", selected_paths={"a.c"}, selected_languages=ALL_LANGS, engine=engine)
        at10 = apply_threshold(run.functions, ThresholdConfig(10))      # equal to the threshold -> flagged
        at11 = apply_threshold(run.functions, ThresholdConfig(11))
        assert at10[0].threshold_status is ThresholdStatus.EXCEEDS and at11[0].threshold_status is ThresholdStatus.WITHIN
    finally:
        project.cleanup()


def test_exports_from_run():
    project = staged({"a.c": SRC, "n.txt": b"x"})
    try:
        run = run_source_analysis(project, project_name="P", selected_paths={"a.c"}, selected_languages=ALL_LANGS, engine=FakeEngine())
        cfg = ThresholdConfig(3)
        assert build_workbook(run, cfg)[:2] == b"PK" and b"a.c" in build_csv(run, cfg)
    finally:
        project.cleanup()


# ---------------------------------------------------------------- bundled analysis core
def test_real_core_zip_workflow():
    from core.complexity import ENGINE_NAME, ComplexityEngine
    entries = {"src/main.c": (FIXTURES / "c" / "constructs.c").read_bytes(),
               "src/Calc.cpp": (FIXTURES / "cpp" / "classes.cpp").read_bytes(),
               "tools/util.py": (FIXTURES / "python" / "constructs.py").read_bytes(),   # not a supported language
               "README.md": b"# demo"}
    project = staged(entries)
    try:
        run = run_source_analysis(project, project_name="Demo", selected_paths={f.display_path for f in project.files},
                                  selected_languages=ALL_LANGS, engine=ComplexityEngine())
        assert run.files_failed == 0 and run.engine == ENGINE_NAME and run.engine_version
        assert {f.file for f in run.functions} == {"src/main.c", "src/Calc.cpp"}
        assert len(run.functions) == 19 and run.duration_s > 0          # 11 (C) + 8 (C++)
        assert sorted(s.path for s in run.skipped) == ["README.md", "tools/util.py"]
    finally:
        project.cleanup()


def test_real_core_malformed_c_is_never_reported_as_plain_success():
    from core.complexity import ComplexityEngine
    project = stage_uploads([UploadedItem("broken.c", b"int f( { if ( ((\n")], SMALL_LIMITS)
    try:
        run = run_source_analysis(project, project_name="P", selected_paths={"broken.c"},
                                  selected_languages=ALL_LANGS, engine=ComplexityEngine())
        assert run.file_results[0].status is not AnalysisStatus.SUCCESS and run.file_results[0].warnings
    finally:
        project.cleanup()


def test_real_core_single_c_and_cpp_uploads_are_analysed():
    from core.complexity import ComplexityEngine
    project = stage_uploads([UploadedItem("a.c", (FIXTURES / "c" / "constructs.c").read_bytes()),
                             UploadedItem("b.cpp", (FIXTURES / "cpp" / "classes.cpp").read_bytes())], SMALL_LIMITS)
    try:
        run = run_source_analysis(project, project_name="P", selected_paths={"a.c", "b.cpp"},
                                  selected_languages=ALL_LANGS, engine=ComplexityEngine())
        assert {f.language for f in run.functions} == {"C", "C++"} and run.files_failed == 0
    finally:
        project.cleanup()


def test_every_output_agrees_on_the_threshold_rule_for_a_real_analysis():
    """Dashboard counts, Excel summary, violations sheet and CSV all come from one classification."""
    import csv
    import io

    from openpyxl import load_workbook

    from core.complexity import ComplexityEngine
    from core.threshold_manager import count_by_status
    project = staged({"src/main.c": (FIXTURES / "c" / "constructs.c").read_bytes(),
                      "src/Calc.cpp": (FIXTURES / "cpp" / "classes.cpp").read_bytes()})
    try:
        run = run_source_analysis(project, project_name="P", selected_paths={f.display_path for f in project.files},
                                  selected_languages=ALL_LANGS, engine=ComplexityEngine())
    finally:
        project.cleanup()
    values = [f.ccn for f in run.functions]
    assert len(values) == 19 and min(values) >= 1
    for threshold in range(1, max(values) + 2):
        cfg = ThresholdConfig(threshold)
        expected = sum(v >= threshold for v in values)                       # independent re-statement of the rule
        counted = count_by_status(apply_threshold(run.functions, cfg))[ThresholdStatus.EXCEEDS]
        wb = load_workbook(__import__("io").BytesIO(build_workbook(run, cfg)))
        summary = {r[0].value: r[1].value for r in wb["Summary"].iter_rows(min_row=3) if r[0].value}
        rows = list(csv.reader(io.StringIO(build_csv(run, cfg).decode("utf-8-sig"))))
        csv_flagged = sum(r[rows[0].index("Status")] == "Exceeds Threshold" for r in rows[1:])
        assert counted == summary["Functions exceeding threshold"] == wb["Threshold Violations"].max_row - 1 \
            == csv_flagged == expected, threshold
