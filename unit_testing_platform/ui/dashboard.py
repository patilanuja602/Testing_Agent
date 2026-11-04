"""Result dashboard shared by the source-code and Excel workflows."""
from __future__ import annotations

from typing import List

import streamlit as st

from core.result_normalizer import average_complexity, results_to_dataframe
from core.threshold_manager import apply_threshold, count_by_status
from models.analysis_result import AnalysisRun, AnalysisStatus, FunctionResult, ThresholdConfig, ThresholdStatus
from services.report_generator import build_csv, build_workbook


def render_run(run: AnalysisRun, cfg: ThresholdConfig, key: str) -> None:
    results = apply_threshold(run.functions, cfg)
    _render_messages(run)
    _render_summary(run, results, cfg)
    tabs = st.tabs(["Functions", "Analysis warnings", "Files" if run.origin == "source" else "Imported rows", "Skipped", "Export"])
    with tabs[0]:
        _render_function_table(results, key)
    with tabs[1]:
        _render_warnings(run, results)
    with tabs[2]:
        _render_files(run)
    with tabs[3]:
        _render_skipped(run)
    with tabs[4]:
        _render_exports(run, cfg, key)


def _render_messages(run: AnalysisRun) -> None:
    for err in run.errors:
        st.error(err)
    for note in run.notes:
        st.warning(note)


def _render_summary(run: AnalysisRun, results: List[FunctionResult], cfg: ThresholdConfig) -> None:
    counts = count_by_status(results)
    avg = average_complexity(results)
    warning_items = (sum(1 for f in run.file_results if f.status is not AnalysisStatus.SUCCESS)
                     + sum(1 for r in results if r.warnings))
    st.caption(cfg.rule_text())
    row1 = st.columns(5)
    if run.origin == "source":
        row1[0].metric("Files uploaded", run.files_uploaded)
        row1[1].metric("Files analyzed", run.files_analyzed)
        row1[2].metric("Files skipped", len(run.skipped))
        row1[3].metric("Files failed", run.files_failed)
    else:
        row1[0].metric("Rows imported", len(results))
        row1[1].metric("Rows skipped", len(run.skipped))
        row1[2].metric("Worksheet", run.details.get("Worksheet", "-"))
    row1[4].metric("Analysis time", f"{run.duration_s:.2f} s")
    row2 = st.columns(5)
    row2[0].metric("Functions detected" if run.origin == "source" else "Functions imported", len(results))
    row2[1].metric("Exceeding threshold", counts[ThresholdStatus.EXCEEDS])
    row2[2].metric("Within threshold", counts[ThresholdStatus.WITHIN])
    row2[3].metric("Analysis warnings", warning_items)
    row2[4].metric("Average complexity", f"{avg:.2f}" if avg is not None else "n/a")


def _render_function_table(results: List[FunctionResult], key: str) -> None:
    if not results:
        st.info("No functions to display.")
        return
    languages = sorted({r.language for r in results if r.language})
    files = sorted({r.file for r in results if r.file})
    values = [r.ccn for r in results if r.ccn is not None]

    c1, c2, c3 = st.columns(3)
    query = c1.text_input("Search file or function", key=f"{key}_q").strip().lower()
    sel_lang = c2.multiselect("Language", languages, key=f"{key}_lang")
    sel_status = c3.multiselect("Status", [s.value for s in ThresholdStatus], key=f"{key}_status")
    c4, c5 = st.columns(2)
    sel_files = c4.multiselect("File", files, key=f"{key}_files")
    rng = None
    if values and min(values) < max(values):
        rng = c5.slider("Complexity range", min(values), max(values), (min(values), max(values)), key=f"{key}_rng")

    def keep(r: FunctionResult) -> bool:
        if query and query not in f"{r.file or ''} {r.function}".lower():
            return False
        if sel_lang and r.language not in sel_lang:
            return False
        if sel_status and r.threshold_status.value not in sel_status:
            return False
        if sel_files and r.file not in sel_files:
            return False
        if rng and r.ccn is not None and not (rng[0] <= r.ccn <= rng[1]):
            return False
        if rng and r.ccn is None and rng != (min(values), max(values)):
            return False
        return True

    shown = [r for r in results if keep(r)]
    st.caption(f"Showing {len(shown)} of {len(results)} functions. Click a column header to sort. "
               "Empty cells mean the value is unavailable.")
    df = results_to_dataframe(shown)
    st.dataframe(df, hide_index=True)

    if shown:
        st.markdown("##### Inspect a function")
        idx = st.selectbox(
            "Function", list(range(len(shown))), key=f"{key}_inspect",
            format_func=lambda i: f"{shown[i].file or 'unknown file'} · {shown[i].function} · "
                                  f"CCN {shown[i].ccn if shown[i].ccn is not None else 'n/a'}")
        _render_detail(shown[idx])


