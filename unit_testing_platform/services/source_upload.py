"""Safe staging of uploaded source files and ZIP projects.

Security properties (all covered by tests/test_upload_security.py):
  * uploads are only ever written inside a private temporary workspace;
  * ZIP member names are sanitised (no absolute paths, drive letters, '..',
    NUL bytes) and the final path is re-checked to stay inside the workspace;
  * symbolic links, encrypted entries and nested archives are never extracted;
  * only supported source files are extracted; sizes are enforced while
    streaming (the sizes declared in a ZIP header are not trusted);
  * nothing is executed or imported.
"""
from __future__ import annotations

import io
import shutil
import tempfile
import time
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import BinaryIO, List, Optional, Sequence, Union

from config import WORKSPACE_PREFIX, Limits
from core.language_detector import check_source_file, detect_language, unsupported_reason
from models.analysis_result import SkippedFile, StagedFile
from services.header_resolver import resolve_headers

IGNORED_DIRECTORIES = {".git", ".svn", ".hg", "__pycache__", "node_modules", "venv", ".venv", ".idea", ".vscode"}
_CHUNK = 64 * 1024
_STALE_WORKSPACE_SECONDS = 6 * 3600


@dataclass
class UploadedItem:
    """Framework-neutral upload (the UI wraps Streamlit's UploadedFile)."""
    name: str
    data: Union[bytes, BinaryIO]

    def stream(self) -> BinaryIO:
        return io.BytesIO(self.data) if isinstance(self.data, (bytes, bytearray)) else self.data

    def size(self) -> int:
        if isinstance(self.data, (bytes, bytearray)):
            return len(self.data)
        pos = self.data.tell()
        self.data.seek(0, io.SEEK_END)
        end = self.data.tell()
        self.data.seek(pos)
        return end


@dataclass
class StagedProject:
    workspace: Path
    files: List[StagedFile] = field(default_factory=list)
    skipped: List[SkippedFile] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    files_received: int = 0          # regular files received (ZIP members counted, directories not)

    def cleanup(self) -> None:
        shutil.rmtree(self.workspace, ignore_errors=True)


def sanitize_member_path(name: str) -> Optional[PurePosixPath]:
    """Return a safe relative path, or None if the name could escape the target."""
    normalised = name.replace("\\", "/")
    if "\x00" in normalised or normalised.startswith("/") or (len(normalised) > 1 and normalised[1] == ":"):
        return None
    parts = [p for p in normalised.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        return None
    return PurePosixPath(*parts)


def cleanup_stale_workspaces(max_age_seconds: int = _STALE_WORKSPACE_SECONDS) -> int:
    """Remove leftover workspaces from crashed sessions (our prefix only)."""
    removed = 0
    for path in Path(tempfile.gettempdir()).glob(f"{WORKSPACE_PREFIX}*"):
        try:
            if path.is_dir() and not path.is_symlink() and time.time() - path.stat().st_mtime > max_age_seconds:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed


class _Names:
    """Hands out unique display paths ('a.c', 'a (2).c', ...)."""
    def __init__(self) -> None:
        self.used: set = set()

    def unique(self, path: str) -> str:
        if path not in self.used:
            self.used.add(path)
            return path
        p, n = PurePosixPath(path), 2
        while True:
            candidate = str(p.with_name(f"{p.stem} ({n}){p.suffix}"))
            if candidate not in self.used:
                self.used.add(candidate)
                return candidate
            n += 1


def stage_uploads(items: Sequence[UploadedItem], limits: Limits) -> StagedProject:
    workspace = Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX))
    project = StagedProject(workspace=workspace)
    names = _Names()
    multiple = len(items) > 1
    extracted_total = [0]

    for index, item in enumerate(items):
        label = PurePosixPath(item.name.replace("\\", "/")).name or "(unnamed)"
        size = item.size()
        if size == 0:
            project.errors.append(f"'{label}' is empty.")
            continue
        if size > limits.max_upload_bytes:
            project.errors.append(f"'{label}' exceeds the upload size limit ({limits.max_upload_bytes // (1024 * 1024)} MB).")
            continue
        if label.lower().endswith(".zip"):
            _stage_zip(project, item, index, label, multiple, names, limits, extracted_total)
        else:
            _stage_single(project, item, index, label, names, limits)
    resolve_headers(project.files)      # needs every file of the project: decides the language of .h files
    return project


