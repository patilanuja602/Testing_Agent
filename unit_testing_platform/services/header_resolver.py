"""Language resolution for ambiguous header files (``.h``).

A ``.h`` file can be C or C++. The extension alone says nothing, so assuming C (as the first
release did) silently drops C++ headers when the user selects "C++" only, and assuming C++
would mis-label plain C headers. This module decides per file, from evidence in the uploaded
project, and says plainly when it cannot:

1. Content: C++-only syntax inside the header (``class X {``, ``template <``, ``namespace x {``,
   ``std::``, ``nullptr``, ``constexpr``, casts like ``static_cast<``, access specifiers, ``::`` ...).
   ``extern "C"`` and ``#ifdef __cplusplus`` guards are NOT evidence (they occur in C headers).
2. Inclusion: which source files include the header, directly or through other headers.
   A quoted include is resolved relative to the including file's directory first (so
   ``a/x.h`` and ``b/x.h`` are told apart); otherwise it is matched as a path suffix. Included only by C++ sources -> C++;
   only by C sources -> C.
3. Otherwise (no evidence, or included from both C and C++): the header is AMBIGUOUS. It is offered
   for analysis whenever C or C++ is selected and analysed as C++ if C++ alone is selected,
   otherwise as C. The user's language selection is the explicit tie-breaker.

Nothing here executes code; files are only read as text.
"""
from __future__ import annotations

import posixpath
import re
from typing import Dict, List, Set

from core.limitations import _blank_c_comments_and_strings
from models.analysis_result import Language, StagedFile

_CPP_SIGNALS = re.compile(r"""
    \bclass\s+\w+\s*(?:final\s*)?[:{]
  | \bnamespace\s*\w*\s*\{
  | \btemplate\s*<
  | \busing\s+(?:namespace\s+\w|\w+\s*=)
  | \b(?:public|private|protected)\s*:(?!:)
  | \b(?:static|reinterpret|dynamic|const)_cast\s*<
  | \b(?:nullptr|constexpr|noexcept|decltype)\b
  | \b(?:virtual|override)\b
  | \bstd\s*::
  | \b[A-Za-z_]\w*\s*::\s*[A-Za-z_~]
  | \boperator\s*(?:[^\w\s(]|new\b|delete\b)
  | =\s*(?:default|delete)\s*;
""", re.X)
_INCLUDE = re.compile(r'^\s*#\s*include\s*(?:"([^"\n]+)"|<([^>\n]+)>)', re.M)
_COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)
_HEADER_NOTE = "Header file (.h)"


def _read(file: StagedFile) -> str:
    try:
        return file.disk_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _code_without_directives(text: str) -> str:
    cleaned = _blank_c_comments_and_strings(text)
    out, continued = [], False
    for line in cleaned.splitlines():
        if continued or line.lstrip().startswith("#"):
            continued = line.rstrip().endswith("\\")
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


def has_cpp_constructs(text: str) -> bool:
    return bool(_CPP_SIGNALS.search(_code_without_directives(text)))


def _norm(path: str) -> str:
    """Lower-cased POSIX path without './' and 'dir/..' segments (leading '..' is kept)."""
    return posixpath.normpath(path.replace("\\", "/")).lower()


def _targets(include: str, quoted: bool, includer: StagedFile, headers: List[StagedFile]) -> List[StagedFile]:
    """Staged headers an ``#include`` may refer to.

    A quoted include is first resolved the way compilers do: relative to the directory of the
    including file. If that names a staged header, it is the only target (so two headers with the
    same name in different directories are told apart). Otherwise the include path is matched as a
    path suffix against all staged headers (the project's include directories are not known); if
    several match, all of them are targets, which keeps the evidence conservative."""
    inc = _norm(include)
    by_path = {_norm(h.display_path): h for h in headers}
    if quoted:
        local = _norm(posixpath.join(posixpath.dirname(includer.display_path), include.replace("\\", "/")))
        if local in by_path:
            return [by_path[local]]
    inc = inc.lstrip("/")
    while inc.startswith("../"):          # cannot be resolved against an unknown include directory
        inc = inc[3:]
    return [h for shown, h in by_path.items() if shown == inc or shown.endswith("/" + inc)]


def resolve_headers(files: List[StagedFile]) -> None:
    """Set ``language`` / ``header_ambiguous`` / ``language_basis`` / warnings on every ``.h``."""
    headers = [f for f in files if f.disk_path.suffix.lower() == ".h"]
    if not headers:
        return
    texts: Dict[str, str] = {}
    graph: Dict[str, List[StagedFile]] = {}
    for f in files:
        text = _read(f)
        texts[f.display_path] = text
        stripped = _COMMENTS.sub(" ", text)
        graph[f.display_path] = [t for quoted, angle in _INCLUDE.findall(stripped)
                                 for t in _targets(quoted or angle, bool(quoted), f, headers)]

    includers: Dict[str, Set[Language]] = {h.display_path: set() for h in headers}
    for src in files:
        if src.disk_path.suffix.lower() == ".h":
            continue
        seen: Set[str] = set()
        stack = list(graph[src.display_path])
        while stack:
            h = stack.pop()
            if h.display_path in seen:
                continue
            seen.add(h.display_path)
            includers[h.display_path].add(src.language)
            stack.extend(graph.get(h.display_path, []))

    for h in headers:
        langs = includers[h.display_path]
        ambiguous = False
        if has_cpp_constructs(texts[h.display_path]):
            language, basis = Language.CPP, "C++ constructs found in the header"
        elif langs == {Language.CPP}:
            language, basis = Language.CPP, "included only by C++ source files"
        elif langs == {Language.C}:
            language, basis = Language.C, "included only by C source files"
        elif langs:
            language, basis, ambiguous = Language.C, "included by both C and C++ source files", True
        else:
            language, basis, ambiguous = (Language.C, "no C++-specific constructs and no including source "
                                                      "file in this upload", True)
        h.language, h.header_ambiguous, h.language_basis = language, ambiguous, basis
        h.warnings = [w for w in h.warnings if not w.startswith(_HEADER_NOTE)]
        if ambiguous:
            h.warnings.append(f"{_HEADER_NOTE}: language could not be determined ({basis}); analysed as C++ if "
                              f"C++ alone is selected, otherwise as C")
        else:
            h.warnings.append(f"{_HEADER_NOTE}: analysed as {language.value} ({basis})")
