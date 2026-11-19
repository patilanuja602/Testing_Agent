"""Architecture, independence and licence-compliance guards for the bundled analysis core.

* The application must run with NO separately installed analysis package and NO network.
* The bundled core must give exactly the results of the original upstream package
  (golden file produced by the upstream package itself).
* The vendored third-party files must not drift from upstream unnoticed, and the notices
  the licences require must stay in the repository.
"""
import ast
import hashlib
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from core.complexity import ComplexityEngine
from core.language_detector import detect_language

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "third_party" / "lizard"
APP_SOURCES = [ROOT / "app.py", ROOT / "config.py",
               *[p for d in ("core", "models", "services", "ui") for p in sorted((ROOT / d).rglob("*.py"))]]
FORBIDDEN_TOP_LEVEL = {"lizard", "lizard_core", "lizard_languages", "lizard_ext", "pygments", "pathspec"}


def _imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


# ------------------------------------------------------------------ independence
def test_application_code_never_imports_an_external_analysis_package():
    offenders = [f"{p.relative_to(ROOT)}: {m}" for p in APP_SOURCES for m in _imported_modules(p)
                 if m.split(".")[0] in FORBIDDEN_TOP_LEVEL]
    assert not offenders, offenders


def test_only_the_complexity_module_touches_third_party():
    offenders = [str(p.relative_to(ROOT)) for p in APP_SOURCES
                 if not str(p.relative_to(ROOT)).startswith("core/complexity/")
                 and any(m.split(".")[0] == "third_party" for m in _imported_modules(p))]
    assert not offenders, offenders


def test_vendored_core_uses_only_the_standard_library():
    stdlib = set(sys.stdlib_module_names)
    for path in VENDOR.rglob("*.py"):
        for module in _imported_modules(path):
            assert module.split(".")[0] in stdlib, f"{path.relative_to(ROOT)} imports non-stdlib {module}"


def test_requirements_do_not_list_the_external_package():
    names = {line.split("#")[0].strip().lower() for line in (ROOT / "requirements.txt").read_text().splitlines()}
    assert not any(n.startswith(("lizard", "pygments", "pathspec")) for n in names)


def test_runs_with_external_package_blocked_and_network_and_subprocesses_forbidden():
    """Fresh interpreter: importing the upstream package fails, any socket use or child
    process raises. The analysis of C and C++ must still work."""
    code = textwrap.dedent(f"""
        import sys, json, socket, subprocess
        sys.path.insert(0, {str(ROOT)!r})
        for name in ("lizard", "lizard_core", "lizard_languages", "lizard_ext", "pygments", "pathspec"):
            sys.modules[name] = None                      # `import <name>` now raises ImportError
        def deny(*a, **k): raise RuntimeError("forbidden: network / child process")
        socket.socket.connect = deny; socket.create_connection = deny; socket.getaddrinfo = deny
        subprocess.Popen = deny
        from pathlib import Path
        from core.complexity import ComplexityEngine
        from core.language_detector import detect_language
        engine = ComplexityEngine()
        fixtures = Path({str(ROOT / "tests" / "fixtures")!r})
        out = {{}}
        for rel in ("c/constructs.c", "cpp/classes.cpp"):
            p = fixtures / rel
            fr, fns = engine.analyze_file(p, rel, detect_language(rel))
            out[rel] = [fr.status.value, len(fns), sum(f.ccn or 0 for f in fns)]
        print(json.dumps(out))
    """)
    proc = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert all(count > 0 for _, count, _ in result.values()), result


# ------------------------------------------------------------------ equivalence with upstream
def _golden():
    return json.loads((ROOT / "tests" / "fixtures" / "golden_upstream.json").read_text(encoding="utf-8"))


def test_golden_file_was_produced_by_the_upstream_release_we_vendored():
    manifest = json.loads((VENDOR / "UPSTREAM_MANIFEST.json").read_text(encoding="utf-8"))
    assert _golden()["upstream_version"] == manifest["upstream"]["version"]


def test_bundled_core_reproduces_original_upstream_results_exactly():
    from third_party.lizard import analyze_file
    attrs = ("name", "long_name", "cyclomatic_complexity", "nloc", "token_count", "parameter_count",
             "parameters", "start_line", "end_line", "top_nesting_level", "length")
    golden = _golden()["files"]
    assert len(golden) >= 9
    total = 0
    for rel, expected in golden.items():
        info = analyze_file(str(ROOT / rel))
        assert (info.nloc, info.token_count) == (expected["nloc"], expected["token_count"]), rel
        got = [{a: (list(getattr(f, a)) if isinstance(getattr(f, a), (list, tuple)) else getattr(f, a))
                for a in attrs} for f in info.function_list]
        assert got == expected["functions"], rel
        total += len(got)
    assert total >= 40


