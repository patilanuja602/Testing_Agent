"""Language detection (by extension) and basic file validation.

Nothing here executes or imports uploaded code.

Supported source languages in this release: C and C++.

To enable another language later (e.g. Python):
  1. make sure ``models.analysis_result.Language`` has it (Python already does),
  2. add its extensions to ``EXTENSION_MAP`` and the language to ``SUPPORTED_LANGUAGES`` below,
  3. add it to ``ComplexityEngine.supported_languages`` (core/complexity/engine.py); the bundled
     analysis core already contains a Python reader,
  4. add fixtures/expectations under tests/fixtures.
The Python-specific syntax check further down is kept for that purpose and is unreachable until then."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import List, Optional

from models.analysis_result import Language

EXTENSION_MAP = {
    ".c": Language.C,
    ".h": Language.C,          # ambiguous: see AMBIGUOUS_EXTENSIONS
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".hpp": Language.CPP,
    ".hh": Language.CPP,
    ".hxx": Language.CPP,
}
AMBIGUOUS_EXTENSIONS = {".h"}
SUPPORTED_LANGUAGES = [Language.C, Language.CPP]
UPLOAD_EXTENSIONS = sorted(e.lstrip(".") for e in EXTENSION_MAP) + ["zip"]


def extension_of(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).suffix.lower()


def detect_language(path: str) -> Optional[Language]:
    return EXTENSION_MAP.get(extension_of(path))


def unsupported_reason(path: str) -> str:
    ext = extension_of(path)
    if ext in (".xlsx", ".xls", ".xlsm"):
        return "Excel report: use the 'Excel Report Analysis' page to import it"
    if ext in (".zip", ".tar", ".gz", ".7z", ".rar"):
        return "Nested archive: not extracted"
    if not ext:
        return "No file extension: not treated as source code"
    return f"Unsupported file type '{ext}'"


@dataclass
class FileCheck:
    ok: bool
    reason: str = ""                       # set when ok is False
    category: str = "invalid"              # skip category when ok is False
    warnings: List[str] = field(default_factory=list)


def check_source_file(path: Path, language: Language, max_bytes: int) -> FileCheck:
    """Validate an on-disk file before it is handed to the analysis engine."""
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            head = fh.read(8192)
    except OSError:
        return FileCheck(False, "File could not be read", "invalid")
    if size == 0:
        return FileCheck(False, "Empty file", "invalid")
    if size > max_bytes:
        return FileCheck(False, f"File exceeds the size limit ({max_bytes // (1024 * 1024)} MB)", "too_large")
    if b"\x00" in head:
        return FileCheck(False, "Binary content detected: not a text source file", "invalid")

    warnings: List[str] = []
    try:
        head.decode("utf-8")
    except UnicodeDecodeError as exc:
        # A multi-byte character may simply be cut by the 8 KiB window.
        if exc.start < len(head) - 4:
            warnings.append("File is not valid UTF-8; characters may be decoded incorrectly")
    if path.suffix.lower() in AMBIGUOUS_EXTENSIONS:
        warnings.append("Header file (.h): language assumed to be C from the extension")

    if language is Language.PYTHON:
        try:
            ast.parse(path.read_bytes())
        except SyntaxError as exc:
            warnings.append(f"Python syntax error near line {exc.lineno}: results may be incomplete")
        except (ValueError, MemoryError, RecursionError):
            warnings.append("Python file could not be fully parsed for validation")
    return FileCheck(True, warnings=warnings)
