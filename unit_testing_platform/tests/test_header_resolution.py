"""Ambiguous .h files: resolved from the project, never silently assumed to be C."""
import pytest

from core.complexity import ComplexityEngine
from models.analysis_result import Language
from services.project_processor import run_source_analysis
from services.source_upload import UploadedItem, stage_uploads
from tests.helpers import SMALL_LIMITS, make_zip

C_HDR = b"#ifndef X_H\n#define X_H\nstatic inline int sq(int a) { return a * a; }\n#endif\n"
CPP_HDR = b"template <typename T>\nT biggest(T a, T b) { return a > b ? a : b; }\n"
ONLY_CPP_SYNTAX_HDR = b"static inline int twice(int a) { return a ? a + a : 0; }\n"   # valid C and C++


def staged(entries):
    return stage_uploads([UploadedItem("p.zip", make_zip(entries))], SMALL_LIMITS)


def info(project, name):
    return next(f for f in project.files if f.display_path == name)


def test_header_with_cpp_constructs_is_cpp_and_survives_cpp_only_selection():
    project = staged({"h.h": CPP_HDR, "m.cpp": b"int main(){return 0;}\n"})
    try:
        h = info(project, "h.h")
        assert h.language is Language.CPP and not h.header_ambiguous and "C++ constructs" in h.language_basis
        run = run_source_analysis(project, project_name="P", selected_paths={"h.h"},
                                  selected_languages=[Language.CPP])
        assert [f.function for f in run.functions] == ["biggest"] and run.functions[0].language == "C++"
    finally:
        project.cleanup()


def test_header_included_only_by_cpp_sources_is_cpp():
    project = staged({"inc/util.h": ONLY_CPP_SYNTAX_HDR, "a.cpp": b'#include "inc/util.h"\nint a(){return 0;}\n'})
    try:
        h = info(project, "inc/util.h")
        assert h.language is Language.CPP and not h.header_ambiguous and "only by C++" in h.language_basis
    finally:
        project.cleanup()


def test_header_included_only_by_c_sources_is_c_and_excluded_from_cpp_only_run():
    project = staged({"util.h": C_HDR, "a.c": b'#include "util.h"\nint a(void){return 0;}\n'})
    try:
        h = info(project, "util.h")
        assert h.language is Language.C and not h.header_ambiguous
        run = run_source_analysis(project, project_name="P", selected_paths={"util.h"},
                                  selected_languages=[Language.CPP])
        assert not run.functions
        assert any(s.path == "util.h" and "resolved as C" in s.reason for s in run.skipped)
    finally:
        project.cleanup()


def test_inclusion_is_followed_through_other_headers():
    project = staged({"leaf.h": ONLY_CPP_SYNTAX_HDR, "mid.h": b'#include "leaf.h"\n', "a.cpp": b'#include "mid.h"\nint a(){return 0;}\n'})
    try:
        assert info(project, "leaf.h").language is Language.CPP
    finally:
        project.cleanup()


def test_header_included_from_both_languages_is_ambiguous():
    project = staged({"u.h": ONLY_CPP_SYNTAX_HDR, "a.c": b'#include "u.h"\nint a(void){return 0;}\n',
                      "b.cpp": b'#include "u.h"\nint b(){return 0;}\n'})
    try:
        h = info(project, "u.h")
        assert h.header_ambiguous and "both C and C++" in h.language_basis
    finally:
        project.cleanup()


@pytest.mark.parametrize("selected,expected_language", [
    ([Language.CPP], "C++"), ([Language.C], "C"), ([Language.C, Language.CPP], "C"),
])
def test_ambiguous_header_follows_the_users_language_selection(selected, expected_language):
    project = staged({"u.h": ONLY_CPP_SYNTAX_HDR})
    try:
        h = info(project, "u.h")
        assert h.header_ambiguous and h.is_selectable(selected)
        run = run_source_analysis(project, project_name="P", selected_paths={"u.h"}, selected_languages=selected)
        assert [(f.function, f.ccn, f.language) for f in run.functions] == [("twice", 2, expected_language)]
        assert any("could not be determined" in w for w in run.file_results[0].warnings)   # stated, not hidden
    finally:
        project.cleanup()


