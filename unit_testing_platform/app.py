"""Unit Testing Platform: entry point.  Start with:  streamlit run app.py"""
from __future__ import annotations

import streamlit as st

from config import APP_NAME, APP_PHASE, load_limits
from services.source_upload import cleanup_stale_workspaces
from ui import complexity_analysis, excel_analysis
from ui.threshold import threshold_sidebar

st.set_page_config(page_title=APP_NAME, page_icon="🧪", layout="wide")

PAGES = {
    "Complexity Analysis": complexity_analysis.render,
    "Excel Report Analysis": excel_analysis.render,
}


def main() -> None:
    limits = load_limits()
    if not st.session_state.get("_stale_cleaned"):
        cleanup_stale_workspaces()
        st.session_state["_stale_cleaned"] = True

    page = st.sidebar.radio("Navigation", list(PAGES), key="nav", label_visibility="collapsed")
    st.sidebar.divider()
    cfg = threshold_sidebar()

    st.title(APP_NAME)
    st.caption(APP_PHASE)
    PAGES[page](cfg, limits)


main()
