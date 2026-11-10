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
    "LICENSE", "README.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md", "alembic.ini",
    "compose.yaml", "requirements-dev.txt", "requirements.txt",
}
ALLOWED_DOCS = {
    "docs/deployment-architecture.md",
    "docs/operations-overview.md",
    "docs/source-release-checklist.md",
}
ALLOWED_SCRIPTS = {"scripts/verify_source_snapshot.py", "scripts/audit_release_assets.py", "scripts/audit_python_licenses.py"}
ALLOWED_WORKFLOWS = {".github/workflows/ci.yml", ".github/workflows/private-history-secret-audit.yml"}
SOURCE_PREFIXES = ("app/", "frontend/", "alembic/", "tests/")

SENSITIVE_PATTERNS = {
    "private-personal-email": re.compile(
        r"[\w.+-]+@(?:gmail|yahoo|outlook|icloud)\.com", re.IGNORECASE
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
    return sorted(x.decode("utf-8") for x in result.stdout.split(b"\0") if x)


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



# These two review-only files existed in earlier private candidate commits and
# were subsequently removed. They are safe path exceptions, not release inputs.
RETIRED_REVIEW_PATHS = {
    "docs/clean-history-publication-plan.md",
    "scripts/prepare_clean_release.py",
}


def scan_reachable_history() -> tuple[list[tuple[str, str]], int, int]:
    """Inspect reachable commit trees and their unique text blobs without outputting values."""
    commits = subprocess.run(
        ["git", "rev-list", "--all"], cwd=ROOT, capture_output=True,
        text=True, check=True,
    ).stdout.splitlines()
    inspected_blobs: set[str] = set()
    findings: set[tuple[str, str]] = set()
    for revision in commits:
        tree = subprocess.run(
            ["git", "ls-tree", "-rz", revision], cwd=ROOT,
            capture_output=True, check=True,
        ).stdout
        for raw_entry in tree.split(b"\0"):
            if not raw_entry:
                continue
            metadata, raw_path = raw_entry.split(b"\t", 1)
            fields = metadata.decode("ascii").split()
            if len(fields) != 3 or fields[1] != "blob":
                continue
            blob_sha = fields[2]
            path = raw_path.decode("utf-8")
            if not acceptable_path(path) and path not in RETIRED_REVIEW_PATHS:
                findings.add((path, "historical file outside reviewed source boundary"))
            if blob_sha in inspected_blobs:
                continue
            inspected_blobs.add(blob_sha)
            if path in ALLOWED_SCRIPTS or path == "scripts/prepare_clean_release.py":
                # Scanner code contains literal detection patterns. A separate
                # Gitleaks scan must still inspect these scripts and history.
                continue
            if path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")):
                continue
            content = subprocess.run(
                ["git", "cat-file", "blob", blob_sha], cwd=ROOT,
                capture_output=True, check=True,
            ).stdout
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                findings.add((path, "historical non-UTF8 nonimage file"))
                continue
            for category, expression in SENSITIVE_PATTERNS.items():
                if expression.search(text_content):
                    findings.add((path, "historical " + category))
    return sorted(findings), len(commits), len(inspected_blobs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--publication-gate", action="store_true",
        help="Refuse publication until migration checks and explicit owner sign-off are recorded",
    )
    parser.add_argument(
        "--history-audit", action="store_true",
        help="Scan all reachable commit trees for excluded paths and known private identifiers",
    )
    args = parser.parse_args()
    paths = tracked_files()
    findings = scan_snapshot(paths)
    if args.history_audit or args.publication_gate:
        history_findings, commits, blobs = scan_reachable_history()
        findings.extend(history_findings)
        print(f"History audit inspected {commits} commits and {blobs} unique blobs")
    if args.publication_gate:
        if IDENTITY_MIGRATION in paths:
            migration = (ROOT / IDENTITY_MIGRATION).read_text(encoding="utf-8")
            # The public candidate may retain the migration revision identifier,
            # but must not hard-code a privileged operator identity or silently
            # rewrite placeholder accounts without opt-in.
            if (
                "PRODUCTION_ADMIN_EMAIL" in migration
                or "admin@telaryn.app" in migration
                or 'ATLAS_BOOTSTRAP_OWNER_REPAIR_APPROVED' not in migration
                or '!= "yes"' not in migration
            ):
                findings.append(
                    (IDENTITY_MIGRATION, "publication-safe migration review unresolved")
                )
        review = (ROOT / "docs/source-release-checklist.md").read_text(encoding="utf-8")
        # This guard is also run after a source-only publication. The post-publication
        # record must preserve an explicit prohibition on production deployment;
        # publication permission must never be interpreted as deployment permission.
        if "**Current disposition: NOT APPROVED FOR PUBLICATION.**" in review:
            findings.append(("<Owner approval>", "release checklist is still not approved"))
        elif (
            "**Current disposition: APPROVED FOR PUBLICATION.**" not in review
            and "**Current disposition: SOURCE PUBLICATION COMPLETED; PRODUCTION DEPLOYMENT NOT AUTHORIZED.**"
            not in review
        ):
            findings.append(("<Owner approval>", "an explicit source publication disposition is required"))
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