def test_extern_c_guard_is_not_evidence_of_cpp():
    guarded = b'#ifdef __cplusplus\nextern "C" {\n#endif\nint f(int a);\n#ifdef __cplusplus\n}\n#endif\n'
    project = staged({"g.h": guarded, "a.c": b'#include "g.h"\nint a(void){return 0;}\n'})
    try:
        assert info(project, "g.h").language is Language.C
    finally:
        project.cleanup()


def test_cpp_header_analysed_as_cpp_gets_reference_and_lambda_rules():
    src = b"template <typename T>\ninline int f(T&& v)\n{\n    auto l = [](int x) { return x ? 1 : 0; };\n    return l(1);\n}\n"
    project = staged({"t.h": src})
    try:
        run = run_source_analysis(project, project_name="P", selected_paths={"t.h"}, selected_languages=[Language.CPP])
        assert [(f.function, f.ccn) for f in run.functions] == [("f", 1), ("f::(lambda at line 4)", 2)]
    finally:
        project.cleanup()


# ---------------------------------------------------------------------------------- thorough cases
PLAIN = b"static inline int twice(int a) { return a ? a + a : 0; }\n"        # valid C and valid C++
CSRC = b'#include "%s"\nint m(void) { return 0; }\n'
CPPSRC = b'#include "%s"\nint m() { return 0; }\n'


def resolved(entries):
    project = staged(entries)
    try:
        return {f.display_path: (f.language, f.header_ambiguous) for f in project.files if f.disk_path.suffix == ".h"}
    finally:
        project.cleanup()


C, CPP = Language.C, Language.CPP


def test_duplicate_header_names_are_told_apart_by_the_including_directory():
    got = resolved({"a/x.h": PLAIN, "b/x.h": PLAIN, "a/m.c": CSRC % b"x.h", "b/m.cpp": CPPSRC % b"x.h"})
    assert got == {"a/x.h": (C, False), "b/x.h": (CPP, False)}


def test_duplicate_names_with_relative_parent_includes():
    got = resolved({"c/inc/x.h": PLAIN, "cpp/inc/x.h": PLAIN,
                    "c/src/m.c": CSRC % b"../inc/x.h", "cpp/src/m.cpp": CPPSRC % b"../inc/x.h"})
    assert got == {"c/inc/x.h": (C, False), "cpp/inc/x.h": (CPP, False)}


@pytest.mark.parametrize("include", [b"./x.h", b"x.h", b"sub/../x.h"])
def test_relative_include_spellings_resolve_to_the_same_header(include):
    assert resolved({"x.h": PLAIN, "m.cpp": CPPSRC % include}) == {"x.h": (CPP, False)}


@pytest.mark.parametrize("entries,header", [
    ({"inc/sub/x.h": PLAIN, "m.cpp": CPPSRC % b"sub/x.h"}, "inc/sub/x.h"),            # include dir not known: suffix match
    ({"inc/sub/x.h": PLAIN, "m.cpp": b"#include <sub/x.h>\nint m(){return 0;}\n"}, "inc/sub/x.h"),   # angle form
    ({".cfg/x.h": PLAIN, "m.cpp": CPPSRC % b".cfg/x.h"}, ".cfg/x.h"),                  # dot-directory (regression)
    ({"Inc/X.h": PLAIN, "m.cpp": CPPSRC % b"inc\\x.h"}, "Inc/X.h"),                    # case and backslash
    ({"deep/a/b/c/x.h": PLAIN, "deep/a/m.cpp": CPPSRC % b"b/c/x.h"}, "deep/a/b/c/x.h"),
])
def test_nested_include_directories(entries, header):
    assert resolved(entries)[header] == (CPP, False)


def test_unresolvable_suffix_matches_stay_conservative_when_names_collide():
    # '#include <x.h>' with two staged x.h and no way to know which include directory is meant:
    # both are linked, so evidence stays (conservatively) attached to both.
    got = resolved({"i1/x.h": PLAIN, "i2/x.h": PLAIN, "m.cpp": b"#include <x.h>\nint m(){return 0;}\n"})
    assert got == {"i1/x.h": (CPP, False), "i2/x.h": (CPP, False)}


