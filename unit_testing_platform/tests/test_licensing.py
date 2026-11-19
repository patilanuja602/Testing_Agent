"""The licence verifier itself is tested: it must pass on the repository and FAIL when something is wrong."""
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("verify_licensing", ROOT / "scripts" / "verify_licensing.py")
vl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vl)


def test_repository_passes_the_licence_checks():
    assert vl.check_vendored() == []
    assert vl.check_notices() == []


def test_tampered_unmodified_file_is_detected(tmp_path, monkeypatch):
    copy = tmp_path / "lizard"
    shutil.copytree(vl.LIZ, copy, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(vl, "LIZ", copy)
    (copy / "lizard_languages" / "clike.py").write_text("# changed\n" + (copy / "lizard_languages" / "clike.py").read_text())
    problems = vl.check_vendored()
    assert any("clike.py" in p and "pinned hash" in p for p in problems)


def test_missing_modification_notice_and_missing_licence_are_detected(tmp_path, monkeypatch):
    copy = tmp_path / "lizard"
    shutil.copytree(vl.LIZ, copy, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(vl, "LIZ", copy)
    target = copy / "lizard_core" / "file_analyzer.py"
    target.write_text(target.read_text().replace(vl.NOTICE, "NOTE removed"))
    (copy / "LICENSE.txt").write_text("no licence here\n")
    problems = vl.check_vendored()
    assert any("file_analyzer.py" in p for p in problems)
    assert any("LICENSE.txt: copyright line missing" in p for p in problems)


def test_new_python_file_outside_the_manifest_is_detected(tmp_path, monkeypatch):
    copy = tmp_path / "lizard"
    shutil.copytree(vl.LIZ, copy, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(vl, "LIZ", copy)
    (copy / "extra.py").write_text("x = 1\n")
    assert any("not covered by the manifest: extra.py" in p for p in vl.check_vendored())


def test_notices_file_must_reproduce_the_licence_verbatim(tmp_path, monkeypatch):
    fake = tmp_path / "root"
    fake.mkdir()
    shutil.copy(ROOT / "LICENSES.md", fake / "LICENSES.md")
    (fake / "THIRD_PARTY_NOTICES.md").write_text("Lizard MIT Apache 1.24.3\n")
    monkeypatch.setattr(vl, "ROOT", fake)
    problems = vl.check_notices()
    assert any("verbatim" in p for p in problems) and any("Copyright Terry Yin" in p for p in problems)
