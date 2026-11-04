# Bundled analysis core: Lizard 1.24.3 (trimmed copy)

This directory contains **third-party code**, not code written by this project.

| | |
|---|---|
| Project | Lizard, "an extensible Cyclomatic Complexity Analyzer" |
| Authors | Terry Yin and other contributors |
| Version copied | **1.24.3** (PyPI release) |
| Upstream | https://github.com/terryyin/lizard · https://pypi.org/project/lizard/1.24.3/ |
| Obtained from | the PyPI source distribution `lizard-1.24.3.tar.gz` (SHA-256 `7d2570ca711288388de1cf0f25512e97fbbc5e189f551c87b4e20d11d028b297`) |
| Licence | MIT (`LICENSE.txt`, verbatim from upstream). The upstream facade file `lizard.py` additionally carries an Apache-2.0 header, so the Apache-2.0 text is shipped as well (`LICENSE-Apache-2.0.txt`). |
| Runtime dependencies | **none** (Python standard library only) |
| Languages enabled by the application | C and C++ (the bundled Python reader is dormant) |

## What is here

Only the part of Lizard that analyses **C, C++ and Python** source files for function-level
cyclomatic complexity (CCN), NLOC, token count, parameter count and line range:

```
__init__.py              NEW (this project): assembles `analyze_file`; exposes UPSTREAM_VERSION
lizard_core/             file_analyzer, file_info_builder, function_info   (upstream, see MODIFICATIONS.md)
lizard_languages/        code_reader, token_pattern, clike, clike_states,
                         python, python_structure, python_tokens, script_language, __init__ (trimmed)
lizard_ext/              auto_open (file reading with BOM handling), __init__ (trimmed)
LICENSE.txt              upstream MIT licence + copyright notice (verbatim)
LICENSE-Apache-2.0.txt   Apache-2.0 text (see "Licence" above)
MODIFICATIONS.md         every difference from upstream
UPSTREAM_MANIFEST.json   SHA-256 of each file in upstream and as shipped (checked by the test-suite)
```

Not copied (not needed for C/C++/Python function analysis, and some would pull in extra
dependencies): the other 25 language readers (`pygments` is needed only by the Erlang reader),
gitignore-aware file discovery (`pathspec`), the command-line interface, the XML/CSV/HTML/Checkstyle
output writers, the optional metric extensions (`-E...`), the multi-process runner, and upstream's tests.

## How the application uses it

Only `core/complexity/engine.py` imports this package. Nothing else in the application knows
about it. The package never starts a process, opens a socket or downloads anything.

## Keeping it honest

* `tests/test_complexity_integration.py` fails if an unmodified file stops being byte-identical to
  upstream, if a modified file changes without review, or if a required notice goes missing.
* `scripts/compare_with_upstream.py` (developer tool; needs `pip install lizard==1.24.3` in a throw-away
  virtualenv) re-proves that this copy and the original package give identical results.
* To update to a newer upstream release: re-copy the files, re-apply `MODIFICATIONS.md`, re-run the
  comparison script and the test-suite, and update `THIRD_PARTY_NOTICES.md`.
