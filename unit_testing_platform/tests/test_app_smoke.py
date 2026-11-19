"""Starts the Streamlit script headlessly (requires streamlit; skipped otherwise) and drives the real UI."""
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
APP = str(ROOT / "app.py")
SAMPLE_ZIP = ROOT / "sample_projects" / "embedded_demo.zip"
SAMPLE_REPORT = ROOT / "sample_reports" / "sample_complexity_report.xlsx"
PAGES = ["Complexity Analysis", "Excel Report Analysis"]


def new_app():
    testing = pytest.importorskip("streamlit.testing.v1")
    return testing.AppTest.from_file(APP, default_timeout=60).run()


def metrics(at):
    return {m.label: m.value for m in at.metric}


def set_threshold(at, value):
    at.sidebar.number_input(key="threshold").set_value(value).run()
    assert not at.exception, [e.value for e in at.exception]


def run_zip_analysis():
    at = new_app()
    at.file_uploader(key="src_uploader").upload("embedded_demo.zip", SAMPLE_ZIP.read_bytes(), "application/zip")
    at.run()
    at.button(key="src_run_btn").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


# ------------------------------------------------------------------ navigation and layout
def test_app_starts_without_exceptions():
    at = new_app()
    assert not at.exception, [e.value for e in at.exception]


def test_navigation_has_exactly_two_pages_and_no_settings():
    at = new_app()
    assert list(at.sidebar.radio(key="nav").options) == PAGES
    for page in PAGES:
        at.sidebar.radio(key="nav").set_value(page).run()
        assert not at.exception, [e.value for e in at.exception]
        text = " ".join(m.value for m in at.markdown) + " ".join(h.value for h in at.header)
        assert "Settings" not in text


def test_main_page_headings_and_labels():
    at = new_app()
    assert [t.value for t in at.title] == ["Unit Testing Platform"]
    assert any(c.value == "Phase 1 · Cyclomatic Complexity Analysis" for c in at.caption)
    assert [h.value for h in at.header] == ["Complexity Analysis"]
    assert at.text_input(key="src_project").label == "Project Name"
    langs = at.multiselect(key="src_langs")
    assert langs.label == "Languages to Analyse" and langs.options == ["C", "C++"] and langs.value == ["C", "C++"]
    assert at.get("file_uploader")[0].proto.label == "Source Files or ZIP Project"
    assert "py" not in at.get("file_uploader")[0].proto.type


# ------------------------------------------------------------------ the single threshold input
def test_sidebar_has_one_threshold_input_default_one_and_nothing_else():
    at = new_app()
    inputs = at.sidebar.number_input
    assert len(inputs) == 1 and len(at.sidebar.radio) == 1             # the number input and the navigation only
    box = at.sidebar.number_input(key="threshold")
    assert box.label == "Enter Complexity Threshold" and box.value == 1 and box.min == 1
    assert [s.value for s in at.sidebar.subheader] == ["Complexity Threshold"]
    assert not at.sidebar.selectbox and not at.sidebar.text_input and not at.sidebar.info


# ------------------------------------------------------------------ workflows
def test_zip_upload_default_threshold_flags_every_function():
    at = run_zip_analysis()
    m = metrics(at)
    assert (m["Files analyzed"], m["Files failed"], m["Functions detected"]) == ("2", "0", "6")
    assert (m["Exceeding threshold"], m["Within threshold"]) == ("6", "0")      # complexity >= 1 for all
    assert m["Files skipped"] == "1"                                           # README.txt


# uart_parse_frame, uart_send, push, clamp, uart_init, MovingAverage ctor (1 + the '?' in its member-initialiser list)
SAMPLE_COMPLEXITIES = [10, 8, 3, 3, 2, 2]


@pytest.mark.parametrize("threshold", [1, 2, 3, 4, 8, 9, 10, 11])
def test_dashboard_flags_values_equal_to_or_above_the_threshold(threshold):
    at = run_zip_analysis()
    set_threshold(at, threshold)
    expected = sum(c >= threshold for c in SAMPLE_COMPLEXITIES)
    m = metrics(at)
    assert m["Exceeding threshold"] == str(expected)
    assert m["Within threshold"] == str(len(SAMPLE_COMPLEXITIES) - expected)


def test_python_file_in_a_zip_is_reported_as_unsupported():
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.c", "int f(int a){ if (a) { return 1; } return 0; }\n")
        zf.writestr("tool.py", "def f():\n    return 1\n")
    at = new_app()
    at.file_uploader(key="src_uploader").upload("p.zip", buf.getvalue(), "application/zip")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    summary = next(m.value for m in at.markdown if m.value.startswith("Received"))
    assert "**1** supported" in summary and "**1** skipped" in summary, summary


def test_excel_import_uses_the_same_threshold_rule():
    # sample report complexities (V(G)) after removing the Python rows: 2, 8, 14, 2, 4, 3, 21, 10, 1, 12
    values = [2, 8, 14, 2, 4, 3, 21, 10, 1, 12]
    at = new_app()
    at.sidebar.radio(key="nav").set_value("Excel Report Analysis").run()
    at.file_uploader(key="xl_uploader").upload("sample_complexity_report.xlsx", SAMPLE_REPORT.read_bytes(),
                                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert not [b for b in at.button if "threshold" in (b.label or "").lower()]       # no 'use report threshold' mode
    next(b for b in at.button if b.label == "Import Report").click().run()
    assert not at.exception, [e.value for e in at.exception]
    for threshold in (1, 4, 10, 12, 21, 22):
        set_threshold(at, threshold)
        expected = sum(v >= threshold for v in values)
        assert metrics(at)["Exceeding threshold"] == str(expected), threshold
        assert metrics(at)["Functions imported"] == str(len(values))


def test_python_is_not_mentioned_or_offered_anywhere_in_the_ui():
    at = new_app()
    for page in PAGES:
        at.sidebar.radio(key="nav").set_value(page).run()
        texts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [h.value for h in at.header]
        texts += [u.proto.label + " " + u.proto.help + " " + " ".join(u.proto.type) for u in at.get("file_uploader")]
        texts += [o for ms in at.multiselect for o in ms.options]
        assert not [t for t in texts if "python" in t.lower() or ".py" in t.lower()], (page, texts)
