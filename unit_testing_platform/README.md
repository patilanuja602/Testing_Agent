# Unit Testing Platform · Phase 1: Cyclomatic Complexity Analysis

A local-only application (Python + Streamlit) that analyses cyclomatic complexity of **C and C++**
code with a **built-in analysis core that runs inside the application**, imports existing
Excel complexity reports, applies a single complexity threshold and exports Excel/CSV reports.
Future platform features (test generation, execution, coverage…) are **not** part of this phase.

The analysis core is a trimmed, modified copy of the open-source *Lizard* analyzer 1.24.3
(MIT licence) kept in `third_party/lizard/`. It is third-party code, attributed as such: see
[Third-party code and licences](#third-party-code-and-licences). There is no separately installed
analysis package, no external service, and nothing is downloaded or sent anywhere at run time.

## Architecture

```
Unit Testing Platform (Streamlit UI: ui/, app.py)
   │  services/project_processor.py  → core/analyzer.py (per-file orchestration)
   ▼
Cyclomatic Complexity Module ........ core/complexity/   (ComplexityEngine adapter: our code)
   ▼
Locally integrated analysis core .... third_party/lizard/ (bundled source, stdlib only)
   ▼
Function-level results .............. models.analysis_result.FunctionResult / FileResult
   ▼
Result processing ................... core/result_normalizer.py (+ core/limitations.py warnings)
   ▼
Threshold management ................ core/threshold_manager.py  (complexity >= threshold, implemented once)
   ▼
Report generation / dashboard ....... services/report_generator.py, ui/dashboard.py
```

Only `core/complexity/engine.py` imports `third_party`. Everything else depends on the
`core.complexity` public surface (`ComplexityEngine`, `EngineUnavailableError`).

## Features (Phase 1)

* Upload single `.c/.h/.cpp/.cc/.cxx/.hpp/.hh/.hxx` files, several files, or a ZIP project
  (directory structure preserved, duplicate file names handled, unrelated files ignored and listed).
* Confirm which files to analyse, choose languages, run the built-in analysis core.
* Function table: file, function, start/end line, CCN, non-comment LOC, parameters, status,
  language, engine, analysis status — with search, sorting, and filters (language, file,
  status, complexity range) plus a per-function detail view.
* Threshold: one input in the sidebar (*Enter Complexity Threshold*, any positive integer, default **1**).
  The rule is fixed and not selectable: **complexity >= threshold → Exceeds Threshold**. It is implemented once in
  `core/threshold_manager.py` and used by source analysis, Excel import, the dashboard and both exports.
  With the default of 1 every function is flagged, because the lowest possible complexity is 1.
* Excel import (`.xlsx`): sheet selection, header-row detection, automatic column detection,
  manual mapping, validation, normalisation; original rows preserved.
* Reports: Excel (Summary, Function Details, Threshold Violations, Analysis Warnings,
  Skipped Files, Configuration, plus Imported Original Data for imports) and CSV.
* Warnings for constructs the analyzer handles unreliably (see *Known limitations*).

## Install and run (Ubuntu Linux, Python 3.10+)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
cd unit_testing_platform
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -c "from core.complexity import ComplexityEngine; print(ComplexityEngine().version)"   # prints 1.1.0 (core 1.24.3)
streamlit run app.py                                 # opens http://127.0.0.1:8501
```

The only things `pip` installs are Streamlit, pandas, openpyxl and pytest (and their dependencies);
the analysis core ships inside the repository. The app binds to `127.0.0.1` and Streamlit usage
statistics are disabled (`.streamlit/config.toml`). Nothing is sent over the network.

### Run the tests

```bash
source venv/bin/activate
pytest -q
```

With `requirements.txt` installed **nothing should be skipped**. Run `pytest -q -rs` to list skips.
`tests/test_complexity_integration.py` checks independence (no external analysis package, no network,
no child processes), equality with the original package's results, and licence/provenance guards.

### Try it

1. `sample_projects/embedded_demo.zip` → *Complexity Analysis* page. (Regenerate samples with `python scripts/make_samples.py`.)
2. `sample_reports/sample_complexity_report.xlsx` → *Excel Report Analysis* page (illustrative data; has title rows above the header and a "Notes" sheet).
3. `sample_reports/unmapped_headers_report.xlsx` → forces manual column mapping.
4. `sample_reports/no_complexity_column_report.xlsx` → shows the "no complexity values" explanation.

## Counting convention

CCN = `1 + number of decision points`. Decision points: `if` (also the `if` of `else if`), `for`, `while` (also the
`while` of do-while), `case`, `catch`, `||`, `?`, and `&&` **when it is a logical AND**. `else` and `default` add nothing.
The first six come unchanged from Lizard 1.24.3; the three rules below are this application's own
(`core/complexity/reader.py`), validated by `tests/test_counting_convention.py` and the GCC oracle test.

1. **`&&`**: only a logical AND counts. Rvalue/forwarding references (`T&& v`, `auto&& e`, `static_cast<T&&>(x)`,
   `void(int&&)`, `S(S&&)`, `int get() &&`, lambda parameters) do not. Each `&&` is classified from its token context; a
   `&&` is treated as a reference only on evidence that cannot be a logical AND, and anything ambiguous is counted
   (the established convention). The GNU label address `&&label` is not a decision. In C files there are no references.
   Fold expressions count one decision per `&&` written (`(a && ...)` is one, `(x && ... && y)` is two); `A&&... a` is a
   reference pack. `static_assert(A && B)` and `if constexpr` are counted like ordinary expressions.
2. **Lambdas (C++)**: a lambda body is its own entry, named `outer::(lambda at line N)`. Its decisions are *not* added to
   the enclosing function (which carries a note), the same treatment Lizard gives nested functions in other languages.
   Lambdas outside any function body (namespace/class-scope initialisers) and lambda-like constructs that cannot be
   read completely are reported as warnings, not guessed.
3. **Constructor initialiser lists (C++)**: decisions in `S() : a(x && y), b(c ? 1 : 0) {}` belong to the constructor. Upstream
   dropped them (the core restarts the count when the body begins); they are added back. A lambda written inside an
   initialiser list is attributed to the constructor (documented limitation).
4. **Preprocessor**: `#if/#ifdef/#ifndef/#elif/#else/#endif` are compile-time, not runtime decisions, and add **nothing**
   (upstream Lizard added +1 for `#if/#ifdef/#elif` but not for `#ifndef/#else`, which was inconsistent). Regions that are
   dead for every configuration (`#if 0`, the `#else` part of `#if 1`) are excluded. All other conditional branches
   are analysed **together** (union of all configurations), so the value can exceed the complexity of any single
   build, or lower than it when decisions hide in macro bodies; functions affected carry a warning. The result is *not* a per-configuration figure: see `docs/PREPROCESSOR_LIMITATIONS.md` for measured differences and how to obtain a per-configuration number.
   `ComplexityEngine`'s backend accepts `preprocessor="legacy"` to reproduce the original counting for comparison with
   reports produced by the original tool.

Imported Excel values follow **the originating tool's** convention and are never recalculated. If the originating tool
is Lizard, expect differences on functions with lambdas, `#if/#ifdef/#elif` lines, or `&&` references.

## Project layout

```
app.py                      Streamlit entry point: page title, navigation (2 pages), sidebar threshold
config.py                   defaults and upload limits (UTP_* env overrides)
core/                       threshold_manager, language_detector, limitations (parser-risk heuristics),
                            analyzer, result_normalizer
core/complexity/            Cyclomatic Complexity Module: ComplexityEngine, backend.py, reader.py (&&, lambdas, preprocessor); the only importer of third_party
third_party/lizard/         bundled analysis core (third-party, licensed separately; see its README.md)
services/                   source_upload (safe ZIP staging), header_resolver (.h language), project_processor, excel_importer, report_generator
models/analysis_result.py   dataclasses/enums shared by every layer
ui/                         dashboard (shared), complexity_analysis, excel_analysis, threshold (sidebar input)
tests/                      pytest suite; tests/fixtures/ + expected.json (hand-derived expectations)
sample_projects/ sample_reports/ scripts/ (incl. compare_with_upstream.py, a developer tool)
LICENSES.md  THIRD_PARTY_NOTICES.md
```

Adding a language later (e.g. Python, whose reader is already bundled but not enabled): follow the numbered
steps at the top of `core/language_detector.py` (extension map, supported list, engine list, fixtures). Replacing/adding an engine: implement the `AnalysisEngine` protocol in `core/analyzer.py`.
Supporting another language in the bundled core means copying that language's reader from the matching
upstream release into `third_party/lizard/lizard_languages/` and documenting it in `MODIFICATIONS.md`.

## Configuration

Environment variables (defaults): `UTP_MAX_UPLOAD_MB=200`, `UTP_MAX_EXTRACTED_MB=500`,
`UTP_MAX_ZIP_MEMBERS=20000`, `UTP_MAX_SOURCE_FILE_MB=5`, `UTP_MAX_ZIP_RATIO=200`, `UTP_MAX_EXCEL_MB=25`.
Streamlit's own cap: `server.maxUploadSize` in `.streamlit/config.toml`.

## Security and privacy design

Uploaded code is never executed or imported.
ZIPs: names sanitised (absolute paths, drive letters, `..`, NUL rejected), final path re-checked,
symlinks/encrypted/nested archives not extracted, only supported files extracted, sizes enforced
while streaming, entry-count/ratio/total-size limits. Files live in a private temp folder that is
deleted right after analysis (stale folders are purged at start-up). File contents are never logged;
error messages avoid workspace paths. CSV export neutralises spreadsheet formula injection.
SQLite is **not** used in Phase 1 (nothing required persistence).

## Verification

Executed in a Linux sandbox (Python 3.12.3, pytest 9.2.0, Streamlit 1.65.0, pandas 3.0.6, openpyxl 3.1.5, GCC 13).
**This is not your development machine.** Streamlit 1.65.0 was loaded from the pure-Python files of your shipped
`venv`; pyarrow (a compiled wheel for Python 3.10) could not be loaded there, so the pytest header reads
`UI table rendering: BYPASSED`: the UI tests ran against the real application script, but the call that renders a table
was replaced by a recorder (`tests/conftest.py`). Arrow serialisation and browser rendering were therefore **not** exercised.

```
export PYTHONPATH=<site-packages with streamlit>       # sandbox only; on your machine activate the venv
python -m pytest -p no:cacheprovider -rs -q            # 317 passed, 2 xfailed, 0 failed, 0 skipped (319 collected)
```

The 2 xfailed are documented inherited parser limitations (strict xfail: they fail the run if they ever start passing).
On a machine with pyarrow the pytest header reads `UI table rendering: REAL`; please run it there once.

| Item | Evidence |
|---|---|
| `&&` accuracy | 5 C/C++ fixtures compared with GCC's own parse (`-fdump-tree-original-raw`, `truth_andif_expr`): identical logical-AND counts; all 76 fixture functions with hand-derived expected values match (71 strict) |
| Convention tests | 115 hand-derived cases (`tests/test_counting_convention.py`): `&&`, references, folds, templates, lambdas, constructors, control flow, macros, preprocessor |
| Preprocessor configurations | `tests/test_preprocessor_configurations.py`: union analysis vs `gcc -E -P` per configuration (`docs/PREPROCESSOR_LIMITATIONS.md`) |
| Header resolution | 29 tests: duplicate names, nested/relative/angle includes, transitive includes, cycles, mixed C/C++ projects |
| UI / end to end | 14 tests: upload C project, analyse, threshold, range filter, inspect a function, export XLSX + CSV; ambiguous headers; language selection; failed file; warnings |
| Distribution | `scripts/make_distribution.py` + `scripts/verify_distribution.py --run-tests`: fresh extraction, required files, no venv/caches, imports resolve, licence check, full suite from the extracted copy |
| Licensing | `scripts/verify_licensing.py` (hashes vs manifest, notices, licence texts, dependency licence files read) |
| Real-world files (ad-hoc, not a test) | re-run after the final changes: 2,500 libstdc++/system headers analysed in C++ mode (7,182 functions upstream): no crash, no function lost, 790 extra entries (all lambdas), CCN lower in 913 functions and higher in 4 (macro-confused pseudo-functions, see limitations); ~20% slower than upstream (14.4 s vs 11.9 s) |

Not verified: rendering in a real browser, Arrow serialisation (see above), accuracy against *your* code base, legal sign-off.

## Known limitations

* The analysis core is a partial parser (inherited from Lizard): **no C/C++ preprocessing or macro expansion**, complexity hidden in
  macros is not counted, and `#if/#else` branches are analysed together (union, see *Counting convention*). A branch that splits a
  block (`#if A  if (x) {  #else  if (y) {  #endif`) can make the parser lose functions; this is detected heuristically and
  flagged, but the affected functions can still be missing. For a per-configuration figure, preprocess with your build flags
  outside the application (`gcc -E -DFLAGS...`) and analyse the result; this is not built in.
* `&&` classification is token-based, not a full C++ parser. Ambiguous cases are counted as logical AND. C++ alternative tokens
  (`and`, `or`) are not counted at all. Requires-clauses and `&&` inside template argument lists may be counted.
* Constructs the bundled parser does not handle (inherited): a trailing C++20 `requires` clause makes it report a function named
  `requires`; member functions of classes declared inside a function body are not extracted.
* Lambda extraction covers lambdas inside function bodies. Lambdas at namespace/class scope, and lambdas with `requires` clauses or
  other unreadable forms, are warned about, not extracted.
* Function-like macros such as `_GLIBCXX_VISIBILITY(default)` before a namespace can make the parser create a pseudo-function
  spanning a whole namespace (seen in libstdc++ headers); inherited from upstream.
* `.h` language is decided per project (header content, inclusion by C or C++ sources). When the evidence is missing or
  contradictory the header is shown as *ambiguous* and follows your language selection (C++ if only C++ is selected, otherwise C).
  A quoted include is resolved relative to the including file first (so `a/x.h` and `b/x.h` are told apart), otherwise by path
  suffix (compiler include paths are not known; several matches are all linked). Includes inside `#if` regions are not
  evaluated: an include in dead code still counts as evidence.
* Only C and C++ can be analysed in this release. Python files are reported as unsupported and skipped.
* Files are analysed one after another; very large projects take proportionally longer.
* Header detection assumes a single header row; two-row/merged headers need the manual header-row and mapping controls.
* Excel formulas without cached values read as empty; save the report once in Excel/LibreOffice first.
* Imported reports are only as reliable as the originating tool; different tools count differently.
* Results are held in the browser session; there is no analysis history (SQLite deferred).
* The range/status/search controls on the results table are **display filters**: the exported XLSX/CSV always contain every analysed
  function (with its threshold status), not only the filtered rows.

## Still requires validation on your side

1. Run the app and click through every workflow once in your browser (upload each type, a few threshold values, Excel mapping, both exports).
2. Compare the results with your existing tool on a real embedded module, especially macro-heavy code,
   `#ifdef` blocks and C++ templates.
3. Check that the exported Excel/CSV open correctly in your company's Excel version.
4. Complete the licence review in `LICENSES.md` / `THIRD_PARTY_NOTICES.md`.
5. Measure analysis time on a representative large project before promising turnaround.

## Third-party code and licences

* `third_party/lizard/` is a **trimmed copy of Lizard 1.24.3** (4 files with import/registry changes, the rest byte-identical) (© Terry Yin and other contributors,
  MIT licence; Apache-2.0 text also shipped because one upstream file carries that header). It is not original
  code of this project. Notices: `THIRD_PARTY_NOTICES.md`, `third_party/lizard/LICENSE.txt`,
  `third_party/lizard/LICENSE-Apache-2.0.txt`; every change: `third_party/lizard/MODIFICATIONS.md`.
* The application has no Settings page, so the notices are **not** displayed in the user interface; they are delivered as files with the
  application. Keep them with every copy you distribute (see the next point).
* Keep `THIRD_PARTY_NOTICES.md` and `third_party/` with every copy of the application you distribute.
* Dependency/licence register: `LICENSES.md`. Do not delete or edit the vendored licence files or the notice
  comments at the top of modified files.

### Updating or re-checking the bundled core

```bash
python3 -m venv /tmp/cmp-venv && /tmp/cmp-venv/bin/pip install lizard==1.24.3      # throw-away, developer only
/tmp/cmp-venv/bin/python scripts/compare_with_upstream.py [extra files or folders]   # must report 0 differences
```
After a deliberate change to a modified vendored file: document it in `MODIFICATIONS.md`, then run
`python scripts/update_vendor_manifest.py`.