def _as_rows(values: dict) -> list:
    return [{"Property": k, "Value": str(v)} for k, v in values.items()]


def _render_detail(r: FunctionResult) -> None:
    na = "unavailable"
    left, right = st.columns(2)
    left.dataframe(_as_rows({
        "File": r.file or na, "Function": r.function, "Long name": r.long_name or na,
        "Language": r.language or na,
    }), hide_index=True)
    right.dataframe(_as_rows({
        "Complexity": r.ccn if r.ccn is not None else na,
        "Threshold status": r.threshold_status.value, "Analysis status": r.analysis_status.value,
        "Start line": r.start_line if r.start_line is not None else na,
        "End line": r.end_line if r.end_line is not None else na,
        "Lines of code": r.nloc if r.nloc is not None else na,
        "Parameters": r.parameters if r.parameters is not None else na,
        "Tokens": r.token_count if r.token_count is not None else na,
        "Threshold in report": r.imported_threshold if r.imported_threshold is not None else na,
    }), hide_index=True)
    for w in r.warnings:
        st.warning(w)
    if r.original_data:
        with st.expander("Original row from the imported report"):
            st.write({k: ("" if v is None else v) for k, v in r.original_data.items()})


def _render_warnings(run: AnalysisRun, results: List[FunctionResult]) -> None:
    rows = []
    for f in run.file_results:
        if f.status is not AnalysisStatus.SUCCESS:
            rows.append({"File": f.path, "Function": "(file)",
                         "Type": "File failed" if f.status is AnalysisStatus.FAILED else "File warning",
                         "Message": f.error or "; ".join(f.warnings)})
    for r in results:
        if r.warnings:
            rows.append({"File": r.file or "unavailable", "Function": r.function, "Type": "Function warning",
                         "Message": "; ".join(r.warnings)})
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.success("No analysis warnings were raised. This does not guarantee the results are complete.")


def _render_files(run: AnalysisRun) -> None:
    if run.origin == "source":
        if not run.file_results:
            st.info("No files were analysed.")
            return
        st.dataframe([{"File": f.path, "Language": f.language, "Functions": f.function_count,
                       "Analysis Status": f.status.value, "Time (s)": round(f.duration_s, 4),
                       "Notes": f.error or "; ".join(f.warnings)} for f in run.file_results], hide_index=True)
    else:
        for k, v in run.details.items():
            if not str(k).startswith("_"):
                st.write(f"**{k}:** {v}")


def _render_skipped(run: AnalysisRun) -> None:
    if run.skipped:
        st.dataframe([{"Item": s.path, "Category": s.category, "Reason": s.reason} for s in run.skipped], hide_index=True)
    else:
        st.info("Nothing was skipped.")


def _render_exports(run: AnalysisRun, cfg: ThresholdConfig, key: str) -> None:
    signature = (id(run), cfg)
    slot = f"{key}_export"
    if st.button("Prepare Reports", key=f"{key}_prepare"):
        st.session_state[slot] = (signature, build_workbook(run, cfg), build_csv(run, cfg))
    ready = st.session_state.get(slot)
    if ready and ready[0] == signature:
        stamp = run.created_at.strftime("%Y%m%d_%H%M%S")
        c1, c2 = st.columns(2)
        c1.download_button("Download Excel Report (.xlsx)", ready[1], file_name=f"complexity_report_{stamp}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"{key}_dl_x")
        c2.download_button("Download CSV Report", ready[2], file_name=f"complexity_report_{stamp}.csv",
                           mime="text/csv", key=f"{key}_dl_c")
    elif ready:
        st.info("The threshold or results changed: press 'Prepare Reports' again.")
    else:
        st.caption("Reports use the threshold currently set in the sidebar.")
