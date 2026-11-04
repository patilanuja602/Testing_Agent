"""Source-code workflow: upload -> validate -> confirm files -> analyse -> dashboard."""
from __future__ import annotations

import hashlib
from typing import List

import pandas as pd
import streamlit as st

from config import Limits
from core.language_detector import SUPPORTED_LANGUAGES, UPLOAD_EXTENSIONS
from core.complexity import ComplexityEngine, EngineUnavailableError
from models.analysis_result import Language, ThresholdConfig
from services.project_processor import run_source_analysis
from services.source_upload import StagedProject, UploadedItem, stage_uploads
from ui.dashboard import render_run


def _signature(items: List[UploadedItem]) -> str:
    h = hashlib.sha256()
    for it in items:
        h.update(it.name.encode("utf-8", "replace"))
        h.update(bytes(it.data) if not isinstance(it.data, bytes) else it.data)
    return h.hexdigest()


def _drop_staged() -> None:
    staged = st.session_state.pop("src_staged", None)
    if staged is not None:
        staged.cleanup()
    st.session_state.pop("src_sig", None)


def render(cfg: ThresholdConfig, limits: Limits) -> None:
    st.header("Complexity Analysis")

    try:
        engine = ComplexityEngine()
    except EngineUnavailableError as exc:
        st.error(str(exc))
        return

    c1, c2 = st.columns([2, 3])
    project_name = c1.text_input("Project Name", value="Untitled project", key="src_project").strip() or "Untitled project"
    languages = c2.multiselect("Languages to Analyse", [l.value for l in SUPPORTED_LANGUAGES],
                               default=[l.value for l in SUPPORTED_LANGUAGES], key="src_langs")
    uploads = st.file_uploader("Source Files or ZIP Project", type=UPLOAD_EXTENSIONS,
                               accept_multiple_files=True, key="src_uploader",
                               help="C and C++ source files (.c, .h, .cpp, .cc, .cxx, .hpp, .hh, .hxx) "
                                    "or a ZIP archive of a project. Files are analysed statically and never executed.")

    if not uploads:
        _drop_staged()
        if "src_run" in st.session_state:
            st.divider()
            render_run(st.session_state["src_run"], cfg, "src")
        return

    items = [UploadedItem(u.name, u.getvalue()) for u in uploads]
    sig = _signature(items)
    if st.session_state.get("src_sig") != sig or st.session_state.get("src_staged") is None:
        _drop_staged()
        with st.spinner("Validating upload..."):
            st.session_state["src_staged"] = stage_uploads(items, limits)
        st.session_state["src_sig"] = sig
    if st.session_state.get("src_run_sig") != sig:
        st.session_state.pop("src_run", None)      # results belong to a different upload
    staged: StagedProject = st.session_state["src_staged"]

    for err in staged.errors:
        st.error(err)
    selected_langs = [Language(v) for v in languages]
    candidates = [f for f in staged.files if f.language in selected_langs]

    st.subheader("1. Confirm Files")
    st.write(f"Received **{staged.files_received}** file(s): **{len(staged.files)}** supported, "
             f"**{len(staged.skipped)}** skipped.")
    if candidates:
        table = [{"Analyze": True, "File": f.display_path, "Language": f.language.value,
                  "Size (KB)": round(f.size / 1024, 1), "Notes": "; ".join(f.warnings)} for f in candidates]
        edited = st.data_editor(pd.DataFrame(table), hide_index=True, disabled=["File", "Language", "Size (KB)", "Notes"],
                                key=f"src_select_{sig}_{'-'.join(sorted(languages))}")
        selected_paths = {r["File"] for r in edited.to_dict("records") if r["Analyze"]}
    else:
        selected_paths = set()
        st.warning("No supported source files are available for the selected languages.")
    if staged.skipped:
        with st.expander(f"Skipped files ({len(staged.skipped)})"):
            st.dataframe([{"File": s.path, "Reason": s.reason} for s in staged.skipped], hide_index=True)

    st.subheader("2. Run Analysis")
    if st.button("Run Analysis", type="primary", disabled=not selected_paths, key="src_run_btn"):
        bar = st.progress(0.0, text="Starting...")

        def on_progress(done: int, total: int, current: str) -> None:
            bar.progress(done / total if total else 1.0, text=f"Analysing {current}" if current else "Finishing...")

        try:
            run = run_source_analysis(staged, project_name=project_name, selected_paths=selected_paths,
                                      selected_languages=selected_langs, engine=engine, progress=on_progress)
        finally:
            bar.empty()
            _drop_staged()          # uploaded copies are deleted as soon as analysis ends
        st.session_state["src_run"] = run
        st.session_state["src_run_sig"] = sig
        st.rerun()

    if "src_run" in st.session_state:
        st.divider()
        st.subheader("3. Results")
        render_run(st.session_state["src_run"], cfg, "src")
