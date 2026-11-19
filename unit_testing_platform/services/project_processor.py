"""Workflow glue: staged files + user selection -> AnalysisRun."""
from __future__ import annotations

from dataclasses import replace
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
        if f.is_selectable(selected_languages) and f.display_path in selected_paths:
            # An ambiguous header is analysed (and reported) as the language the user selected.
            to_analyze.append(replace(f, language=f.effective_language(selected_languages)))
        else:
            reason = ("Not selected for analysis" if f.is_selectable(selected_languages)
                      else ("Language not selected" if not f.language_basis
                            else f"Language not selected (resolved as {f.language.value}: {f.language_basis})"))
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
