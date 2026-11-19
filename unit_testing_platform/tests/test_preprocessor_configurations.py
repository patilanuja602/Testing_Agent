"""How the analysis of ALL conditional branches together compares with one compiled configuration.

The reference for a configuration is the same fixture run through GCC's preprocessor
(``gcc -E -P -D...``: macros expanded, inactive branches removed) and then analysed. The expected
numbers are hand-derived (documented in ``docs/PREPROCESSOR_LIMITATIONS.md``); they are not taken
from the analyzer's own output. Skipped (visibly) when gcc is not installed.
"""
import shutil
import subprocess

import pytest

from core.complexity import ComplexityEngine
from models.analysis_result import Language
from tests.helpers import FIXTURES

GCC = shutil.which("gcc")
SOURCE = FIXTURES / "c" / "config_variants.c"

# function -> (union of all branches, {configuration: complexity of the code that configuration compiles})
EXPECTED = {
    "mode_select": (4, {"none": 2, "MODE_FAST": 3}),       # A: union adds the decisions of every alternative
    "feature":     (2, {"none": 1, "FEATURE_X": 2}),       # B: union equals the richest configuration
    "use_clamp":   (1, {"none": 3, "MODE_FAST": 3}),       # C: macro-body decisions: union UNDER-reports
    "checked":     (1, {"none": 1, "SAFE": 2}),            # D: config-dependent macro: union under-reports
    "dead_code":   (1, {"none": 1, "MODE_FAST": 1}),       # F: constant-false code is excluded: exact
}
CONFIGS = {"none": [], "MODE_FAST": ["-DMODE_FAST"], "FEATURE_X": ["-DFEATURE_X"], "SAFE": ["-DSAFE"],
           "USE_A": ["-DUSE_A"], "all": ["-DMODE_FAST", "-DFEATURE_X", "-DSAFE", "-DUSE_A"]}


def rows(path):
    _, funcs = ComplexityEngine().analyze_file(path, path.name, Language.C)
    return [(f.function, f.ccn) for f in funcs]


def configuration_rows(tmp_path, defines):
    out = subprocess.run([GCC, "-E", "-P", *defines, str(SOURCE)], capture_output=True, text=True, check=True).stdout
    path = tmp_path / "preprocessed.c"
    path.write_text(out)
    return dict(rows(path))


def test_union_analysis_of_the_fixture():
    got = rows(SOURCE)
    assert [(n, c) for n, c in got if n != "pick"] == [(n, EXPECTED[n][0]) for n in
                                                       ("mode_select", "feature", "use_clamp", "checked", "dead_code")]
    # E: both alternative definitions are reported although exactly one is ever compiled.
    assert [c for n, c in got if n == "pick"] == [2, 2]


@pytest.mark.skipif(not GCC, reason="gcc not installed: per-configuration comparison skipped")
@pytest.mark.parametrize("function", sorted(EXPECTED))
def test_each_configuration_matches_the_hand_derived_value(tmp_path, function):
    union, per_config = EXPECTED[function]
    cache = {name: configuration_rows(tmp_path, CONFIGS[name]) for name in per_config}
    for name, ccn in per_config.items():
        assert cache[name][function] == ccn, (function, name)


@pytest.mark.skipif(not GCC, reason="gcc not installed: per-configuration comparison skipped")
def test_union_is_not_a_bound_in_either_direction(tmp_path):
    """A: union above a configuration. C/D: union below it (macro expansion). Hence 'not a per-configuration figure'."""
    union = dict(rows(SOURCE))
    none, fast = configuration_rows(tmp_path, []), configuration_rows(tmp_path, CONFIGS["MODE_FAST"])
    assert union["mode_select"] > max(none["mode_select"], fast["mode_select"])
    assert union["use_clamp"] < none["use_clamp"]
    assert union["checked"] < configuration_rows(tmp_path, CONFIGS["SAFE"])["checked"]
    assert len([1 for _ in rows(SOURCE) if _[0] == "pick"]) == 2 and \
        [n for n, _ in configuration_rows(tmp_path, []).items()].count("pick") == 1
