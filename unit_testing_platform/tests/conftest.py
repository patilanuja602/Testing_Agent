"""Test environment helpers.

Streamlit renders tables through pyarrow. On a normal development machine pyarrow is installed
(it is a Streamlit dependency) and NOTHING here is active: the real rendering path is exercised.

Only when pyarrow cannot be imported (a stripped-down CI box or a sandbox without the compiled
wheel) the tests would die inside ``st.dataframe`` for a reason unrelated to this application.
In that case ``st.dataframe`` / ``st.data_editor`` are replaced by recorders that keep the table
that the application *passed in* (``tests.conftest.TABLES``). The UI logic (selection, language
handling, threshold filtering, inspection, export, error display) still runs for real; what is
NOT verified in that mode is Arrow serialisation and browser rendering. The pytest header says
which mode is active, so a green run can never be mistaken for a full-rendering run.
"""
import pandas as pd
import pytest

try:
    import pyarrow  # noqa: F401
    PYARROW = True
except Exception:       # ImportError, or a compiled wheel for another Python version
    PYARROW = False

TABLES: list = []        # (kind, DataFrame) passed to st.dataframe / st.data_editor, in call order


def pytest_report_header(config):
    return ("UI table rendering: REAL (pyarrow available)" if PYARROW else
            "UI table rendering: BYPASSED (pyarrow unavailable): tables are recorded, Arrow serialisation not tested")


@pytest.fixture(autouse=True)
def _table_recorder(monkeypatch):
    """Always records the tables the application hands to Streamlit. With pyarrow available the call
    is passed through to the real Streamlit function (real rendering); without it the call is replaced."""
    TABLES.clear()
    import streamlit as st
    from streamlit.delta_generator import DeltaGenerator

    real_st_dataframe, real_st_editor, real_write = st.dataframe, st.data_editor, st.write
    real_dg_dataframe, real_dg_editor = DeltaGenerator.dataframe, DeltaGenerator.data_editor

    def _frame(data):
        return data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)

    def _first(args, kwargs):
        return args[0] if args else kwargs.get("data")

    def st_dataframe(*args, **kwargs):
        TABLES.append(("dataframe", _frame(_first(args, kwargs))))
        return real_st_dataframe(*args, **kwargs) if PYARROW else None

    def st_editor(*args, **kwargs):
        TABLES.append(("data_editor", _frame(_first(args, kwargs))))
        return real_st_editor(*args, **kwargs) if PYARROW else _frame(_first(args, kwargs))

    def dg_dataframe(self, *args, **kwargs):
        TABLES.append(("dataframe", _frame(_first(args, kwargs))))
        return real_dg_dataframe(self, *args, **kwargs) if PYARROW else None

    def dg_editor(self, *args, **kwargs):
        TABLES.append(("data_editor", _frame(_first(args, kwargs))))
        return real_dg_editor(self, *args, **kwargs) if PYARROW else _frame(_first(args, kwargs))

    def write(*args, **kwargs):
        if not PYARROW and args and isinstance(args[0], (dict, list)):
            TABLES.append(("write", args[0]))      # st.write(dict) probes for dataframes through pyarrow
            return None
        return real_write(*args, **kwargs)

    monkeypatch.setattr(st, "dataframe", st_dataframe)
    monkeypatch.setattr(st, "data_editor", st_editor)
    monkeypatch.setattr(st, "write", write)
    monkeypatch.setattr(DeltaGenerator, "dataframe", dg_dataframe)
    monkeypatch.setattr(DeltaGenerator, "data_editor", dg_editor)
    yield TABLES
