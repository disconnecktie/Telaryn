"""Conservative checks for a prospective public Telaryn source snapshot.

This is a release guard, not a substitute for Gitleaks, manual review,
privacy review, or validating the provenance of third-party assets.
Findings report file paths and categories only, never matched values.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_ROOT_FILES = {
    ".dockerignore", ".gitattributes", ".gitignore", "Dockerfile",
    "LICENSE", "README.md", "SECURITY.md", "alembic.ini",
    "compose.yaml", "requirements-dev.txt", "requirements.txt",
}
ALLOWED_DOCS = {
    "docs/deployment-architecture.md",
    "docs/operations-overview.md",
    "docs/source-release-checklist.md",
}
ALLOWED_SCRIPTS = {"scripts/verify_source_snapshot.py"}
ALLOWED_WORKFLOWS = {".github/workflows/ci.yml"}
SOURCE_PREFIXES = ("app/", "frontend/", "alembic/", "tests/")

SENSITIVE_PATTERNS = {
    "private-personal-email": re.compile(
        r"[\\w.+-]+@(?:gmail|yahoo|outlook|icloud)\\.com", re.IGNORECASE
    ),
    "known-environment-resource": re.compile(
        r"(?:kvatlasproductionjay|rg-atlas-production)", re.IGNORECASE
    ),
    "private-key-material": re.compile(
        r"-----BEGIN (?:RSA |OPENSSH |EC |PRIVATE )?PRIVATE KEY-----"
    ),
    "credential-prefix": re.compile(
        r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|sk-proj-|AKIA)[A-Za-z0-9_-]{12,}"
    ),
}

# An identity-specific migration must be reviewed before publication.
IDENTITY_MIGRATION = "alembic/versions/a108b010c002_repair_production_bootstrap_owner.py"


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    )
    return sorted(x.decode("utf-8") for x in result.stdout.split(b"\\0") if x)


def acceptable_path(path: str) -> bool:
    if path in ALLOWED_ROOT_FILES or path in ALLOWED_DOCS:
        return True
    if path in ALLOWED_SCRIPTS or path in ALLOWED_WORKFLOWS:
        return True
    return path.startswith(SOURCE_PREFIXES)


def scan_snapshot(paths: list[str]) -> list[tuple[str, str]]:
    findings = []
    for path in paths:
        if not acceptable_path(path):
            findings.append((path, "outside explicit source boundary"))
            continue
        name = Path(path).name
        if name == ".env" or name.startswith(".env.") or name.endswith(".pem"):
            findings.append((path, "unapproved configuration/private key"))
            continue
        if path in ALLOWED_SCRIPTS:
            # Avoid matching this scanner's pattern definitions.
            continue
        try:
            content = (ROOT / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            if not path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")):
                findings.append((path, "unreviewed binary"))
            continue
        for name, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(content):
                findings.append((path, name))
    return findings


def history_has_personal_email() -> bool:
    result = subprocess.run(
        ["git", "log", "--format=%ae%n%ce"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    return any(
        re.search(r"@(?:gmail|yahoo|outlook|icloud)\\.com\\b", line, re.IGNORECASE)
        for line in result.stdout.splitlines()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--publication-gate", action="store_true",
        help="Also reject unresolved migration and Git history identity blockers",
    )
    args = parser.parse_args()
    paths = tracked_files()
    findings = scan_snapshot(paths)
    if args.publication_gate:
        if IDENTITY_MIGRATION in paths:
            findings.append((IDENTITY_MIGRATION, "mandatory migration review unresolved"))
        if history_has_personal_email():
            findings.append(("<Git history>", "personal commit email in retained history"))
    if findings:
        print(f"Release guard: {len(findings)} finding(s); no credential values shown")
        for path, category in findings:
            print(f"  {path}: {category}")
        return 1
    print(f"Release guard: {len(paths)} tracked files passed conservative checks")
    if not args.publication_gate:
        print("Note: publication gate, Gitleaks and independent review are still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
