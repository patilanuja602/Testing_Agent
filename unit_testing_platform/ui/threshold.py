"""Sidebar control for the single complexity threshold."""
from __future__ import annotations

import streamlit as st

from config import DEFAULT_THRESHOLD, MIN_THRESHOLD
from models.analysis_result import ThresholdConfig

THRESHOLD_KEY = "threshold"


def threshold_sidebar() -> ThresholdConfig:
    """One positive-integer input. The comparison (complexity >= threshold) is fixed."""
    st.sidebar.subheader("Complexity Threshold")
    value = st.sidebar.number_input("Enter Complexity Threshold", min_value=MIN_THRESHOLD,
                                    value=DEFAULT_THRESHOLD, step=1, format="%d", key=THRESHOLD_KEY)
    return ThresholdConfig(value=max(MIN_THRESHOLD, int(value)))
