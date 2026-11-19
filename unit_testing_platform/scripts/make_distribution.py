"""Build the distributable ZIP of the application.

    python scripts/make_distribution.py [--out PATH]

Everything under the repository root is included EXCEPT development leftovers: virtual environments,
bytecode, test caches, VCS data, logs, local secrets and distribution ZIPs left in the root or in dist/. Archives that are
part of the application (the demo projects) are kept. Run
`python scripts/verify_distribution.py <zip>` afterwards.
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_DIRS = {"venv", ".venv", "env", "__pycache__", ".pytest_cache", ".git", ".idea", ".vscode", "dist", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}      # NOT .zip: the demo projects under sample_projects/ and tests/ are archives
EXCLUDED_NAMES = {"secrets.toml", ".DS_Store", ".env"}


def included(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in rel.parts[:-1]):
        return False
    if rel.parent == Path(".") and path.suffix == ".zip":      # a previously built distribution lying in the root
        return False
    return path.suffix not in EXCLUDED_SUFFIXES and path.name not in EXCLUDED_NAMES


def build(out: Path, top: str = "unit_testing_platform") -> int:
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and included(p))
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, f"{top}/{p.relative_to(ROOT).as_posix()}")
    return len(files)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "unit_testing_platform.zip")
    args = ap.parse_args()
    print(f"{build(args.out)} files written to {args.out}")
