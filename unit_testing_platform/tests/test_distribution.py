"""The packaging scripts: the built ZIP verifies, and the verifier rejects a bad ZIP."""
import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify(zip_path):
    res = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_distribution.py"), str(zip_path)],
                         capture_output=True, text=True)
    return res.returncode, res.stdout


def test_built_zip_verifies_and_excludes_development_files(tmp_path):
    out = tmp_path / "d.zip"
    load("make_distribution").build(out)
    code, text = verify(out)
    assert code == 0, text
    names = zipfile.ZipFile(out).namelist()
    assert not [n for n in names if "/venv/" in n or "__pycache__" in n or n.endswith(".pyc") or ".pytest_cache" in n]
    assert "unit_testing_platform/THIRD_PARTY_NOTICES.md" in names and "unit_testing_platform/LICENSES.md" in names
    assert "unit_testing_platform/third_party/lizard/LICENSE.txt" in names
    # regression: the demo archives are part of the application and its tests; an earlier build dropped them
    assert "unit_testing_platform/sample_projects/embedded_demo.zip" in names
    assert "unit_testing_platform/tests/test_code_samples/embedded_demo.zip" in names


def test_verifier_rejects_a_zip_with_venv_missing_licence_and_tampered_vendor_file(tmp_path):
    good = tmp_path / "good.zip"
    load("make_distribution").build(good)
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(bad, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.endswith("/THIRD_PARTY_NOTICES.md"):
                continue                                                       # licence document missing
            if info.filename.endswith("lizard_languages/clike.py"):
                data = b"# tampered\n" + data                                  # vendored file changed
            dst.writestr(info, data)
        dst.writestr("unit_testing_platform/venv/lib/site.py", "x = 1\n")     # development environment shipped
        dst.writestr("unit_testing_platform/core/__pycache__/a.pyc", b"\0")
    code, text = verify(bad)
    assert code == 1
    assert "missing required file: THIRD_PARTY_NOTICES.md" in text
    assert "must not be shipped: venv/lib/site.py" in text and "__pycache__" in text
    assert "pinned hash" in text or "licence verifier failed" in text
