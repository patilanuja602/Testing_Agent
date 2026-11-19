"""Licence verification from the ACTUAL files (not from package metadata alone).

    python scripts/verify_licensing.py [--site-packages PATH] [--json]

Checks
  1. third_party/lizard: every file's SHA-256 against UPSTREAM_MANIFEST.json, the 'modified' files carry the
     modification notice, the 'unmodified' files do not, LICENSE.txt has the copyright line and the MIT text,
     LICENSE-Apache-2.0.txt has the Apache-2.0 terms (compared with the system copy when one exists).
  2. THIRD_PARTY_NOTICES.md / LICENSES.md contain what the vendored tree requires (copyright holder, version,
     both licence texts referenced, MIT text reproduced verbatim).
  3. Dependencies (when --site-packages is given): for every distribution reachable from requirements.txt the
     licence FILES shipped in its dist-info are read; the licence family is recognised from the text and compared
     with the licence the package metadata declares. Distributions without any licence file are listed.

Exit status 1 if a check in 1 or 2 fails. Section 3 reports; it needs a human to decide (it prints UNRESOLVED items).
It does not contact any server. It cannot compare Lizard with upstream (no network): that comparison needs the
upstream source distribution named in UPSTREAM_MANIFEST.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIZ = ROOT / "third_party" / "lizard"
NOTICE = "NOTE (Unit Testing Platform)"

FAMILIES = [  # (name, regex on the licence text)
    ("Apache-2.0", r"Apache License\s+Version 2\.0"),
    ("Apache-2.0 (short notice only)", r"Licensed under the Apache License,\s+Version 2\.0"),
    ("MPL-2.0 (reference only)", r"Mozilla Public License,?\s+(?:Version|v\.?)\s?2\.0"),
    ("GPL/LGPL", r"GNU (?:LESSER |LIBRARY )?GENERAL PUBLIC LICENSE"),
    ("BSD-3-Clause", r"Redistribution and use in source and binary forms.*?Neither the name"),
    ("BSD-2-Clause", r"Redistribution and use in source and binary forms"),
    ("MIT", r"Permission is hereby granted, free of charge"),
    ("ISC", r"Permission to use, copy, modify, and/or distribute this software for any"),
    ("PSF", r"PYTHON SOFTWARE FOUNDATION"),
    ("MIT-CMU", r"Permission to use, copy, modify, and distribute this software and its documentation for any purpose"),
    ("Unlicense/CC0", r"(?:This is free and unencumbered software|CC0 1\.0)"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def check_vendored() -> list:
    problems = []
    manifest = json.loads((LIZ / "UPSTREAM_MANIFEST.json").read_text(encoding="utf-8"))
    listed = manifest["files"]
    for rel, info in sorted(listed.items()):
        path = LIZ / rel
        if not path.exists():
            problems.append(f"missing file listed in the manifest: {rel}")
            continue
        if sha256(path) != info["sha256"]:
            problems.append(f"{rel}: content differs from its pinned hash (changed without updating manifest/MODIFICATIONS.md)")
        has_notice = NOTICE in path.read_text(encoding="utf-8", errors="replace") if path.suffix == ".py" else None
        if info["status"] == "modified" and has_notice is False:
            problems.append(f"{rel}: modified file without the modification notice")
        if info["status"] == "unmodified":
            if sha256(path) != info["upstream_sha256"]:
                problems.append(f"{rel}: marked unmodified but differs from the recorded upstream hash")
            if has_notice:
                problems.append(f"{rel}: marked unmodified but carries a modification notice")
    on_disk = {str(p.relative_to(LIZ)).replace("\\", "/") for p in LIZ.rglob("*.py") if "__pycache__" not in p.parts}
    for extra in sorted(on_disk - set(listed)):
        problems.append(f"python file not covered by the manifest: {extra}")
    lic = (LIZ / "LICENSE.txt").read_text(encoding="utf-8")
    if "Copyright Terry Yin and other contributors" not in lic:
        problems.append("LICENSE.txt: copyright line missing")
    if not re.search(r"Permission is hereby granted, free of charge.*?DEALINGS\s+IN\s+THE\s+SOFTWARE\.", lic, re.S):
        problems.append("LICENSE.txt: MIT text missing or altered")
    apache = (LIZ / "LICENSE-Apache-2.0.txt").read_text(encoding="utf-8")
    ref = Path("/usr/share/common-licenses/Apache-2.0")
    if "END OF TERMS AND CONDITIONS" not in apache:
        problems.append("LICENSE-Apache-2.0.txt: terms incomplete")
    elif ref.exists():
        terms = lambda t: norm(t.split("END OF TERMS AND CONDITIONS")[0])
        if terms(apache) != terms(ref.read_text(encoding="utf-8")):
            problems.append("LICENSE-Apache-2.0.txt: terms differ from the system reference copy")
    return problems


def check_notices() -> list:
    problems = []
    notices = (ROOT / "THIRD_PARTY_NOTICES.md")
    register = (ROOT / "LICENSES.md")
    for f in (notices, register):
        if not f.exists():
            problems.append(f"missing: {f.name}")
    if problems:
        return problems
    text, reg = notices.read_text(encoding="utf-8"), register.read_text(encoding="utf-8")
    lic = (LIZ / "LICENSE.txt").read_text(encoding="utf-8").strip()
    manifest = json.loads((LIZ / "UPSTREAM_MANIFEST.json").read_text(encoding="utf-8"))
    for needle in ("Copyright Terry Yin and other contributors", "1.24.3", "MIT", "Apache", manifest["upstream"]["sdist_sha256"]):
        if needle not in text:
            problems.append(f"THIRD_PARTY_NOTICES.md lacks: {needle}")
    if norm(lic) not in norm(text):
        problems.append("THIRD_PARTY_NOTICES.md does not reproduce LICENSE.txt verbatim")
    modified = [k for k, v in manifest["files"].items() if v["status"] == "modified"]
    if f"Four files" in text and len(modified) != 4:
        problems.append(f"THIRD_PARTY_NOTICES.md says four modified files, manifest lists {len(modified)}")
    for needle in ("Lizard", "MIT"):
        if needle not in reg:
            problems.append(f"LICENSES.md lacks: {needle}")
    return problems


def requirement_names(path: Path) -> list:
    names = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line and not line.startswith("-"):
            names.append(re.split(r"[<>=!~\[; ]", line, 1)[0])
    return names


def canon(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def closure(roots: list, dists: dict) -> set:
    seen, todo = set(), [canon(r) for r in roots]
    while todo:
        n = todo.pop()
        if n in seen or n not in dists:
            continue
        seen.add(n)
        for req in dists[n].requires or []:
            if "extra ==" in req:
                continue
            todo.append(canon(re.split(r"[<>=!~\[; (]", req, 1)[0]))
    return seen


def license_files(dist) -> list:
    out = []
    for f in dist.files or []:
        low = f.name.lower()
        if any(k in low for k in ("licen", "copying", "notice", "copyright")) and f.suffix.lower() not in (".py", ".pyc", ".json", ".js", ".so", ".pyd"):
            path = Path(dist.locate_file(f))
            if path.is_file():
                out.append(path)
    return out


def classify(text: str) -> set:
    return {name for name, rx in FAMILIES if re.search(rx, text, re.S | re.I)}


def declared(dist) -> str:
    md = dist.metadata
    expr = md.get("License-Expression")
    if expr:
        return expr
    classifiers = [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    lic = (md.get("License") or "").strip()
    return "; ".join(classifiers) or (lic.splitlines()[0][:60] if lic else "(not declared)")


def check_dependencies(site: Path) -> list:
    dists = {canon(d.metadata["Name"]): d for d in metadata.distributions(path=[str(site)])}
    names = closure(requirement_names(ROOT / "requirements.txt"), dists)
    rows = []
    for n in sorted(names):
        d = dists[n]
        files = license_files(d)
        found = set()
        for f in files:
            found |= classify(f.read_text(encoding="utf-8", errors="replace"))
        rows.append({"package": d.metadata["Name"], "version": d.version, "declared": declared(d),
                     "license_files": [f.name for f in files], "recognised_in_files": sorted(found),
                     "copyright": sorted({m.strip() for f in files for m in re.findall(r"^\s*Copyright[^\n]{0,120}", f.read_text(encoding="utf-8", errors="replace"), re.M | re.I)})[:3]})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-packages", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true", help="print only the dependency table as Markdown")
    args = ap.parse_args()
    vend, notices = check_vendored(), check_notices()
    deps = check_dependencies(args.site_packages) if args.site_packages else None
    unresolved = [r for r in deps if not r["license_files"] or not r["recognised_in_files"]] if deps else []
    if args.markdown:
        print("| Package | Version | Declared in metadata | Licence file(s) shipped in the package | Licence text recognised in those files |")
        print("|---|---|---|---|---|")
        for r in deps or []:
            files = ", ".join(sorted(set(r["license_files"]))) or "**none**"
            print(f"| {r['package']} | {r['version']} | {r['declared']} | {files} | {', '.join(r['recognised_in_files']) or '**none recognised**'} |")
        return 0
    if args.json:
        print(json.dumps({"vendored": vend, "notices": notices, "dependencies": deps}, indent=1))
    else:
        print("1. vendored Lizard tree:", "OK" if not vend else "")
        [print("   FAIL", p) for p in vend]
        print("2. notices / register:", "OK" if not notices else "")
        [print("   FAIL", p) for p in notices]
        if deps is not None:
            print(f"3. dependencies ({len(deps)}): licence files read from the installed packages")
            for r in deps:
                flag = "" if r["license_files"] and r["recognised_in_files"] else "   <-- UNRESOLVED"
                print(f"   {r['package']} {r['version']}: declared [{r['declared']}] files {r['license_files']} "
                      f"text says {r['recognised_in_files']}{flag}")
    return 1 if vend or notices else 0


if __name__ == "__main__":
    sys.exit(main())
