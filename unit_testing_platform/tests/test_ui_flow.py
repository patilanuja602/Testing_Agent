"""End-to-end and UI behaviour tests that drive the real Streamlit script (AppTest).

What they verify: the values and tables the application hands to Streamlit (recorded by the autouse
fixture in conftest.py), session state, metrics, messages. With pyarrow installed the real Streamlit
rendering call is made as well; see conftest.py for what is and is not covered without it.
Expected values are hand-derived from the C sources below (CCN = 1 + decisions).
"""
import csv
import io
from pathlib import Path

import pytest
from openpyxl import load_workbook

from tests.conftest import TABLES
from tests.helpers import make_zip

ROOT = Path(__file__).parent.parent
APP = str(ROOT / "app.py")

SENSOR_C = b'''#include "../include/sensor.h"
int adc(int ch);

int read_sensor(int ch, int *out)
{
    int i;
    if (ch < 0 || ch > 7)
        return -1;
    for (i = 0; i < 3; i++) {
        if (adc(ch) > 0) {
            *out = adc(ch);
            return 0;
        }
    }
    return -2;
}

int scale(int v)
{
    return v * 2;
}
'''                    # read_sensor: 1 + if + || + for + if = 5 ; scale: 1
CONTROL_C = b'''static int clamp(int v, int lo, int hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

int pid_step(int e, int *acc)
{
    int out = 0;
    if (e > 100 && *acc > 0) {
        out = 1;
    } else if (e < -100 || *acc < 0) {
        out = 2;
    }
    while (*acc > 1000)
        *acc -= 10;
    return e > 0 ? out : -out;
}
'''                    # clamp: 3 ; pid_step: 1 + if + && + else-if + || + while + ? = 7
SENSOR_H = b'''#ifndef SENSOR_H
#define SENSOR_H
static inline int sat(int v) { return v > 255 ? 255 : v; }
#endif
'''                    # sat: 2
C_PROJECT = {"src/sensor.c": SENSOR_C, "src/control.c": CONTROL_C, "include/sensor.h": SENSOR_H,
             "README.txt": b"notes\n"}
EXPECTED = {"read_sensor": 5, "scale": 1, "clamp": 3, "pid_step": 7, "sat": 2}


def new_app():
    testing = pytest.importorskip("streamlit.testing.v1")
    return testing.AppTest.from_file(APP, default_timeout=60).run()


def run_step(widget_action):
    TABLES.clear()
    widget_action()


def tables(kind, *columns):
    return [df for k, df in TABLES if k == kind and set(columns) <= set(df.columns)]


def metrics(at):
    return {m.label: m.value for m in at.metric}


def upload(at, name, data, mime="application/zip"):
    TABLES.clear()
    at.file_uploader(key="src_uploader").upload(name, data, mime)
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def analyse(at):
    TABLES.clear()
    at.button(key="src_run_btn").click().run()
    assert not at.exception, [e.value for e in at.exception]


def set_threshold(at, value):
    TABLES.clear()
    at.sidebar.number_input(key="threshold").set_value(value).run()
    assert not at.exception, [e.value for e in at.exception]


def function_table():
    frames = tables("dataframe", "Function", "Complexity", "Status")
    assert frames, "no function table was rendered"
    return frames[0]


def ccn_by_function(df):
    return {r["Function"]: int(r["Complexity"]) for r in df.to_dict("records")}


