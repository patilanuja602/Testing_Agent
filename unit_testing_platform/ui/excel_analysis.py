"""Excel workflow: upload -> sheet -> header row -> column mapping -> import -> dashboard."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import PurePosixPath

import streamlit as st

from config import Limits
from models.analysis_result import AnalysisRun, SkippedFile, ThresholdConfig
from services.excel_importer import (
    CONVENTION_NOTE, ENGINE_LABEL, FIELD_LABELS, ColumnMapping, ExcelImportError, apply_header,
    detect_header_row, import_records, read_raw_sheet, read_sheet_names, suggest_mapping,
    validate_excel_upload, validate_mapping,
)
from ui.dashboard import render_run

_NONE = "(none)"
_FIELD_ORDER = ["complexity", "function", "file", "start_line", "end_line", "threshold", "nloc", "parameters"]


def render(cfg: ThresholdConfig, limits: Limits) -> None:
    st.header("Excel Report Analysis")
    st.caption("Import a complexity report produced by another tool (.xlsx). "
               "Values are imported as-is and are not recalculated.")
    upload = st.file_uploader("Excel Report (.xlsx)", type=["xlsx", "xls"], key="xl_uploader")
    if upload is None:
        if "xl_run" in st.session_state:
            st.divider()
            render_run(st.session_state["xl_run"], cfg, "xl")
        return

    data = upload.getvalue()
    try:
        validate_excel_upload(upload.name, data, limits)
        sheets = read_sheet_names(data)
    except ExcelImportError as exc:
        st.error(str(exc))
        return
    sig = hashlib.sha256(data).hexdigest()[:16]

    sheet = st.selectbox("Worksheet", sheets, key=f"xl_sheet_{sig}")
    try:
        raw = read_raw_sheet(data, sheet)
    except ExcelImportError as exc:
        st.error(str(exc))
        return

    detection = detect_header_row(raw)
    if not detection.confident:
        st.warning("The header row could not be detected reliably. Check the header row below and "
                   "map the columns manually if needed.")
    header_row = int(st.number_input("Header row (1 = first non-empty row of the sheet)", 1, len(raw),
                                     detection.row_index + 1, key=f"xl_hdr_{sig}_{sheet}")) - 1
    table = apply_header(raw, header_row)
    st.markdown("**Preview** (first 15 rows)")
    st.dataframe(table.head(15).astype(str), hide_index=True)

    suggestion = suggest_mapping(table)
    st.subheader("Column Mapping")
    st.caption("Columns were detected from the header names. Change any selection that is wrong.")
    options = [_NONE] + [str(c) for c in table.columns]
    chosen = {}
    cols = st.columns(2)
    for i, name in enumerate(_FIELD_ORDER):
        default = getattr(suggestion, name)
        label = FIELD_LABELS[name] + (" (required)" if name in ("complexity", "function") else "")
        pick = cols[i % 2].selectbox(label, options, index=options.index(default) if default in options else 0,
                                     key=f"xl_map_{sig}_{sheet}_{header_row}_{name}")
        chosen[name] = None if pick == _NONE else pick
    mapping = ColumnMapping(**chosen)

    check = validate_mapping(table, mapping)
    for e in check.errors:
        st.error(e)
    for w in check.warnings:
        st.warning(w)

    if st.button("Import Report", type="primary", disabled=not check.ok, key=f"xl_import_{sig}"):
        started = datetime.now()
        try:
            outcome = import_records(table, mapping, sheet=sheet, source_name=upload.name)
        except ExcelImportError as exc:
            st.error(str(exc))
            return
        mapped = {FIELD_LABELS[k]: v for k, v in chosen.items() if v}
        run = AnalysisRun(
            project_name=PurePosixPath(upload.name).stem, origin="excel", engine=ENGINE_LABEL, engine_version="",
            created_at=started, functions=outcome.results, notes=[CONVENTION_NOTE] + outcome.warnings,
            skipped=[SkippedFile(f"{sheet}, data row {n}", reason, "invalid") for n, reason in outcome.skipped_rows],
            duration_s=(datetime.now() - started).total_seconds(),
            details={"Source file": upload.name, "Worksheet": sheet, "Header row": header_row + 1,
                     "Column mapping": "; ".join(f"{k} = {v}" for k, v in mapped.items()),
                     "_original_columns": outcome.original_columns},
        )
        st.session_state["xl_run"] = run
        st.rerun()

    if "xl_run" in st.session_state:
        st.divider()
        st.subheader("Results")
        render_run(st.session_state["xl_run"], cfg, "xl")
