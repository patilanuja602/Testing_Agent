"""Orchestrates a source-code analysis run over staged files."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Callable, List, Optional, Protocol, Sequence, Tuple

from core.result_normalizer import flag_duplicates
from models.analysis_result import (
    AnalysisRun, AnalysisStatus, FileResult, FunctionResult, Language, SkippedFile, StagedFile,
)

ProgressCallback = Callable[[int, int, str], None]


class AnalysisEngine(Protocol):
    name: str
    version: str

    def analyze_file(self, disk_path, display_path: str, language: Language) -> Tuple[FileResult, List[FunctionResult]]: ...


def analyze_files(
    files: Sequence[StagedFile],
    engine: AnalysisEngine,
    *,
    project_name: str,
    selected_languages: Sequence[Language],
    files_uploaded: int,
    skipped: Sequence[SkippedFile] = (),
    progress: Optional[ProgressCallback] = None,
) -> AnalysisRun:
    """Analyse each file independently; one failing file never stops the others."""
    started = time.perf_counter()
    run = AnalysisRun(
        project_name=project_name, origin="source", engine=engine.name,
        engine_version=engine.version, created_at=datetime.now(),
        selected_languages=[l.value for l in selected_languages],
        files_uploaded=files_uploaded, skipped=list(skipped), notes=[],
    )
    total = len(files)
    for index, staged in enumerate(files, start=1):
        if progress:
            progress(index - 1, total, staged.display_path)
        try:
            file_result, functions = engine.analyze_file(staged.disk_path, staged.display_path, staged.language)
        except Exception as exc:  # engine adapters should not raise, but never trust that
            file_result = FileResult(staged.display_path, staged.language.value, AnalysisStatus.FAILED,
                                     error=f"{type(exc).__name__}: analysis failed")
            functions = []
        if staged.warnings:
            file_result.warnings = list(dict.fromkeys(staged.warnings + file_result.warnings))
            if file_result.status is AnalysisStatus.SUCCESS:
                file_result.status = AnalysisStatus.WARNING
        run.file_results.append(file_result)
        run.functions.extend(functions)
    if progress:
        progress(total, total, "")
    flag_duplicates(run.functions)
    run.duration_s = time.perf_counter() - started
    return run