# ======================================================================= task 8: end to end, C project
def test_end_to_end_c_project_threshold_range_inspection_and_export():
    at = new_app()
    upload(at, "c_project.zip", make_zip(C_PROJECT))

    # --- upload is validated and summarised
    summary = next(m.value for m in at.markdown if m.value.startswith("Received"))
    assert "**4** file(s)" in summary and "**3** supported" in summary and "**1** skipped" in summary
    selection = tables("data_editor", "Analyze", "File", "Language")[0]
    assert sorted(selection["File"]) == ["include/sensor.h", "src/control.c", "src/sensor.c"]
    header = selection[selection["File"] == "include/sensor.h"].iloc[0]
    assert header["Language"] == "C" and "included only by C source files" in header["Notes"]

    # --- analysis
    analyse(at)
    m = metrics(at)
    assert (m["Files uploaded"], m["Files analyzed"], m["Files skipped"], m["Files failed"]) == ("4", "3", "1", "0")
    assert m["Functions detected"] == "5" and m["Average complexity"] == "3.60"
    results = function_table()
    assert ccn_by_function(results) == EXPECTED
    pid = results[results["Function"] == "pid_step"].iloc[0]
    assert (pid["File"], pid["Start Line"], pid["Language"]) == ("src/control.c", 8, "C")

    # --- threshold 3 (>=): 5, 3, 7 exceed; 1, 2 are within
    set_threshold(at, 3)
    m = metrics(at)
    assert (m["Exceeding threshold"], m["Within threshold"]) == ("3", "2")
    status = {r["Function"]: r["Status"] for r in function_table().to_dict("records")}
    assert status == {"read_sensor": "Exceeds Threshold", "scale": "Within Threshold", "clamp": "Exceeds Threshold",
                      "pid_step": "Exceeds Threshold", "sat": "Within Threshold"}

    # --- complexity range 3..5 selects read_sensor (5) and clamp (3)
    TABLES.clear()
    at.slider(key="src_rng").set_range(3, 5).run()
    assert not at.exception, [e.value for e in at.exception]
    assert sorted(ccn_by_function(function_table())) == ["clamp", "read_sensor"]
    assert any("Showing 2 of 5 functions" in c.value for c in at.caption)

    # --- inspect one selected function
    rows = function_table()["Function"].tolist()
    TABLES.clear()
    at.selectbox(key="src_inspect").set_value(rows.index("read_sensor")).run()
    assert not at.exception, [e.value for e in at.exception]
    details = {r["Property"]: r["Value"] for df in tables("dataframe", "Property", "Value") for r in df.to_dict("records")}
    assert details["Function"] == "read_sensor" and details["File"] == "src/sensor.c"
    assert details["Complexity"] == "5" and details["Threshold status"] == "Exceeds Threshold"
    assert details["Start line"] == "4" and details["Parameters"] == "2"

    # --- export (threshold 3): the report contains every function; the range view is a display filter only
    at.button(key="src_prepare").click().run()
    assert not at.exception, [e.value for e in at.exception]
    _, xlsx, csv_bytes = at.session_state["src_export"]
    assert len(at.get("download_button")) == 2
    wb = load_workbook(io.BytesIO(xlsx))
    assert wb.sheetnames[:3] == ["Summary", "Function Details", "Threshold Violations"]
    detail = list(wb["Function Details"].iter_rows(values_only=True))
    head = detail[0]
    by_name = {r[head.index("Function")]: (r[head.index("Complexity")], r[head.index("Status")]) for r in detail[1:]}
    assert by_name == {n: (c, "Exceeds Threshold" if c >= 3 else "Within Threshold") for n, c in EXPECTED.items()}
    violations = list(wb["Threshold Violations"].iter_rows(values_only=True))
    assert sorted(r[head.index("Function")] for r in violations[1:]) == ["clamp", "pid_step", "read_sensor"]
    reader = list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
    assert {r["Function"]: int(r["Complexity"]) for r in reader} == EXPECTED
    assert {r["Threshold"] for r in reader} == {"3"}
    assert {r["Status"] for r in reader if r["Function"] in ("clamp", "pid_step", "read_sensor")} == {"Exceeds Threshold"}


def test_status_filter_and_search_narrow_the_function_table():
    at = new_app()
    upload(at, "p.zip", make_zip(C_PROJECT))
    analyse(at)
    set_threshold(at, 5)                                     # exceeds: read_sensor 5, pid_step 7
    TABLES.clear()
    at.multiselect(key="src_status").set_value(["Exceeds Threshold"]).run()
    assert sorted(ccn_by_function(function_table())) == ["pid_step", "read_sensor"]
    TABLES.clear()
    at.text_input(key="src_q").set_value("pid").run()
    assert list(ccn_by_function(function_table())) == ["pid_step"]
    assert any("Showing 1 of 5 functions" in c.value for c in at.caption)


@pytest.mark.parametrize("threshold,exceeding", [(1, 5), (2, 4), (3, 3), (5, 2), (7, 1), (8, 0)])
def test_threshold_boundary_is_greater_or_equal(threshold, exceeding):
    at = new_app()
    upload(at, "p.zip", make_zip(C_PROJECT))
    analyse(at)
    set_threshold(at, threshold)
    assert metrics(at)["Exceeding threshold"] == str(exceeding)
    assert any(f">= {threshold}" in c.value for c in at.caption)


# ======================================================================= task 5: headers and language selection
AMBIGUOUS_PROJECT = {
    "drv/uart.h": b"static inline int u(int a) { return a ? 1 : 0; }\n", "drv/uart.c": b'#include "uart.h"\nint d(void){return 0;}\n',
    "app/filter.h": b"static inline int f(int a) { return a ? 1 : 0; }\n", "app/filter.cpp": b'#include "filter.h"\nint a(){return 0;}\n',
    "orphan.h": b"static inline int o(int a) { return a ? 1 : 0; }\n",
}


def selection_languages():
    df = tables("data_editor", "Analyze", "File", "Language")[0]
    return dict(zip(df["File"], df["Language"])), df


