# Third-party notices

This application contains third-party source code. The notices below must be kept with every
copy of the application that is distributed (source or binary). Facts here were checked against the
files in this repository (`third_party/lizard/`); nothing was added from memory.

## Lizard 1.24.3 (bundled, modified, trimmed copy)

| | |
|---|---|
| Location | `third_party/lizard/` |
| Project | Lizard, an extensible Cyclomatic Complexity Analyzer |
| Copyright | Copyright Terry Yin and other contributors |
| Version copied | 1.24.3 (PyPI source distribution `lizard-1.24.3.tar.gz`, SHA-256 `7d2570ca711288388de1cf0f25512e97fbbc5e189f551c87b4e20d11d028b297`, as recorded in `third_party/lizard/UPSTREAM_MANIFEST.json`) |
| Upstream | https://github.com/terryyin/lizard |
| Licence | MIT. The licence file shipped by upstream (`third_party/lizard/LICENSE.txt`) is reproduced below. |
| Additional licence text | `third_party/lizard/LICENSE-Apache-2.0.txt` (Apache License 2.0). The repository records that upstream's facade file `lizard.py` carries an Apache-2.0 header; that file is NOT part of this copy, and this statement was taken from the repository's own records, not re-verified against upstream in this review (no network access). The text is shipped to stay on the safe side. |
| Runtime dependencies of this code | none (Python standard library only; checked by a test) |
| Modifications | See `third_party/lizard/MODIFICATIONS.md`. Four files have changed import lines/trimmed registries and carry a change notice at the top; the other files are byte-identical to upstream (verified by `UPSTREAM_MANIFEST.json` and a test). |

### Application code that builds on Lizard

`core/complexity/reader.py` and `core/complexity/backend.py` are written for this application. They
subclass and call Lizard's C/C++ reader and token pipeline (imported from `third_party/lizard`) and
change how `&&`, lambdas and preprocessor directives are counted. Lizard itself is not modified by
them. They are listed here because they depend on, and are structured around, the Lizard code above.

### Lizard licence text (`third_party/lizard/LICENSE.txt`, verbatim)

```text
Copyright Terry Yin and other contributors

This software consists of voluntary contributions made by many
individuals. For exact contribution history, see the revision history.

The following license applies to all parts of this software except as
documented below:

====

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

====
```

The Apache License 2.0 text is in `third_party/lizard/LICENSE-Apache-2.0.txt`.

## Other dependencies

Python packages installed with `pip` (Streamlit, pandas, openpyxl, pytest and their dependencies) are
not bundled in this repository or in the ZIP. `LICENSES.md` lists what each of them ships (licence files read from the
installed packages, not only their metadata) and which statements could not be verified.