# The application deliberately differs from upstream Lizard 1.24.3 in exactly these documented places
# (core/complexity/reader.py). Anything else that differs is a regression.
DOCUMENTED_DIVERGENCES = {
    # (file, function): (upstream CCN, application CCN, reason)
    ("tests/fixtures/c/macros_ifdef.c", "with_ifdef"): (4, 3, "#ifdef is compile-time, not a decision"),
    ("sample_projects/embedded_demo/src/filter.cpp", "MovingAverage::MovingAverage"):
        (1, 2, "the '?' in the member-initialiser list is executed by the constructor; upstream drops it"),
}
DOCUMENTED_TOKEN_DIVERGENCES = {   # tokens of a lambda body belong to the lambda entry, not the enclosing function
    ("tests/fixtures/cpp/templates_lambdas.cpp", "count_positive"): (60, 54),
}
DOCUMENTED_EXTRA_FUNCTIONS = {   # lambda bodies are reported as their own entries
    ("tests/fixtures/cpp/templates_lambdas.cpp", "count_positive::(lambda at line 15)"),
}


def test_adapter_output_agrees_with_golden_ccn_for_every_function():
    """Same check one level up: what the application actually reports. Differences from the
    upstream golden file must be exactly the documented, reasoned divergences."""
    engine = ComplexityEngine()
    checked = 0
    seen_div, seen_extra = set(), set()
    for rel, expected in _golden()["files"].items():
        if detect_language(rel) is None:          # e.g. the Python fixtures: bundled core only, not offered by the app
            continue
        checked += 1
        _, funcs = engine.analyze_file(ROOT / rel, rel, detect_language(rel))
        got = []
        for f in funcs:
            if (rel, f.function) in DOCUMENTED_EXTRA_FUNCTIONS:
                seen_extra.add((rel, f.function))
                continue
            got.append((f.function, f.start_line, f.end_line, f.ccn, f.nloc, f.token_count, f.parameters))
        want = []
        for e in expected["functions"]:
            row = (e["name"], e["start_line"], e["end_line"], e["cyclomatic_complexity"], e["nloc"],
                   e["token_count"], e["parameter_count"])
            div = DOCUMENTED_DIVERGENCES.get((rel, e["name"]))
            if div:
                assert row[3] == div[0], f"golden value changed for {rel}:{e['name']}"
                row = row[:3] + (div[1],) + row[4:]
                seen_div.add((rel, e["name"]))
            tok = DOCUMENTED_TOKEN_DIVERGENCES.get((rel, e["name"]))
            if tok:
                assert row[5] == tok[0], f"golden token count changed for {rel}:{e['name']}"
                row = row[:5] + (tok[1],) + row[6:]
            want.append(row)
        assert got == want, rel
    assert checked >= 6
    assert seen_div == set(DOCUMENTED_DIVERGENCES) and seen_extra == DOCUMENTED_EXTRA_FUNCTIONS


# ------------------------------------------------------------------ licence / provenance guards
def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_vendored_files_match_manifest_and_unmodified_files_equal_upstream():
    manifest = json.loads((VENDOR / "UPSTREAM_MANIFEST.json").read_text(encoding="utf-8"))
    listed = set(manifest["files"])
    on_disk = {p.relative_to(VENDOR).as_posix() for p in VENDOR.rglob("*.py")} | {"LICENSE.txt"}
    assert listed == on_disk, f"unlisted/missing vendored files: {sorted(listed ^ on_disk)}"
    for rel, info in manifest["files"].items():
        digest = _sha(VENDOR / rel)
        if info["status"] == "unmodified":
            assert digest == info["upstream_sha256"], f"{rel} differs from upstream but is not declared modified"
        else:
            assert digest == info["sha256"], (f"{rel} changed since it was reviewed: update MODIFICATIONS.md and run "
                                              f"scripts/update_vendor_manifest.py")


def test_modified_upstream_files_carry_a_prominent_change_notice():
    manifest = json.loads((VENDOR / "UPSTREAM_MANIFEST.json").read_text(encoding="utf-8"))
    for rel, info in manifest["files"].items():
        if info["status"] == "modified":
            head = "\n".join((VENDOR / rel).read_text(encoding="utf-8").splitlines()[:6])
            assert "MODIFIED from the upstream Lizard" in head, rel


def test_required_notices_and_licence_texts_are_present():
    mit = (VENDOR / "LICENSE.txt").read_text(encoding="utf-8")
    assert "Copyright Terry Yin and other contributors" in mit and "Permission is hereby granted" in mit
    apache = (VENDOR / "LICENSE-Apache-2.0.txt").read_text(encoding="utf-8")
    assert "Apache License" in apache and "Version 2.0, January 2004" in apache
    for name in ("README.md", "MODIFICATIONS.md"):
        assert (VENDOR / name).is_file(), name
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    for needle in ("Lizard", "Terry Yin", "MIT", "Apache", "1.24.3", "Permission is hereby granted"):
        assert needle in notices, needle
    assert "Lizard" in (ROOT / "LICENSES.md").read_text(encoding="utf-8")


def test_reader_selection_is_unchanged_for_every_supported_extension():
    """The trimmed language registry must still pick the same reader family as upstream did
    (.hxx has no upstream reader and falls back to the C/C++ reader). The Python reader stays
    bundled but dormant, so Python can be enabled later without touching third-party code."""
    from third_party.lizard.lizard_languages import CLikeReader, PythonReader, get_reader_for
    from core.language_detector import EXTENSION_MAP
    for ext in EXTENSION_MAP:
        assert (get_reader_for(f"x{ext}") or CLikeReader) is CLikeReader, ext
    assert detect_language("a.hxx") is not None
    assert get_reader_for("x.py") is PythonReader
