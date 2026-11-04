"""Two groups (both always run; the analysis core is part of this repository):

1. ADAPTER tests: use an injected fake backend to verify how OUR adapter maps
   analysis-core objects. They say nothing about the core's correctness.
2. REAL core tests: verify function detection, names, line numbers and complexity
   of the bundled core against hand-derived expectations in fixtures/expected.json.

The Python fixtures are kept on purpose: Python is not enabled in the application in this
release, but the core's Python support must keep working so it can be enabled later.
"""
import sys
from types import SimpleNamespace

import pytest

from core.complexity import ENGINE_NAME, ComplexityEngine
from models.analysis_result import AnalysisStatus, Language
from tests.helpers import FIXTURES, load_manifest, marker_lines


# ------------------------------------------------------------------ adapter tests
class FakeBackend:
    def __init__(self, functions=None, raise_for=None):
        self.functions, self.raise_for = functions or [], raise_for

    def analyze_file(self, path):
        if self.raise_for and self.raise_for in path:
            raise RuntimeError(f"cannot parse {path}")
        return SimpleNamespace(function_list=self.functions)


def lf(name="f", ccn=3, start=1, end=4, **kw):
    return SimpleNamespace(name=name, long_name=f"{name}( )", cyclomatic_complexity=ccn, start_line=start,
                           end_line=end, nloc=kw.get("nloc", 3), parameter_count=kw.get("params", 0),
                           token_count=kw.get("tokens", 10))


def test_adapter_maps_all_fields(tmp_path):
    src = tmp_path / "a.c"; src.write_text("int f(void) {\n  return 0;\n}\n")
    engine = ComplexityEngine(FakeBackend([lf("f", 7, 1, 3, nloc=3, params=1, tokens=9)]))
    fr, funcs = engine.analyze_file(src, "dir/a.c", Language.C)
    f = funcs[0]
    assert (f.file, f.function, f.ccn, f.start_line, f.end_line, f.nloc, f.parameters, f.token_count) == \
           ("dir/a.c", "f", 7, 1, 3, 3, 1, 9)
    assert f.language == "C" and f.engine == ENGINE_NAME and f.analysis_status is AnalysisStatus.SUCCESS
    assert fr.status is AnalysisStatus.SUCCESS and fr.function_count == 1


def test_adapter_does_not_invent_missing_metrics(tmp_path):
    src = tmp_path / "a.c"; src.write_text("int f(void){return 0;}\n")
    bare = SimpleNamespace(name="f", cyclomatic_complexity=2)          # nothing else available
    _, funcs = ComplexityEngine(FakeBackend([bare])).analyze_file(src, "a.c", Language.C)
    f = funcs[0]
    assert f.ccn == 2 and f.start_line is None and f.end_line is None and f.nloc is None
    assert f.parameters is None and f.token_count is None


def test_adapter_flags_missing_complexity(tmp_path):
    src = tmp_path / "a.c"; src.write_text("int f(void){return 0;}\n")
    _, funcs = ComplexityEngine(FakeBackend([lf(ccn=None)])).analyze_file(src, "a.c", Language.C)
    assert funcs[0].ccn is None and funcs[0].analysis_status is AnalysisStatus.WARNING


def test_adapter_file_failure_is_reported_not_hidden(tmp_path):
    src = tmp_path / "boom.c"; src.write_text("int f(void){return 0;}\n")
    fr, funcs = ComplexityEngine(FakeBackend(raise_for="boom")).analyze_file(src, "proj/boom.c", Language.C)
    assert fr.status is AnalysisStatus.FAILED and funcs == []
    assert "RuntimeError" in fr.error and str(tmp_path) not in fr.error     # no internal path leaked


def test_adapter_warns_when_nothing_detected(tmp_path):
    src = tmp_path / "decl.c"; src.write_text("int f(void);\nextern int x;\n")
    fr, funcs = ComplexityEngine(FakeBackend([])).analyze_file(src, "decl.c", Language.C)
    assert funcs == [] and fr.status is AnalysisStatus.WARNING and fr.warnings


