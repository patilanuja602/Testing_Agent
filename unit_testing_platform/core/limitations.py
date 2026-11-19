"""Heuristic detection of constructs that the analyzer's partial parsers are known
to handle unreliably. This does NOT measure accuracy: it only raises visible
warnings so results are not presented as guaranteed.

Warnings are produced from simple text patterns and can be false positives.
File contents are never logged."""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import List, Tuple

from models.analysis_result import Language

_PP_CONDITIONAL = re.compile(r"^\s*#\s*(if|ifdef|ifndef|elif)\b")
_PP_FUNC_MACRO = re.compile(r"^\s*#\s*define\s+\w+\(")
_TEMPLATE = re.compile(r"\btemplate\s*<")

MSG_CONDITIONAL = ("Conditional compilation (#if/#ifdef) is not preprocessed: all branches are analysed "
                   "together (union of all configurations) and the directives themselves are not counted, "
                   "so the value can exceed the complexity of any single build configuration")
MSG_PP_SPLIT = ("Conditional compilation splits code blocks: braces are not balanced inside a branch of "
                "#if/#else, so functions around it may be mis-detected or missing from the results")
MSG_FUNC_MACRO = ("Function-like macros are defined in this file; the analyzer does not expand "
                  "macros, so complexity hidden inside macros is not counted")
MSG_TEMPLATE = "C++ template near this function: the analyzer's parser may mis-detect or mis-count"
MSG_MATCH = "Python match/case: counting depends on the engine's convention; verify manually"
MSG_NO_FUNCTIONS = ("No functions were detected in a non-empty file (declarations only, "
                    "macros, or a construct the parser could not recognise)")


@dataclass
class LimitationScan:
    file_warnings: List[str] = field(default_factory=list)
    # (line_number, message): attached to functions whose line range covers them
    line_risks: List[Tuple[int, str]] = field(default_factory=list)


def _blank_c_comments_and_strings(text: str) -> str:
    """Replace comments and string/char literals with spaces, keeping newlines
    so line numbers stay valid."""
    out: List[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            while i < n and text[i] != "\n":
                out.append(" "); i += 1
        elif c == "/" and nxt == "*":
            out.append("  "); i += 2
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                out.append("\n" if text[i] == "\n" else " "); i += 1
            out.append("  "); i += 2
        elif c in "\"'":
            quote = c
            out.append(" "); i += 1
            while i < n and text[i] != quote and text[i] != "\n":
                if text[i] == "\\" and i + 1 < n:
                    out.append(" "); i += 1
                out.append(" "); i += 1
            out.append(" "); i += 1
        else:
            out.append(c); i += 1
    return "".join(out)


_PP_DIRECTIVE = re.compile(r"^\s*#\s*(\w+)\s*(.*)$")
_LITERAL = re.compile(r"^\(?\s*\d+\s*\)?$")


def _splits_blocks(cleaned: str) -> bool:
    """True if some #if..#endif group has a branch whose braces are unbalanced. Groups whose
    condition is a numeric literal are excluded (the reader resolves those itself)."""
    stack: list = []          # frames: [literal, branch_deltas, current_delta]
    continued = False
    for line in cleaned.splitlines():
        if continued:                      # body of a multi-line directive (e.g. a #define): not code
            continued = line.rstrip().endswith("\\")
            continue
        m = _PP_DIRECTIVE.match(line)
        if m:
            continued = line.rstrip().endswith("\\")
            name, rest = m.group(1), m.group(2).strip()
            if name in ("if", "ifdef", "ifndef"):
                stack.append([name == "if" and bool(_LITERAL.match(rest)), [], 0])
            elif name in ("else", "elif") and stack:
                stack[-1][1].append(stack[-1][2])
                stack[-1][2] = 0
            elif name == "endif" and stack:
                literal, branches, current = stack.pop()
                branches.append(current)
                if not literal and any(delta != 0 for delta in branches):
                    return True
            continue
        if stack:
            stack[-1][2] += line.count("{") - line.count("}")
    return False


def scan_source(text: str, language: Language) -> LimitationScan:
    scan = LimitationScan()
    if language is Language.PYTHON:
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, MemoryError, RecursionError):
            return scan  # syntax problems are reported by file validation
        match_type = getattr(ast, "Match", None)
        if match_type is not None:
            for node in ast.walk(tree):
                if isinstance(node, match_type):
                    scan.line_risks.append((node.lineno, MSG_MATCH))
        return scan

    cleaned = _blank_c_comments_and_strings(text)
    has_func_macro = False
    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        if _PP_CONDITIONAL.match(line):
            scan.line_risks.append((lineno, MSG_CONDITIONAL))
        if _PP_FUNC_MACRO.match(line):
            has_func_macro = True
        if language is Language.CPP and _TEMPLATE.search(line):
            scan.line_risks.append((lineno, MSG_TEMPLATE))
    if has_func_macro:
        scan.file_warnings.append(MSG_FUNC_MACRO)
    if _splits_blocks(cleaned):
        scan.file_warnings.append(MSG_PP_SPLIT)
    return scan