def _stage_single(project: StagedProject, item: UploadedItem, index: int, label: str,
                  names: _Names, limits: Limits) -> None:
    project.files_received += 1
    language = detect_language(label)
    if language is None:
        project.skipped.append(SkippedFile(label, unsupported_reason(label), "unsupported"))
        return
    target_dir = project.workspace / "files" / f"{index:04d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / PurePosixPath(label).name
    stream = item.stream()
    stream.seek(0)
    with target.open("wb") as out:
        shutil.copyfileobj(stream, out, _CHUNK)
    _register_file(project, target, names.unique(label), language, limits)


def _stage_zip(project: StagedProject, item: UploadedItem, index: int, label: str, multiple: bool,
               names: _Names, limits: Limits, extracted_total: List[int]) -> None:
    try:
        stream = item.stream()
        stream.seek(0)
        archive = zipfile.ZipFile(stream)
    except (zipfile.BadZipFile, OSError, EOFError):
        project.errors.append(f"'{label}' is not a valid ZIP archive or is corrupted.")
        return
    prefix = f"{PurePosixPath(label).stem}/" if multiple else ""
    root = project.workspace / "zip" / f"{index:04d}"
    root.mkdir(parents=True, exist_ok=True)
    root_resolved = root.resolve()

    with archive:
        members = archive.infolist()
        if len(members) > limits.max_zip_members:
            project.errors.append(f"'{label}' contains too many entries ({len(members)}; limit {limits.max_zip_members}).")
            return
        for info in members:
            if info.is_dir():
                continue
            project.files_received += 1
            raw_name = info.filename
            rel = sanitize_member_path(raw_name)
            shown = prefix + (str(rel) if rel else raw_name.replace("\\", "/"))
            if rel is None:
                project.skipped.append(SkippedFile(shown, "Unsafe path in archive (absolute or parent-directory reference): not extracted", "unsafe"))
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                project.skipped.append(SkippedFile(shown, "Symbolic link: not extracted", "unsafe"))
                continue
            if info.flag_bits & 0x1:
                project.skipped.append(SkippedFile(shown, "Encrypted entry: not extracted", "unsafe"))
                continue
            if any(part in IGNORED_DIRECTORIES for part in rel.parts[:-1]):
                project.skipped.append(SkippedFile(shown, "Inside an ignored directory", "ignored"))
                continue
            language = detect_language(rel.name)
            if language is None:
                project.skipped.append(SkippedFile(shown, unsupported_reason(rel.name), "unsupported"))
                continue
            if info.file_size > limits.max_source_file_bytes:
                project.skipped.append(SkippedFile(shown, "File exceeds the source file size limit", "too_large"))
                continue
            if info.compress_size > 0 and info.file_size / info.compress_size > limits.max_zip_ratio:
                project.skipped.append(SkippedFile(shown, "Suspicious compression ratio: not extracted", "unsafe"))
                continue
            if extracted_total[0] + info.file_size > limits.max_extracted_bytes:
                project.errors.append("Total extracted size limit reached; remaining files were not extracted.")
                break

            dest = (root / Path(*rel.parts))
            if not str(dest.resolve()).startswith(str(root_resolved)):   # defence in depth
                project.skipped.append(SkippedFile(shown, "Unsafe path in archive: not extracted", "unsafe"))
                continue
            written = _extract_member(archive, info, dest, limits.max_source_file_bytes)
            if written is None:
                project.skipped.append(SkippedFile(shown, "Entry is corrupted or exceeded the size limit while extracting", "invalid"))
                continue
            extracted_total[0] += written
            _register_file(project, dest, names.unique(shown), language, limits)


def _extract_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, dest: Path, max_bytes: int) -> Optional[int]:
    """Stream one member to disk, enforcing the size cap on bytes actually written."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with archive.open(info) as src, dest.open("wb") as out:
            while True:
                chunk = src.read(_CHUNK)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise ValueError("size limit exceeded")
                out.write(chunk)
        return written
    except (zipfile.BadZipFile, RuntimeError, OSError, EOFError, zlib.error, ValueError, NotImplementedError):
        dest.unlink(missing_ok=True)
        return None


def _register_file(project: StagedProject, disk_path: Path, display: str, language, limits: Limits) -> None:
    check = check_source_file(disk_path, language, limits.max_source_file_bytes)
    if not check.ok:
        project.skipped.append(SkippedFile(display, check.reason, check.category))
        disk_path.unlink(missing_ok=True)
        return
    project.files.append(StagedFile(display_path=display, disk_path=disk_path, language=language,
                                    size=disk_path.stat().st_size, warnings=check.warnings))
