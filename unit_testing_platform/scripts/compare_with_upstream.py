"""DEVELOPER TOOL (not used by the application): prove that the bundled analysis core
(third_party/lizard) still gives exactly the same results as the original upstream
package it was taken from.

The application itself never imports the upstream package. This script does, so run it
in a throw-away virtual environment:

    python3 -m venv /tmp/cmp-venv && /tmp/cmp-venv/bin/pip install lizard==1.24.3
    /tmp/cmp-venv/bin/python scripts/compare_with_upstream.py [DIR_OR_FILE ...]

With no arguments it compares every C/C++/Python file under tests/fixtures and
sample_projects. Exit code 0 = identical, 1 = differences (listed), 2 = upstream missing.

    /tmp/cmp-venv/bin/python scripts/compare_with_upstream.py --write-golden tests/fixtures/golden_upstream.json

(--write-golden records the ORIGINAL upstream package's results for tests/fixtures and
sample_projects; tests/test_complexity_integration.py compares the bundled core with it.)

Compared per file: file-level nloc / token count / function count, and for every function
all of: name, long_name, cyclomatic_complexity, nloc, token_count, parameter_count,
parameters, start_line, end_line, top_nesting_level, length. Each file is also analysed
under every supported extension spelling to check that reader selection is unchanged.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EXTS = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".py"}
FUNC_ATTRS = ("name", "long_name", "cyclomatic_complexity", "nloc", "token_count", "parameter_count",
              "parameters", "start_line", "end_line", "top_nesting_level", "length")


def load_upstream():
    # Imported by name at run time on purpose: this is the only place that may do so.
    try:
        return importlib.import_module("lizard")
    except ImportError:
        print("Upstream 'lizard' is not installed in this interpreter (see the usage text).", file=sys.stderr)
        raise SystemExit(2)


def snapshot(info):
    return {
        "nloc": getattr(info, "nloc", None),
        "token_count": getattr(info, "token_count", None),
        "functions": [tuple(_norm(getattr(f, a, "<missing>")) for a in FUNC_ATTRS) for f in info.function_list],
    }


def _norm(v):
    return list(v) if isinstance(v, (list, tuple)) else v


def files_under(targets):
    for t in targets:
        t = Path(t)
        if t.is_file():
            yield t
        else:
            yield from (p for p in sorted(t.rglob("*")) if p.is_file() and p.suffix.lower() in EXTS)


def write_golden(upstream, out: Path) -> int:
    import json
    from importlib import metadata
    data = {"_comment": "Produced by the ORIGINAL upstream package (not by the bundled copy) via "
                        "scripts/compare_with_upstream.py --write-golden.",
            "upstream_version": metadata.version("lizard"), "files": {}}
    for path in files_under([ROOT / "tests" / "fixtures", ROOT / "sample_projects"]):
        info = upstream.analyze_file(str(path))
        snap = snapshot(info)
        data["files"][path.relative_to(ROOT).as_posix()] = {
            "nloc": snap["nloc"], "token_count": snap["token_count"],
            "functions": [dict(zip(FUNC_ATTRS, f)) for f in snap["functions"]]}
    out.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(data['files'])} files, "
          f"{sum(len(v['functions']) for v in data['files'].values())} functions)")
    return 0


def main(argv) -> int:
    upstream = load_upstream()
    if argv[:1] == ["--write-golden"]:
        return write_golden(upstream, Path(argv[1]))
    from third_party.lizard import UPSTREAM_VERSION, analyze_file as bundled
    from importlib import metadata
    print(f"upstream lizard {metadata.version('lizard')}  vs  bundled core {UPSTREAM_VERSION}")
    targets = argv or [ROOT / "tests" / "fixtures", ROOT / "sample_projects"]
    import shutil
    import tempfile
    files = checked = functions = 0
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        for path in files_under(targets):
            files += 1
            # same content under every supported extension spelling of its language family
            fam = ({".py"} if path.suffix.lower() == ".py" else EXTS - {".py"})
            for n, ext in enumerate(sorted(fam)):
                copy = Path(tmp) / f"f{files}_{n}{ext}"
                shutil.copyfile(path, copy)
                a, b = snapshot(upstream.analyze_file(str(copy))), snapshot(bundled(str(copy)))
                checked += 1
                functions += len(b["functions"])
                if a != b:
                    problems.append(f"{path} (as {ext})")
                    if len(problems) <= 10:
                        print("DIFFERENT:", path, "as", ext)
    print(f"files: {files}, analyses compared: {checked}, functions compared: {functions}, "
          f"differences: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
