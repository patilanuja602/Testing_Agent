"""Shared test helpers (no pytest dependency)."""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openpyxl import Workbook

from config import Limits, MB
from models.analysis_result import AnalysisStatus, FileResult, FunctionResult, Language

FIXTURES = Path(__file__).parent / "fixtures"
SMALL_LIMITS = Limits(max_upload_bytes=50 * MB, max_extracted_bytes=50 * MB, max_zip_members=1000,
                      max_source_file_bytes=1 * MB, max_zip_ratio=200, max_excel_bytes=5 * MB)


def load_manifest() -> dict:
    return json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


def marker_lines(path: Path) -> Dict[str, Tuple[int, int]]:
    """{id: (start_line, end_line)} from 'START id' / 'END id' markers."""
    starts, ends = {}, {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for kind, target in (("START", starts), ("END", ends)):
            m = re.search(rf"\b{kind} (\w+)", line)
            if m and not m.group(1) == "id":
                target[m.group(1)] = n
    return {k: (starts[k], ends[k]) for k in starts if k in ends}


def make_zip(entries: Dict[str, bytes], extra_infos=None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def make_xlsx(sheets: Dict[str, List[list]]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in rows:
            ws.append(row)
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def fn(name="f", ccn: Optional[int] = 5, file="a.c", **kw) -> FunctionResult:
    return FunctionResult(file=file, function=name, ccn=ccn, language=kw.pop("language", "C"),
                          engine=kw.pop("engine", "Fake"), **kw)


class FakeEngine:
    """Engine stand-in for pipeline tests. Not a complexity implementation:
    results are canned and can be configured to fail for chosen files."""
    name = "Fake"
    version = "0.0"

    def __init__(self, fail_for=(), ccn=5):
        self.fail_for = set(fail_for)
        self.ccn = ccn

    def analyze_file(self, disk_path, display_path: str, language: Language):
        if display_path in self.fail_for:
            return FileResult(display_path, language.value, AnalysisStatus.FAILED, error="Boom: parser failed"), []
        f = fn("func", self.ccn, display_path, language=language.value, engine=self.name, start_line=1, end_line=3)
        return FileResult(display_path, language.value, AnalysisStatus.SUCCESS, function_count=1), [f]