def test_system_headers_and_missing_files_are_ignored():
    got = resolved({"x.h": PLAIN, "m.cpp": b'#include <stdio.h>\n#include "missing.h"\nint m(){return 0;}\n'})
    assert got == {"x.h": (C, True)}          # nothing includes it: ambiguous


def test_transitive_includes_across_directories():
    got = resolved({"inc/leaf.h": PLAIN, "inc/mid.h": b'#include "leaf.h"\n', "src/m.cpp": CPPSRC % b"../inc/mid.h"})
    assert got == {"inc/leaf.h": (CPP, False), "inc/mid.h": (CPP, False)}


def test_transitive_includes_from_both_languages_make_the_shared_leaf_ambiguous_but_not_the_others():
    got = resolved({"leaf.h": PLAIN, "only_c.h": b'#include "leaf.h"\n' + PLAIN, "only_cpp.h": b'#include "leaf.h"\n' + PLAIN,
                    "a.c": CSRC % b"only_c.h", "b.cpp": CPPSRC % b"only_cpp.h"})
    assert got == {"leaf.h": (C, True), "only_c.h": (C, False), "only_cpp.h": (CPP, False)}


def test_include_cycles_terminate():
    got = resolved({"a.h": b'#include "b.h"\n' + PLAIN, "b.h": b'#include "a.h"\n' + PLAIN, "m.cpp": CPPSRC % b"a.h"})
    assert got == {"a.h": (CPP, False), "b.h": (CPP, False)}


def test_cpp_content_wins_over_inclusion_by_a_c_file():
    got = resolved({"t.h": b"template <typename T> T id(T v) { return v; }\n", "m.c": CSRC % b"t.h"})
    assert got == {"t.h": (CPP, False)}


def test_mixed_project_each_header_gets_its_own_answer():
    got = resolved({
        "drv/uart.h": PLAIN, "drv/uart.c": CSRC % b"uart.h",                         # C only
        "app/filter.h": PLAIN, "app/filter.cpp": CPPSRC % b"filter.h",               # C++ only
        "common/types.h": PLAIN, "drv/d.c": CSRC % b"../common/types.h", "app/a.cpp": CPPSRC % b"../common/types.h",  # shared
        "orphan/o.h": PLAIN,                                                         # nobody includes it
        "app/cls.h": b"class A { public: int f() const { return 1; } };\n",          # content
    })
    assert got == {"drv/uart.h": (C, False), "app/filter.h": (CPP, False), "common/types.h": (C, True),
                   "orphan/o.h": (C, True), "app/cls.h": (CPP, False)}


def test_loose_files_uploaded_together_are_resolved_like_a_zip():
    project = stage_uploads([UploadedItem("x.h", PLAIN), UploadedItem("m.cpp", CPPSRC % b"x.h")], SMALL_LIMITS)
    try:
        h = info(project, "x.h")
        assert (h.language, h.header_ambiguous) == (CPP, False)
    finally:
        project.cleanup()


def test_header_selection_in_a_mixed_project_under_each_language_selection():
    entries = {"drv/uart.h": PLAIN, "drv/uart.c": CSRC % b"uart.h", "app/filter.h": PLAIN,
               "app/filter.cpp": CPPSRC % b"filter.h", "orphan.h": PLAIN}
    expectations = {   # selection -> headers analysed
        (Language.C,): {"drv/uart.h", "orphan.h"},
        (Language.CPP,): {"app/filter.h", "orphan.h"},
        (Language.C, Language.CPP): {"drv/uart.h", "app/filter.h", "orphan.h"},
    }
    for selection, headers in expectations.items():
        project = staged(entries)
        try:
            run = run_source_analysis(project, project_name="P", selected_paths={f.display_path for f in project.files},
                                      selected_languages=list(selection))
            analysed = {f.file for f in run.functions if f.file.endswith(".h")}
            assert analysed == headers, (selection, analysed)
        finally:
            project.cleanup()
