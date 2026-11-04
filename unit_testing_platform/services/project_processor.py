"""Workflow glue: staged files + user selection -> AnalysisRun."""
from __future__ import annotations

from typing import Collection, List, Optional

from core.analyzer import ProgressCallback, analyze_files
from core.complexity import ComplexityEngine
from models.analysis_result import AnalysisRun, Language, SkippedFile
from services.source_upload import StagedProject


def run_source_analysis(
    staged: StagedProject,
    *,
    project_name: str,
    selected_paths: Collection[str],
    selected_languages: Collection[Language],
    engine: Optional[ComplexityEngine] = None,
    progress: Optional[ProgressCallback] = None,
) -> AnalysisRun:
    """Analyse the files the user confirmed. Unselected files are reported as skipped."""
    engine = engine or ComplexityEngine()
    to_analyze, not_selected = [], []
    for f in staged.files:
        if f.language in selected_languages and f.display_path in selected_paths:
            to_analyze.append(f)
        else:
            reason = ("Language not selected" if f.language not in selected_languages
                      else "Not selected for analysis")
            not_selected.append(SkippedFile(f.display_path, reason, "not_selected"))

    run = analyze_files(
        to_analyze, engine, project_name=project_name,
        selected_languages=list(selected_languages),
        files_uploaded=staged.files_received,
        skipped=list(staged.skipped) + not_selected, progress=progress,
    )
    run.errors.extend(staged.errors)
    if not to_analyze:
        run.errors.append("No files were analysed: nothing supported was selected.")
    return run
