"""Cyclomatic Complexity Module: adapter between the application and the locally
integrated analysis core (``third_party/lizard``). Enabled languages: C and C++ (the core also
contains a Python reader, which is not enabled in this release).

Architecture (everything runs in-process, locally):

    this module  ->  third_party.lizard.analyze_file(path)  ->  FileInformation
                 ->  FunctionResult / FileResult (models.analysis_result)

The backend API used (unchanged from the upstream code it was taken from):

    analyze_file(path) -> FileInformation
    FileInformation.function_list -> [FunctionInfo]
    FunctionInfo: name, long_name, cyclomatic_complexity, nloc, token_count,
                  parameter_count, start_line, end_line

Every attribute is read defensively: a missing attribute becomes ``None``
("unavailable") instead of an invented value. No network access, no external
analysis package, no subprocess.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, List, Optional, Tuple

from core.limitations import MSG_NO_FUNCTIONS, scan_source
from models.analysis_result import AnalysisStatus, FileResult, FunctionResult, Language

ENGINE_NAME = "Built-in complexity analyzer"
ENGINE_VERSION = "1.0.0"          # version of this module; the core release is added in `version`
# Warnings on the lines just above a function (e.g. "template <...>") belong to it.
_LOOKBEHIND_LINES = 3


class EngineUnavailableError(RuntimeError):
    """The bundled analysis core could not be loaded (incomplete or damaged installation)."""


def _as_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ComplexityEngine:
    name = ENGINE_NAME
    supported_languages = (Language.C, Language.CPP)

    def __init__(self, backend: Any = None) -> None:
        """``backend`` is any object with ``analyze_file(path_str)``; it allows dependency
        injection (used by adapter tests). Default: the bundled core."""
        if backend is None:
            try:
                from third_party import lizard as backend  # type: ignore[no-redef]
            except ImportError as exc:  # pragma: no cover - only with a damaged installation
                raise EngineUnavailableError(
                    "The built-in complexity analyzer could not be loaded. "
                    "Re-install the application files (the 'third_party' folder is missing or damaged).") from exc
        self._backend = backend

    @property
    def version(self) -> str:
        core = getattr(self._backend, "UPSTREAM_VERSION", None)
        return f"{ENGINE_VERSION} (core {core})" if core else ENGINE_VERSION

    def analyze_file(self, disk_path: Path, display_path: str, language: Language) -> Tuple[FileResult, List[FunctionResult]]:
        started = time.perf_counter()
        file_result = FileResult(path=display_path, language=language.value, status=AnalysisStatus.SUCCESS)
        try:
            info = self._backend.analyze_file(str(disk_path))
            raw_functions = list(getattr(info, "function_list", []) or [])
            text = disk_path.read_text(encoding="utf-8", errors="replace")
            scan = scan_source(text, language)
        except Exception as exc:  # file-level failure must not stop other files
            file_result.status = AnalysisStatus.FAILED
            # Class name + message only; never file contents or workspace paths.
            file_result.error = f"{type(exc).__name__}: {str(exc).replace(str(disk_path), display_path)}"[:500]
            file_result.duration_s = time.perf_counter() - started
            return file_result, []

        functions: List[FunctionResult] = []
        for raw in raw_functions:
            start, end = _as_int(getattr(raw, "start_line", None)), _as_int(getattr(raw, "end_line", None))
            ccn = _as_int(getattr(raw, "cyclomatic_complexity", None))
            warnings = list(scan.file_warnings)
            if start is not None:
                hi = end if end is not None else start
                warnings += [msg for line, msg in scan.line_risks
                             if start - _LOOKBEHIND_LINES <= line <= hi]
            if ccn is None:
                warnings.append("Complexity value not provided by the engine")
            name = getattr(raw, "name", None) or "<unnamed>"
            functions.append(FunctionResult(
                file=display_path, function=str(name), ccn=ccn,
                language=language.value, engine=ENGINE_NAME,
                analysis_status=AnalysisStatus.WARNING if warnings else AnalysisStatus.SUCCESS,
                start_line=start, end_line=end,
                nloc=_as_int(getattr(raw, "nloc", None)),
                parameters=_as_int(getattr(raw, "parameter_count", None)),
                token_count=_as_int(getattr(raw, "token_count", None)),
                long_name=getattr(raw, "long_name", None),
                warnings=list(dict.fromkeys(warnings)),   # de-duplicate, keep order
            ))

        file_result.function_count = len(functions)
        file_result.warnings = list(scan.file_warnings)
        if not functions and text.strip():
            file_result.warnings.append(MSG_NO_FUNCTIONS)
        if file_result.warnings or any(f.analysis_status is AnalysisStatus.WARNING for f in functions):
            file_result.status = AnalysisStatus.WARNING
        file_result.duration_s = time.perf_counter() - started
        return file_result, functions
