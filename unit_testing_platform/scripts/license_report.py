"""Generate a dependency + license table from the metadata of INSTALLED packages
(direct and transitive). Run inside the project's virtual environment:

    python scripts/license_report.py            # prints Markdown
    python scripts/license_report.py --write    # writes licenses_generated.md

Data comes from each package's own metadata (License-Expression / License /
Trove classifiers). It is evidence for your compliance review, not legal advice;
packages that declare nothing are shown as 'NOT DECLARED' and need manual review."""
from __future__ import annotations

import re
import sys
from importlib import metadata
from pathlib import Path

DIRECT = ["streamlit", "pandas", "openpyxl", "pytest"]


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def license_of(dist: metadata.Distribution) -> str:
    md = dist.metadata
    expr = md.get("License-Expression")
    if expr:
        return expr
    classifiers = [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return "; ".join(classifiers)
    text = (md.get("License") or "").strip()
    if text and len(text) < 80 and "\n" not in text:
        return text
    return "NOT DECLARED (see the package's license file)" if not text else "Custom/long text (see the package's license file)"


def requirements_of(dist: metadata.Distribution) -> list[str]:
    try:
        from packaging.requirements import Requirement
    except ImportError:                                   # packaging is nearly always present
        Requirement = None
    names = []
    for line in dist.requires or []:
        if Requirement is None:
            if "extra ==" in line:
                continue
            names.append(norm(re.split(r"[ ;<>=!~\[(]", line, maxsplit=1)[0]))
            continue
        req = Requirement(line)
        if req.marker is not None and not req.marker.evaluate({"extra": ""}):
            continue
        names.append(norm(req.name))
    return names


def main() -> int:
    seen: dict[str, metadata.Distribution] = {}
    direct = {norm(n) for n in DIRECT}
    missing: list[str] = []
    queue = [norm(n) for n in DIRECT]
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        seen[name] = dist
        queue.extend(requirements_of(dist))
    lines = ["| Package | Version | Type | License (as declared in package metadata) | Home page |",
             "|---|---|---|---|---|"]
    for name in sorted(seen):
        d = seen[name]
        home = d.metadata.get("Home-page") or next(
            (u.split(",", 1)[-1].strip() for u in d.metadata.get_all("Project-URL") or []), "")
        lines.append(f"| {d.metadata['Name']} | {d.version} | {'direct' if name in direct else 'transitive'} | {license_of(d)} | {home} |")
    if missing:
        lines += ["", "Not installed (not checked): " + ", ".join(sorted(missing))]
    text = "\n".join(lines) + "\n"
    if "--write" in sys.argv:
        Path(__file__).resolve().parent.parent.joinpath("licenses_generated.md").write_text(text, encoding="utf-8")
        print("Wrote licenses_generated.md")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
