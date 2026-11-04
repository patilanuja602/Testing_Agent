"""Refresh the 'sha256' fields in third_party/lizard/UPSTREAM_MANIFEST.json after a DELIBERATE
change to a modified/new vendored file. Unmodified files are never refreshed: if one of them
differs from upstream, restore it instead. Always update third_party/lizard/MODIFICATIONS.md too.

    python scripts/update_vendor_manifest.py
"""
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "third_party" / "lizard"
manifest_path = BASE / "UPSTREAM_MANIFEST.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
bad = 0
for rel, info in manifest["files"].items():
    digest = hashlib.sha256((BASE / rel).read_bytes()).hexdigest()
    if info["status"] == "unmodified":
        if digest != info["upstream_sha256"]:
            print(f"NOT refreshed (must stay identical to upstream): {rel}")
            bad += 1
    elif digest != info["sha256"]:
        print(f"refreshed: {rel}")
        info["sha256"] = digest
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
sys.exit(1 if bad else 0)
