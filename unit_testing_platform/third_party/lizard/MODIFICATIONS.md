# Modifications relative to upstream Lizard 1.24.3

Upstream licence terms ask that modified files are marked as such. Every modified file below
starts with a `NOTE (Unit Testing Platform): this file was MODIFIED ...` comment.
**No counting or parsing logic was changed.** Compare against upstream with
`scripts/compare_with_upstream.py`.

## Files copied byte-for-byte (12)

`LICENSE.txt`, `lizard_core/__init__.py`, `lizard_core/function_info.py`,
`lizard_languages/{code_reader,token_pattern,clike,clike_states,python,python_structure,python_tokens,script_language}.py`,
`lizard_ext/auto_open.py`.

## Files modified (4)

| File | Change | Why |
|---|---|---|
| `lizard_core/file_analyzer.py` | 4 import lines: `from lizard_languages import ...` / `from lizard_ext import ...` / `from lizard_core.function_info import ...` / `from lizard_core.file_info_builder import ...` became relative imports (`from ..lizard_languages import ...`, `from ..lizard_ext import ...`, `from .function_info import ...`, `from .file_info_builder import ...`). Notice comment added at the top. | Upstream installs three top-level packages (`lizard_core`, `lizard_languages`, `lizard_ext`). Inside this repository they live under `third_party/lizard/`, and relative imports avoid any clash with a separately installed `lizard` and avoid `sys.path` manipulation. |
| `lizard_core/file_info_builder.py` | 1 import line: `from lizard_core.function_info import ...` became `from .function_info import ...`. Notice comment added. | same |
| `lizard_languages/__init__.py` | The upstream file imports 27 language readers and lists them in `languages()`. Reduced to the two this application uses: `CLikeReader` (C/C++) and `PythonReader`, **in upstream's relative order**. `get_reader_for` is unchanged. Notice comment added. | Removes the 25 unused readers, and with them the `pygments` dependency of the Erlang reader. |
| `lizard_ext/__init__.py` | Upstream also exports `print_xml`, `print_csv`, `html_output`, `print_checkstyle`, `version` and imports the writer modules. Reduced to `from .auto_open import auto_open, auto_read`. Notice comment added. | Command-line output features are not used here. |

## File added (1)

`__init__.py` (written for this project, not upstream code) defines `analyze_file` as
`FileAnalyzer([preprocessing, comment_counter, line_counter, token_counter, condition_counter])`,
which is exactly what upstream builds in `lizard_core/extensions.py` (`get_extensions([])`) and
`lizard_core/analysis.py` (`analyze_file = FileAnalyzer(get_extensions([]))`) for its default
configuration. It also exposes `UPSTREAM_VERSION`.

## Behavioural consequences

* **Complexity results: none.** Verified identical to the original package (see "Verification" in the repository `README.md`).
* **Reader selection:** with the 27-reader registry, upstream matched files by extension in list order and fell
  back to the C/C++ reader (`get_reader_for(filename) or CLikeReader`). For the extensions this application
  accepts (`.c .h .cpp .cc .cxx .hpp .hh .hxx .py`) the result is the same; `.hxx` has no reader of its own and
  uses the fallback in both cases (checked by a test).
* **Other languages** (Java, JavaScript, ...) are not analysable by this copy. The application never sent
  them to the analyser.
* Upstream behaviour kept as is: diagnostics for unreadable files are written to stderr; invalid UTF-8 is decoded
  with `errors="ignore"`; no C/C++ preprocessing or macro expansion.