def test_ambiguous_header_is_labelled_and_follows_the_language_selection():
    at = new_app()
    upload(at, "mixed.zip", make_zip(AMBIGUOUS_PROJECT))
    langs, df = selection_languages()                       # default selection: C and C++
    assert langs == {"drv/uart.h": "C", "drv/uart.c": "C", "app/filter.h": "C++", "app/filter.cpp": "C++",
                     "orphan.h": "C (header, ambiguous)"}
    notes = dict(zip(df["File"], df["Notes"]))
    assert "included only by C++ source files" in notes["app/filter.h"]
    assert "could not be determined" in notes["orphan.h"]

    TABLES.clear()
    at.multiselect(key="src_langs").set_value(["C++"]).run()
    assert not at.exception, [e.value for e in at.exception]
    langs, _ = selection_languages()
    assert langs == {"app/filter.h": "C++", "app/filter.cpp": "C++", "orphan.h": "C++ (header, ambiguous)"}

    TABLES.clear()
    at.multiselect(key="src_langs").set_value(["C"]).run()
    langs, _ = selection_languages()
    assert langs == {"drv/uart.h": "C", "drv/uart.c": "C", "orphan.h": "C (header, ambiguous)"}


def test_analysis_respects_ambiguous_header_language_and_unchecked_rows_are_not_analysed():
    at = new_app()
    upload(at, "mixed.zip", make_zip(AMBIGUOUS_PROJECT))
    TABLES.clear()
    at.multiselect(key="src_langs").set_value(["C++"]).run()
    analyse(at)
    results = function_table()
    assert {(r["File"], r["Language"]) for r in results.to_dict("records")} == {
        ("app/filter.h", "C++"), ("app/filter.cpp", "C++"), ("orphan.h", "C++")}
    skipped = [df for df in tables("dataframe", "Item", "Category", "Reason")][0]
    assert {r["Item"] for r in skipped.to_dict("records") if "Language not selected" in r["Reason"]} == {"drv/uart.c", "drv/uart.h"}


def test_no_candidate_files_for_the_selected_language_shows_a_warning():
    at = new_app()
    upload(at, "c_only.zip", make_zip({"a.c": b"int a(void){return 0;}\n"}))
    TABLES.clear()
    at.multiselect(key="src_langs").set_value(["C++"]).run()
    assert any("No supported source files are available for the selected languages" in w.value for w in at.warning)
    assert at.button(key="src_run_btn").disabled


# ======================================================================= task 5: failed parsing, warnings
def test_failed_file_is_reported_not_hidden_and_other_files_still_analysed(monkeypatch):
    from core.complexity.backend import AppBackend
    real = AppBackend.analyze_file

    def flaky(self, path, *args, **kwargs):
        if "CRASH_ME" in Path(path).read_text(errors="ignore"):
            raise RuntimeError("simulated parser crash")
        return real(self, path, *args, **kwargs)

    monkeypatch.setattr(AppBackend, "analyze_file", flaky)
    at = new_app()
    upload(at, "p.zip", make_zip({"good.c": b"int g(int a){ if (a) return 1; return 0; }\n",
                                  "bad.c": b"/* CRASH_ME */\nint b(void){ return 0; }\n"}))
    analyse(at)
    m = metrics(at)
    assert (m["Files analyzed"], m["Files failed"], m["Functions detected"]) == ("1", "1", "1")
    assert m["Analysis warnings"] == "1"
    assert ccn_by_function(function_table()) == {"g": 2}
    warn_rows = tables("dataframe", "File", "Function", "Type", "Message")[0].to_dict("records")
    failed = [r for r in warn_rows if r["Type"] == "File failed"]
    assert len(failed) == 1 and failed[0]["File"] == "bad.c" and "simulated parser crash" in failed[0]["Message"]
    files = tables("dataframe", "File", "Language", "Functions", "Analysis Status")[0]
    assert dict(zip(files["File"], files["Analysis Status"])) == {"good.c": "Successful", "bad.c": "Failed"}


def test_file_without_functions_is_flagged_and_lambda_and_conditional_warnings_are_visible():
    at = new_app()
    upload(at, "p.zip", make_zip({
        "empty.c": b"/* nothing here */\n",
        "m.cpp": b"int f(int n) {\n    auto g = [](int a) { return a ? 1 : 0; };\n    return g(n);\n}\n",
        "pp.c": b"int h(int x) {\n#ifdef A\n    if (x) return 1;\n#endif\n    return 0;\n}\n"}))
    analyse(at)
    warn_rows = tables("dataframe", "File", "Function", "Type", "Message")[0].to_dict("records")
    text = {(r["File"], r["Type"]): r["Message"] for r in warn_rows}
    assert "No functions" in text[("empty.c", "File warning")]
    assert "lambda" in text[("m.cpp", "Function warning")].lower()
    assert "union of all configurations" in text[("pp.c", "Function warning")]
    assert ccn_by_function(function_table()) == {"f": 1, "f::(lambda at line 2)": 2, "h": 2}


def test_unsupported_and_oversize_uploads_do_not_break_the_page():
    at = new_app()
    upload(at, "p.zip", make_zip({"tool.py": b"def f():\n    return 1\n", "a.c": b"int a(void){return 0;}\n"}))
    assert [f for f in tables("data_editor", "File")[0]["File"]] == ["a.c"]
    assert not at.exception
