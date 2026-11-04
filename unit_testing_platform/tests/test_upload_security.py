import io
import tempfile
import zipfile
from pathlib import Path

import pytest

from config import Limits, MB
from services.source_upload import UploadedItem, sanitize_member_path, stage_uploads
from tests.helpers import SMALL_LIMITS, make_zip

C_SRC = b"int f(int a){ if (a) { return 1; } return 0; }\n"


def stage(items, limits=SMALL_LIMITS):
    return stage_uploads(items, limits)


# ---- path sanitising --------------------------------------------------------
@pytest.mark.parametrize("name", ["../evil.c", "a/../../evil.c", "/etc/evil.c", "C:/evil.c", "..\\evil.c",
                                  "a\\..\\..\\evil.c", "a\x00b.c", "", "./", ".."])
def test_unsafe_names_rejected(name):
    assert sanitize_member_path(name) is None


def test_safe_names_normalised():
    assert str(sanitize_member_path("src\\drivers/./uart.c")) == "src/drivers/uart.c"


# ---- ZIP handling -----------------------------------------------------------
def test_zip_path_traversal_is_not_extracted(tmp_path):
    outside_before = set(Path(tempfile.gettempdir()).glob("evil*.c"))
    data = make_zip({"../evil.c": C_SRC, "/abs_evil.c": C_SRC, "ok/good.c": C_SRC})
    project = stage([UploadedItem("p.zip", data)])
    try:
        assert [f.display_path for f in project.files] == ["ok/good.c"]
        assert sum(1 for s in project.skipped if s.category == "unsafe") == 2
        assert set(Path(tempfile.gettempdir()).glob("evil*.c")) == outside_before
        assert not (project.workspace.parent / "evil.c").exists()
        for f in project.files:                       # everything lives inside the workspace
            assert project.workspace.resolve() in f.disk_path.resolve().parents
    finally:
        project.cleanup()


def test_directory_structure_and_duplicate_names_preserved():
    data = make_zip({"a/main.c": C_SRC, "b/main.c": C_SRC, "docs/readme.txt": b"hi", "build/app.exe": b"MZ"})
    project = stage([UploadedItem("proj.zip", data)])
    try:
        assert sorted(f.display_path for f in project.files) == ["a/main.c", "b/main.c"]
        assert len({f.disk_path for f in project.files}) == 2
        reasons = {s.path: s.category for s in project.skipped}
        assert reasons["docs/readme.txt"] == "unsupported" and reasons["build/app.exe"] == "unsupported"
        assert project.files_received == 4
    finally:
        project.cleanup()


def test_duplicate_filenames_from_separate_uploads_get_unique_display_names():
    project = stage([UploadedItem("main.c", C_SRC), UploadedItem("main.c", C_SRC)])
    try:
        assert sorted(f.display_path for f in project.files) == ["main (2).c", "main.c"]
    finally:
        project.cleanup()


def test_symlink_and_nested_zip_and_ignored_dir_skipped():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        link = zipfile.ZipInfo("link.c")
        link.external_attr = (0o120777 << 16)
        zf.writestr(link, "/etc/passwd")
        zf.writestr("inner.zip", b"PK\x03\x04")
        zf.writestr(".git/hooks/x.c", C_SRC)
        zf.writestr("src/real.c", C_SRC)
    project = stage([UploadedItem("p.zip", buf.getvalue())])
    try:
        assert [f.display_path for f in project.files] == ["src/real.c"]
        cats = {s.path: s.category for s in project.skipped}
        assert cats["link.c"] == "unsafe" and cats["inner.zip"] == "unsupported" and cats[".git/hooks/x.c"] == "ignored"
    finally:
        project.cleanup()


def test_zip_bomb_ratio_and_size_limits():
    limits = Limits(50 * MB, 50 * MB, 1000, 1 * MB, 200, 5 * MB)
    bomb = make_zip({"big.c": b"/" + b"a" * (900 * 1024)})            # highly compressible
    project = stage([UploadedItem("bomb.zip", bomb)], limits)
    try:
        assert not project.files and project.skipped[0].category == "unsafe"
    finally:
        project.cleanup()
    too_big = make_zip({"huge.c": (b"int x;\n" * 300000)})              # ~2 MB > 1 MB source limit
    project = stage([UploadedItem("big.zip", too_big)], limits)
    try:
        assert not project.files and project.skipped[0].category == "too_large"
    finally:
        project.cleanup()


def test_too_many_members_rejected():
    limits = Limits(50 * MB, 50 * MB, 3, 1 * MB, 200, 5 * MB)
    project = stage([UploadedItem("m.zip", make_zip({f"f{i}.c": C_SRC for i in range(5)}))], limits)
    try:
        assert not project.files and any("too many" in e for e in project.errors)
    finally:
        project.cleanup()


def test_extracted_total_limit():
    limits = Limits(50 * MB, len(C_SRC) * 2, 1000, 1 * MB, 200, 5 * MB)
    project = stage([UploadedItem("t.zip", make_zip({f"f{i}.c": C_SRC for i in range(6)}))], limits)
    try:
        assert len(project.files) == 2 and any("extracted size limit" in e for e in project.errors)
    finally:
        project.cleanup()


# ---- error handling ---------------------------------------------------------
def test_invalid_zip_reports_error():
    project = stage([UploadedItem("broken.zip", b"this is not a zip file at all")])
    try:
        assert project.errors and "not a valid ZIP" in project.errors[0] and not project.files
    finally:
        project.cleanup()


def test_truncated_zip_reports_error():
    data = make_zip({"a.c": C_SRC})
    project = stage([UploadedItem("cut.zip", data[: len(data) // 2])])
    try:
        assert project.errors and not project.files
    finally:
        project.cleanup()


def test_empty_upload_and_empty_project_and_no_sources():
    p1 = stage([UploadedItem("a.c", b"")])
    p2 = stage([UploadedItem("p.zip", make_zip({}))])
    p3 = stage([UploadedItem("p.zip", make_zip({"readme.md": b"x", "data.bin": b"\x00"}))])
    try:
        assert p1.errors and not p1.files
        assert not p2.files
        assert not p3.files and len(p3.skipped) == 2
    finally:
        for p in (p1, p2, p3):
            p.cleanup()


def test_unsupported_and_binary_single_files():
    project = stage([UploadedItem("notes.txt", b"hello"), UploadedItem("fake.c", b"\x00\x01\x02\x03"),
                     UploadedItem("report.xlsx", b"PK")])
    try:
        assert not project.files
        by_path = {s.path: s for s in project.skipped}
        assert by_path["notes.txt"].category == "unsupported"
        assert by_path["fake.c"].category == "invalid"
        assert "Excel" in by_path["report.xlsx"].reason
    finally:
        project.cleanup()


def test_upload_over_limit_rejected():
    limits = Limits(10, 50 * MB, 1000, 1 * MB, 200, 5 * MB)
    project = stage([UploadedItem("big.c", C_SRC)], limits)
    try:
        assert project.errors and not project.files
    finally:
        project.cleanup()


def test_uploaded_code_is_never_executed(tmp_path):
    marker = tmp_path / "executed.txt"
    evil_py = f"open({str(marker)!r}, 'w').write('x')\n".encode()
    project = stage([UploadedItem("evil.py", evil_py)])
    try:
        assert project.files == [] and [x.category for x in project.skipped] == ["unsupported"]
        assert not marker.exists()
    finally:
        project.cleanup()


def test_cleanup_removes_workspace():
    project = stage([UploadedItem("a.c", C_SRC)])
    ws = project.workspace
    assert ws.exists()
    project.cleanup()
    assert not ws.exists()
