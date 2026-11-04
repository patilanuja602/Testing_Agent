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
python -c "from core.complexity import ComplexityEngine; print(ComplexityEngine().version)"   # prints 1.0.0 (core 1.24.3)
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

The CCN (as defined by the bundled core, inherited unchanged from Lizard 1.24.3) is `1 + number of decision points`: `if`, `else if`/`elif`, `for`, `while` (also the `while`
of do-while), `case`, `catch`/`except`, `&&`/`||` (`and`/`or`), and `?`. `else` and `default` add nothing.
Constructs such as C++ lambdas and templates are convention-sensitive (see `tests/fixtures/expected.json`).
Imported Excel values follow **the originating tool's** convention and are never recalculated.

## Project layout

```
app.py                      Streamlit entry point: page title, navigation (2 pages), sidebar threshold
config.py                   defaults and upload limits (UTP_* env overrides)
core/                       threshold_manager, language_detector, limitations (parser-risk heuristics),
                            analyzer, result_normalizer
core/complexity/            Cyclomatic Complexity Module: ComplexityEngine (the only importer of third_party)
third_party/lizard/         bundled analysis core (third-party, licensed separately; see its README.md)
services/                   source_upload (safe ZIP staging), project_processor, excel_importer, report_generator
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

Last verified on 2026-11-04 on Ubuntu 24.04 in clean virtualenvs created from `requirements.txt`
(no `lizard`, no `pathspec`). The test-suite was run on Python 3.11, 3.12 and 3.13; the other checks on 3.13:

| Item | Result |
|---|---|
| Test-suite (real pytest, incl. Streamlit `AppTest` runs of the real UI) | 142 passed, 0 skipped on each of Python 3.11, 3.12, 3.13 |
| Threshold | Boundary tests at every level: a value equal to the threshold is flagged, one below is not. Dashboard (via the real UI), Excel summary, violations sheet and CSV agree for every threshold on a real analysis. Mutating `>=` to `>` makes 22 tests fail |
| Analysis engine, C and C++ | Output byte-identical to the previous release on 432 files / 5,906 functions (real-world C/C++ files, fixtures, sample project); bundled core vs original `lizard==1.24.3` identical on 433 files / 3,443 analyses / 47,213 functions; `third_party/` unchanged |
| Workflows | Single C and C++ uploads, ZIP projects, Excel import of the sample report, Excel and CSV exports: covered by automated tests |

Not verified: rendering in a real browser (Streamlit's headless `AppTest` and a server start-up check were used),
accuracy against *your* code base, and legal sign-off (see `LICENSES.md`).

## Known limitations

* The analysis core is a partial parser (inherited from Lizard): no C/C++ preprocessing or macro expansion, complexity hidden in macros is
  not counted, `#if/#else` branches are analysed together, complicated templates/lambdas/unusual syntax can be
  mis-detected. The app *warns* about these using text heuristics (can have false positives and cannot
  find every problem); a file without warnings is not guaranteed to be analysed correctly.
* `.h` files are treated as C (flagged); select C to include them.
* Only C and C++ can be analysed in this release. Python files are reported as unsupported and skipped.
* Files are analysed one after another (simple and predictable); very large projects take proportionally longer.
* Header detection assumes a single header row; two-row/merged headers need the manual header-row and mapping controls.
* Excel formulas without cached values read as empty; save the report once in Excel/LibreOffice first.
* Imported reports are only as reliable as the originating tool; different tools count differently.
* Results are held in the browser session; there is no analysis history (SQLite deferred).

## Still requires validation on your side

1. Run the app and click through every workflow once in your browser (upload each type, a few threshold values, Excel mapping, both exports).
2. Compare the results with your existing tool on a real embedded module, especially macro-heavy code,
   `#ifdef` blocks and C++ templates.
3. Check that the exported Excel/CSV open correctly in your company's Excel version.
4. Complete the licence review in `LICENSES.md` / `THIRD_PARTY_NOTICES.md`.
5. Measure analysis time on a representative large project before promising turnaround.

## Third-party code and licences

* `third_party/lizard/` is a **modified, trimmed copy of Lizard 1.24.3** (© Terry Yin and other contributors,
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
