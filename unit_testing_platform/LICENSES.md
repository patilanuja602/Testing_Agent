# Licence register

Evidence for the company's compliance review. **This is not legal advice and not a legal sign-off.**
Re-run the checks any time: `python scripts/verify_licensing.py --site-packages <venv>/lib/python3.X/site-packages`.

## 1. Code included in the distributable (the ZIP)

| Component | Version | Licence | Where | Notes |
|---|---|---|---|---|
| Lizard (Terry Yin and other contributors) | 1.24.3 | MIT (+ Apache-2.0 text shipped, see `THIRD_PARTY_NOTICES.md`) | `third_party/lizard/` | trimmed copy, 4 files with import/registry changes; notices required; no runtime dependencies |
| Application code | - | owned by the company (licence to be decided by the company) | everything else | `core/complexity/reader.py` and `backend.py` build on Lizard (see notices) |

The ZIP contains no other third-party code: no virtual environment, no wheels, no `node_modules`.
The analysis is integrated locally: nothing in the application imports the separately installable `lizard`,
`pygments` or `pathspec` packages (checked by tests).

### What was verified from the files, and how

| Check | Result |
|---|---|
| All 17 files of `third_party/lizard` hashed and compared with `UPSTREAM_MANIFEST.json` | all match the pinned hashes |
| 12 files marked "unmodified": current hash equals the *recorded* upstream hash | yes |
| The 4 files marked "modified" carry the modification notice; the unmodified ones do not | yes (4 of 4 modified files; none of the unmodified files) |
| Python files in the tree not covered by the manifest | none |
| `LICENSE.txt` has the copyright line "Copyright Terry Yin and other contributors" and the MIT text | yes |
| MIT permission, condition and warranty text of `LICENSE.txt` equals the MIT text in `pytest`'s licence file (whitespace-normalised) | identical |
| `LICENSE-Apache-2.0.txt` terms (up to "END OF TERMS AND CONDITIONS") equal the system reference `/usr/share/common-licenses/Apache-2.0` | identical; the file ends before the reference copy's boilerplate appendix, which is not part of the licence terms |
| `THIRD_PARTY_NOTICES.md` reproduces `LICENSE.txt` verbatim, names the copyright holder, version and sdist hash | yes |
| Copyright or licence headers inside the vendored `.py` files | none exist (search for copyright/licence/SPDX/Apache/MIT found only the project's own notices); the only upstream copyright notice is `LICENSE.txt` |

### NOT verified (cannot be verified offline, flagged for the reviewer)

* **Comparison with upstream.** The manifest records upstream SHA-256 values and the hash of the upstream source
  distribution, but no upstream file was available here. The "unmodified" claim therefore rests on the recorded
  hashes. To close this: download `lizard-1.24.3.tar.gz` from PyPI, check its SHA-256 against
  `UPSTREAM_MANIFEST.json`, and compare the 12 unmodified files byte for byte (`scripts/compare_with_upstream.py`
  automates part of this when the `lizard` package is installed).
* **The statement that upstream's facade file `lizard.py` carries an Apache-2.0 header.** It is in the repository's
  own records (`third_party/lizard/README.md`, `__init__.py`); `lizard.py` is not part of this copy and could not be
  inspected. The Apache text is shipped to be safe.
* **"... except as documented below"** in upstream's `LICENSE.txt`: the file as shipped documents no exceptions.
  Whether upstream documents any elsewhere was not checked.

## 2. Python dependencies (installed with `pip install -r requirements.txt`, NOT part of the ZIP)

The table lists what each installed package **actually ships**: the licence files found in its `.dist-info`
and the licence text recognised in them, next to what its metadata declares (46 packages reachable from
`requirements.txt`, read from the environment in the review sandbox: Streamlit 1.65.0, pandas 2.3.3, openpyxl 3.1.5, pytest 9.2.0).

| Package | Version | Declared in metadata | Licence file(s) shipped in the package | Licence text recognised in those files |
|---|---|---|---|---|
| altair | 6.2.2 | BSD License | LICENSE | BSD-2-Clause, BSD-3-Clause |
| anyio | 4.16.0 | MIT | LICENSE | MIT |
| attrs | 26.1.0 | MIT | LICENSE | MIT |
| certifi | 2026.10.23 | Mozilla Public License 2.0 (MPL 2.0) | LICENSE | MPL-2.0 (reference only) |
| charset-normalizer | 3.5.2 | MIT | LICENSE | MIT |
| click | 8.5.0 | BSD-3-Clause | LICENSE.txt | BSD-2-Clause, BSD-3-Clause |
| et_xmlfile | 2.0.0 | MIT License | LICENCE.python, LICENCE.rst | GPL/LGPL, ISC, MIT, PSF |
| exceptiongroup | 1.3.1 | MIT License | LICENSE | MIT, PSF |
| h11 | 0.16.0 | MIT License | LICENSE.txt | MIT |
| httptools | 0.9.0 | MIT | LICENSE, LICENSE-MIT | MIT |
| idna | 3.20 | BSD-3-Clause | LICENSE.md | BSD-2-Clause, BSD-3-Clause |
| iniconfig | 2.3.1 | MIT | LICENSE | MIT |
| itsdangerous | 2.2.0 | BSD License | LICENSE.txt | BSD-2-Clause, BSD-3-Clause |
| Jinja2 | 3.1.6 | BSD License | LICENSE.txt | BSD-2-Clause, BSD-3-Clause |
| jsonschema | 4.26.0 | MIT | COPYING | MIT |
| jsonschema-specifications | 2025.9.1 | MIT | COPYING | MIT |
| MarkupSafe | 3.0.4 | BSD-3-Clause | LICENSE.txt | BSD-2-Clause, BSD-3-Clause |
| narwhals | 2.28.0 | MIT | LICENSE.md | MIT |
| numpy | 2.2.6 | BSD License | LICENSE, LICENSE.md, LICENSE.txt | BSD-2-Clause, BSD-3-Clause, GPL/LGPL, MIT |
| openpyxl | 3.1.5 | MIT License | LICENCE.rst | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | LICENSE, LICENSE.APACHE, LICENSE.BSD | Apache-2.0, BSD-2-Clause |
| pandas | 2.3.3 | BSD License | LICENSE | Apache-2.0, Apache-2.0 (short notice only), BSD-2-Clause, BSD-3-Clause, GPL/LGPL, ISC, MIT, PSF |
| pillow | 12.3.0 | MIT-CMU | LICENSE | Apache-2.0, Apache-2.0 (short notice only), BSD-2-Clause, BSD-3-Clause, GPL/LGPL, MIT |
| pluggy | 1.7.0 | MIT License | LICENSE | MIT |
| protobuf | 7.36.2 | 3-Clause BSD License | LICENSE | BSD-2-Clause, BSD-3-Clause |
| pyarrow | 25.0.1 | Apache-2.0 | LICENSE.txt, NOTICE.txt | Apache-2.0, Apache-2.0 (short notice only), BSD-2-Clause, BSD-3-Clause, MIT, PSF, Unlicense/CC0 |
| pydeck | 0.9.3 | Apache License 2.0 | LICENSE.txt | Apache-2.0 (short notice only) |
| Pygments | 2.21.0 | BSD-2-Clause | LICENSE | BSD-2-Clause |
| pytest | 9.2.0 | MIT | LICENSE | MIT |
| python-dateutil | 3.0.0 | BSD License; Apache Software License | LICENSE | Apache-2.0 (short notice only), BSD-2-Clause, BSD-3-Clause |
| python-multipart | 0.0.32 | Apache-2.0 | LICENSE.txt | Apache-2.0, Apache-2.0 (short notice only) |
| pytz | 2026.6 | MIT License | LICENSE.txt | MIT |
| referencing | 0.37.0 | MIT | COPYING | MIT |
| requests | 2.34.2 | Apache Software License | LICENSE, NOTICE | Apache-2.0 |
| rpds-py | 0.30.0 | MIT | LICENSE | MIT |
| six | 1.17.0 | MIT License | LICENSE | MIT |
| starlette | 1.7.0 | BSD-3-Clause | LICENSE.md | BSD-2-Clause, BSD-3-Clause |
| streamlit | 1.65.0 | Apache-2.0 | **none** | **none recognised** |
| toml | 0.10.2 | MIT License | LICENSE | MIT |
| tomli | 2.5.0 | MIT | LICENSE | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 | LICENSE | GPL/LGPL, ISC, PSF |
| tzdata | 2026.6 | Apache-2.0 | LICENSE, LICENSE_APACHE | Apache-2.0, Apache-2.0 (short notice only) |
| urllib3 | 2.8.0 | MIT | LICENSE.txt | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause | LICENSE.md | BSD-2-Clause, BSD-3-Clause |
| watchdog | 6.0.0 | Apache Software License | COPYING, LICENSE | Apache-2.0, Apache-2.0 (short notice only) |
| websockets | 16.1.1 | BSD-3-Clause | LICENSE | BSD-2-Clause, BSD-3-Clause |

Findings from reading the files:

* **Streamlit 1.65.0 ships no licence file** in its installed package; Apache-2.0 appears only in its metadata.
  If the company ever redistributes Streamlit (for example inside an installer), obtain the licence text from
  the upstream repository for that exact version. The same applies to its bundled front-end assets.
* **pydeck** and **certifi** ship only a short notice (Apache-2.0 header; a reference to the Mozilla Public
  License 2.0), not the full licence text. certifi's data file (CA certificates) is MPL-2.0.
* `packaging` offers two licences (`LICENSE.APACHE`, `LICENSE.BSD`); both files are present.
* `numpy`, `pandas`, `pillow` and `pyarrow` ship licence files that also contain the texts of the third-party
  components they bundle; if any of them is redistributed, ship the complete files, not a summary.
* `pytest`, `pluggy`, `iniconfig`, `tomli`, `exceptiongroup` are test-only.
* If the application is ever distributed together with a virtual environment, the licence files of every
  package in it must be shipped. Do not distribute the `venv/` folder; create it on the target machine.
