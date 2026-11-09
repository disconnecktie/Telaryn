"""Audit license metadata for pinned Python runtime requirements.

Runs after pip installs requirements-dev.txt. This inventory does not replace
reviewing the full upstream licenses, redistributed binary assets, or notices.
Do not print package metadata's arbitrary long-form License text.
"""
from __future__ import annotations

from collections import Counter
from importlib import metadata
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[A-Za-z0-9_,.-]+\])?==([A-Za-z0-9_.+!-]+)\s*$")


def requirements() -> list[tuple[str, str]]:
    result = []
    for raw in (ROOT / "requirements.txt").read_text(encoding="utf-8-sig").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = PIN.fullmatch(line)
        if not match:
            raise RuntimeError("Unrecognized non-pinned Python dependency entry")
        result.append(match.groups())
    return result


def declared_license(dist: metadata.Distribution) -> str:
    info = dist.metadata
    expression = (info.get("License-Expression") or "").strip()
    if expression:
        return expression
    legacy = (info.get("License") or "").strip()
    if legacy and len(legacy) < 100 and "\n" not in legacy:
        return legacy
    matches = [
        c.rsplit(" :: ", 1)[-1]
        for c in info.get_all("Classifier", [])
        if c.startswith("License ::")
    ]
    return ", ".join(matches) if matches else "Unspecified (manual review)"


def main() -> int:
    missing = []
    mismatched = []
    no_license = []
    exceptional = []
    license_counts = Counter()
    entries = requirements()
    for name, pinned in entries:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        if dist.version != pinned:
            mismatched.append(name)
        declared = declared_license(dist)
        license_counts[declared] += 1
        if "lgpl" in declared.lower() or "mpl" in declared.lower():
            exceptional.append((name, declared))
        if declared == "Unspecified (manual review)":
            no_license.append(name)

    print(f"Python runtime dependency license metadata: {len(entries)} exact pins inspected")
    for license_name, count in sorted(license_counts.items()):
        print(f"  {license_name[:90]}: {count} package(s)")
    if exceptional:
        print("Copyleft or file-level license review (package and metadata only):")
        for name, declared in exceptional:
            print(f"  {name}: {declared}")
    if no_license:
        print("Missing/unclassified license metadata (owner review required):")
        for name in sorted(no_license):
            print(f"  {name}")
    if missing or mismatched:
        print(f"Missing distributions: {len(missing)}; version mismatches: {len(mismatched)}")
        for name in missing + mismatched:
            print(f"  check required: {name}")
        return 1
    print("All Python runtime pins are installed at expected versions.")
    print("License metadata inventory only; not redistribution approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
