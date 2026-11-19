"""Independent oracle for the '&&' classification: GCC itself.

``g++/gcc -fdump-tree-original-raw`` writes the parsed program; a logical AND appears as a
``truth_andif_expr`` node and a reference declarator never does. For each fixture the number of
``&&`` the application counted as logical AND (``logical_and_count``) must equal GCC's number.
The fixtures contain no #include and no constant operands, so nothing is folded away.
Skipped (visibly) when GCC is not installed.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from core.complexity.backend import AppBackend
from tests.helpers import FIXTURES

GXX, GCC = shutil.which("g++"), shutil.which("gcc")
CASES = [  # (fixture, compiler, language flags, cpp mode)
    ("cpp/amp_amp.cpp", GXX, ["-std=c++17"], True),
    ("cpp/refs_templates_ctor.cpp", GXX, ["-std=c++17"], True),
    ("c/amp_amp_c.c", GCC, ["-std=gnu11"], False),
    ("c/control_flow.c", GCC, ["-std=gnu11"], False),
    ("c/constructs.c", GCC, ["-std=gnu11"], False),
]


def gcc_logical_and_total(compiler, flags, source: Path, tmp: Path) -> int:
    subprocess.run([compiler, *flags, "-O0", "-w", "-c", "-fdump-tree-original-raw", "-o", "/dev/null", str(source)],
                   cwd=tmp, check=True, capture_output=True, timeout=120)
    dump = next(tmp.glob("*original*"))
    return sum(line.count("truth_andif_expr") for line in dump.read_text(errors="replace").splitlines())


@pytest.mark.skipif(not (GXX and GCC), reason="GCC not installed: oracle comparison skipped")
@pytest.mark.parametrize("rel,compiler,flags,cpp", CASES)
def test_logical_and_count_matches_gcc(rel, compiler, flags, cpp, tmp_path):
    source = FIXTURES / rel
    expected = gcc_logical_and_total(compiler, flags, source, tmp_path)
    info = AppBackend().analyze_file(str(source), cpp=cpp)
    ours = sum(getattr(f, "logical_and_count", 0) for f in info.function_list)
    assert ours == expected, f"{rel}: application counted {ours} logical '&&', GCC found {expected}"
    assert expected > 0
