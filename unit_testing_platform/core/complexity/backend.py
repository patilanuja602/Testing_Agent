"""Analysis backend used by :class:`core.complexity.engine.ComplexityEngine`.

It assembles the pipeline the bundled core uses (same token processors, same order) but drives
the application-owned reader (:mod:`core.complexity.reader`) instead of the stock C/C++ reader.
The vendored files themselves are not touched.

Unlike upstream's ``FileAnalyzer`` this backend never hides a failed parse: a ``RecursionError``
or an unexpected exception propagates to the engine, which reports the file as FAILED. (Upstream
prints a message to stderr and returns a partial result.)
"""
from __future__ import annotations

from typing import Optional

from third_party.lizard import UPSTREAM_VERSION
from third_party.lizard import analyze_file as _upstream_analyze_file
from third_party.lizard.lizard_core.file_analyzer import (
    comment_counter, condition_counter, line_counter, preprocessing, token_counter,
)
from third_party.lizard.lizard_core.file_info_builder import FileInfoBuilder
from third_party.lizard.lizard_ext import auto_read

from .reader import PREPROCESSOR_IGNORE, AppCLikeReader

_PIPELINE = (preprocessing, comment_counter, line_counter, token_counter, condition_counter)


class AppBackend:
    """``analyze_file(path, cpp=..., preprocessor=...)`` -> upstream ``FileInformation`` plus
    ``parser_warnings``: a list of ``(line, message)`` produced by the reader. ``cpp=None`` means
    "not C/C++": the call is delegated to the untouched upstream pipeline."""

    UPSTREAM_VERSION = UPSTREAM_VERSION
    accepts_options = True

    def __init__(self, preprocessor: str = PREPROCESSOR_IGNORE) -> None:
        self.preprocessor = preprocessor

    def analyze_file(self, path: str, cpp: Optional[bool] = None, preprocessor: Optional[str] = None):
        if cpp is None:
            # Not a C/C++ request (e.g. the dormant Python reader): unchanged upstream pipeline.
            return _upstream_analyze_file(path)
        code = auto_read(path)
        context = FileInfoBuilder(path)
        reader = AppCLikeReader(context, cpp=cpp, preprocessor=preprocessor or self.preprocessor)
        tokens = reader.generate_tokens(code)
        for processor in _PIPELINE:
            tokens = processor(tokens, reader)
        for _ in reader(tokens, reader):
            pass
        info = context.fileinfo
        info.parser_warnings = list(reader.parser_warnings)
        return info