def test_adapter_attaches_risk_warnings_only_to_affected_functions(tmp_path):
    src = tmp_path / "m.c"
    src.write_text("#define SQ(x) ((x)*(x))\nint a(void){return 0;}\n"
                   "int b(int x){\n#ifdef Z\n if(x){return 1;}\n#endif\n return 0;}\n")
    funcs = ComplexityEngine(FakeBackend([lf("a", 1, 2, 2), lf("b", 2, 3, 7)])).analyze_file(src, "m.c", Language.C)[1]
    a, b = funcs
    assert any("macros" in w for w in a.warnings) and not any("Conditional" in w for w in a.warnings)
    assert any("Conditional" in w for w in b.warnings) and b.analysis_status is AnalysisStatus.WARNING


def test_comments_and_strings_do_not_trigger_warnings(tmp_path):
    src = tmp_path / "c.cpp"
    src.write_text('// template <typename T> and #if in a comment\nconst char* s = "template <int>";\n'
                   "int a(void){return 0;}\n")
    funcs = ComplexityEngine(FakeBackend([lf("a", 1, 3, 3)])).analyze_file(src, "c.cpp", Language.CPP)[1]
    assert funcs[0].warnings == []


# ------------------------------------------------------------------ real core tests
@pytest.fixture
def real_engine():
    return ComplexityEngine()


def test_engine_identity_and_core_version(real_engine):
    assert real_engine.name == ENGINE_NAME
    assert real_engine.version == "1.0.0 (core 1.24.3)"


def _expected_cases():
    cases = []
    for entry in load_manifest()["files"]:
        for fx in entry["functions"]:
            cases.append((entry, fx))
    return cases


def _analyze(engine, entry):
    path = FIXTURES / entry["file"]
    return path, *engine.analyze_file(path, entry["file"], Language(entry["language"]))


def test_real_detects_every_fixture_function_with_names_and_lines(real_engine):
    for entry in load_manifest()["files"]:
        if tuple(entry.get("min_python", (0, 0))) > sys.version_info[:2]:
            continue
        path, file_result, funcs = _analyze(real_engine, entry)
        markers = marker_lines(path)
        assert file_result.status is not AnalysisStatus.FAILED, entry["file"]
        found = {}
        for f in funcs:
            found.setdefault((f.function.split("::")[-1], f.start_line), f)
        for fx in entry["functions"]:
            start, end = markers[fx["id"]]
            hit = found.get((fx["name"], start))
            assert hit is not None, f"{entry['file']}: {fx['id']} not detected at line {start}; got {sorted(found)}"
            assert hit.file == entry["file"]
            assert hit.end_line == end, f"{fx['id']}: end line {hit.end_line} != {end}"


def test_real_complexity_matches_hand_derived_values(real_engine):
    mismatches = []
    for entry in load_manifest()["files"]:
        if tuple(entry.get("min_python", (0, 0))) > sys.version_info[:2]:
            continue
        path, _, funcs = _analyze(real_engine, entry)
        markers = marker_lines(path)
        by_start = {f.start_line: f for f in funcs}
        for fx in entry["functions"]:
            if not fx["strict"]:
                continue
            f = by_start.get(markers[fx["id"]][0])
            if f is None or f.ccn != fx["ccn"]:
                mismatches.append((entry["file"], fx["id"], fx["ccn"], None if f is None else f.ccn))
    assert not mismatches, f"CCN differs from hand-derived expectation (investigate fixture OR convention): {mismatches}"


def test_real_parameter_counts(real_engine):
    entry = next(e for e in load_manifest()["files"] if e["file"] == "c/constructs.c")
    path, _, funcs = _analyze(real_engine, entry)
    markers = marker_lines(path)
    by_start = {f.start_line: f for f in funcs}
    for fx in entry["functions"]:
        assert by_start[markers[fx["id"]][0]].parameters == fx["params"], fx["id"]


def test_real_limitation_warnings_are_visible(real_engine):
    for entry in load_manifest()["files"]:
        if tuple(entry.get("min_python", (0, 0))) > sys.version_info[:2]:
            continue
        path, file_result, funcs = _analyze(real_engine, entry)
        markers = marker_lines(path)
        by_start = {f.start_line: f for f in funcs}
        for fx in entry["functions"]:
            keyword = fx.get("expect_warning")
            if not keyword:
                continue
            f = by_start.get(markers[fx["id"]][0])
            assert f is not None, fx["id"]
            assert any(keyword.lower() in w.lower() for w in f.warnings), (fx["id"], f.warnings)
            assert f.analysis_status is AnalysisStatus.WARNING
