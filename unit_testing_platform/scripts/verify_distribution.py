"""Independent checks of a distributable ZIP, made only from the ZIP itself.

    python scripts/verify_distribution.py unit_testing_platform.zip [--run-tests] [--python PYTHON]

1. Required application, documentation and licensing files are present.
2. No development leftovers: virtual environment, bytecode, caches, VCS data, secrets, nested archives.
3. Every first-party import in every shipped .py file resolves to a file inside the ZIP.
4. All Python files compile.
5. The licence verifier shipped inside the ZIP passes when run from the extracted copy.
6. With --run-tests: the full test suite is run from the extracted copy (needs the dependencies installed).
Exit status 1 on any failure.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REQUIRED = [
    "app.py", "config.py", "requirements.txt", "README.md", "pytest.ini", "THIRD_PARTY_NOTICES.md", "LICENSES.md",
    "docs/PREPROCESSOR_LIMITATIONS.md",
    "core/__init__.py", "core/complexity/__init__.py", "core/complexity/engine.py", "core/complexity/backend.py",
    "core/complexity/reader.py", "core/language_detector.py", "core/limitations.py", "core/threshold_manager.py",
    "models/analysis_result.py", "services/source_upload.py", "services/header_resolver.py",
    "services/project_processor.py", "services/excel_importer.py", "services/report_generator.py",
    "ui/complexity_analysis.py", "ui/excel_analysis.py", "ui/dashboard.py",
    "third_party/lizard/LICENSE.txt", "third_party/lizard/LICENSE-Apache-2.0.txt",
    "third_party/lizard/UPSTREAM_MANIFEST.json", "third_party/lizard/MODIFICATIONS.md", "third_party/lizard/README.md",
    "third_party/lizard/__init__.py", "third_party/lizard/lizard_languages/clike.py",
    "scripts/verify_licensing.py", "scripts/make_distribution.py", "scripts/verify_distribution.py",
    "sample_projects/embedded_demo.zip", "tests/test_code_samples/embedded_demo.zip",
    "tests/conftest.py", "tests/fixtures/expected.json", "tests/test_ui_flow.py", "tests/test_licensing.py",
]
FORBIDDEN_DIRS = {"venv", ".venv", "env", "__pycache__", ".pytest_cache", ".git", ".idea", ".vscode", "dist"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".log")
ALLOWED_ARCHIVES = ("sample_projects/", "tests/")          # demo projects are archives on purpose
FORBIDDEN_NAMES = {"secrets.toml", ".env", ".DS_Store"}
FIRST_PARTY = {"core", "models", "services", "ui", "config", "third_party", "tests"}
SAMPLE_DIRS = ("tests/fixtures/", "tests/test_code_samples/", "sample_projects/")   # contain deliberately invalid code


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip", type=Path)
    ap.add_argument("--run-tests", action="store_true")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()
    failures = []
    with zipfile.ZipFile(args.zip) as zf:
        bad = zf.testzip()
        if bad:
            failures.append(f"corrupt member: {bad}")
        names = [n for n in zf.namelist() if not n.endswith("/")]
        tops = {n.split("/", 1)[0] for n in names}
        if len(tops) != 1:
            failures.append(f"expected a single top-level folder, found {sorted(tops)}")
        top = sorted(tops)[0]
        rel = {n[len(top) + 1:] for n in names}
        for req in REQUIRED:
            if req not in rel:
                failures.append(f"missing required file: {req}")
        for n in sorted(rel):
            if n.endswith(".zip") and not n.startswith(ALLOWED_ARCHIVES):
                failures.append(f"must not be shipped (nested archive): {n}")
            parts = n.split("/")
            if any(p in FORBIDDEN_DIRS or p.endswith(".egg-info") for p in parts[:-1]) or n.endswith(FORBIDDEN_SUFFIXES) \
                    or parts[-1] in FORBIDDEN_NAMES:
                failures.append(f"must not be shipped: {n}")
        # first-party imports must resolve inside the archive
        for n in sorted(rel):
            if not n.endswith(".py") or n.startswith(SAMPLE_DIRS):
                continue
            tree = ast.parse(zf.read(f"{top}/{n}").decode("utf-8"), filename=n)
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    mods = [node.module]
                for mod in mods:
                    if mod.split(".")[0] in FIRST_PARTY:
                        path = mod.replace(".", "/")
                        if f"{path}.py" not in rel and f"{path}/__init__.py" not in rel:
                            failures.append(f"{n}: import {mod} is not in the archive")
        with tempfile.TemporaryDirectory() as tmp:
            zf.extractall(tmp)
            root = Path(tmp) / top
            comp = subprocess.run([args.python, "-m", "compileall", "-q", "-x", r"(fixtures|test_code_samples|sample_projects)", str(root)], capture_output=True, text=True)
            if comp.returncode:
                failures.append("compileall failed: " + comp.stdout[-300:] + comp.stderr[-300:])
            lic = subprocess.run([args.python, "scripts/verify_licensing.py"], cwd=root, capture_output=True, text=True)
            if lic.returncode:
                failures.append("licence verifier failed inside the extracted copy:\n" + lic.stdout)
            if args.run_tests:
                res = subprocess.run([args.python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs"], cwd=root,
                                     capture_output=True, text=True)
                print(res.stdout[-1500:])
                if res.returncode:
                    failures.append("test suite failed inside the extracted copy")
    print(f"{len(names)} files in {args.zip.name}")
    for f in failures:
        print("FAIL", f)
    print("RESULT:", "OK" if not failures else f"{len(failures)} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
