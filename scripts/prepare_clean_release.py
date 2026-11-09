"""Build a fresh, offline Telaryn source tree without retaining Git history.

This script never pushes, deletes, renames, or changes a GitHub repository.
It is not publication approval. Review docs/clean-history-publication-plan.md.
"""
from __future__ import annotations

import argparse
from io import BytesIO
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
REVIEW_ONLY = {
    "docs/clean-history-publication-plan.md",
    "docs/source-release-checklist.md",
    "scripts/prepare_clean_release.py",
    "scripts/verify_source_snapshot.py",
    ".github/workflows/ci.yml",
    ".github/workflows/private-history-secret-audit.yml",
}
ROOT_FILES = {
    ".dockerignore", ".gitattributes", ".gitignore", "Dockerfile",
    "README.md", "LICENSE", "SECURITY.md",
    "alembic.ini", "compose.yaml", "requirements.txt", "requirements-dev.txt",
}
PUBLIC_DOCS = {
    "docs/deployment-architecture.md", "docs/operations-overview.md",
}
PUBLIC_DIRS = ("app/", "frontend/", "alembic/", "tests/")
MAX_ARCHIVE_SIZE = 40 * 1024 * 1024


def git(*args: str, cwd: Path = ROOT, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def public_path(path: str) -> bool:
    return path in ROOT_FILES or path in PUBLIC_DOCS or path.startswith(PUBLIC_DIRS)


def collect_archive() -> tuple[list[tuple[str, bytes]], int]:
    branch = git("branch", "--show-current").stdout.decode().strip()
    if branch not in ("release/source-candidate", ""):
        raise RuntimeError("Refusing export: checkout the reviewed source-candidate branch.")
    proc = git("archive", "--format=tar", "HEAD")
    if len(proc.stdout) > MAX_ARCHIVE_SIZE:
        raise RuntimeError("Export exceeds configured archive size.")
    records: list[tuple[str, bytes]] = []
    skipped = 0
    seen = set()
    with tarfile.open(fileobj=BytesIO(proc.stdout), mode="r:") as archive:
        for member in archive:
            path = member.name.rstrip("/")
            parts = PurePosixPath(path).parts
            if not parts or ".." in parts or ".git" in parts or path.startswith("/"):
                raise RuntimeError("Unsafe archive path was detected.")
            if member.isdir():
                continue
            if not member.isfile():
                raise RuntimeError(f"Non-regular archive entry refused: {path}")
            if path in REVIEW_ONLY:
                skipped += 1
                continue
            if not public_path(path):
                raise RuntimeError(f"Unexpected source path requires review: {path}")
            if path in seen:
                raise RuntimeError(f"Duplicate archive entry refused: {path}")
            seen.add(path)
            fileobj = archive.extractfile(member)
            if fileobj is None:
                raise RuntimeError(f"Unreadable archive entry refused: {path}")
            records.append((path, fileobj.read()))
    required = {"README.md", "LICENSE", "SECURITY.md", "app/main.py", "frontend/package.json"}
    missing = required - {path for path, _ in records}
    if missing:
        raise RuntimeError(f"Missing required public source files: {sorted(missing)}")
    license_text = next(content for path, content in records if path == "LICENSE").decode()
    if "All rights reserved" not in license_text or "Proprietary Source-Available" not in license_text:
        raise RuntimeError("Expected proprietary source-available license was not found.")
    return sorted(records), skipped


def assert_ready_to_initialize(records: list[tuple[str, bytes]], author_email: str) -> None:
    if not re.fullmatch(
        r"(?:[0-9]+\+)?[A-Za-z0-9-]+@users\.noreply\.github\.com",
        author_email,
        flags=re.IGNORECASE,
    ):
        raise RuntimeError("An explicitly verified GitHub users.noreply.github.com address is required.")
    readme = next(content for path, content in records if path == "README.md").decode().lower()
    if any(flag in readme for flag in (
        "private source release candidate",
        "do not make this repository public",
        "not yet cleared for public visibility",
        "review branch",
    )):
        raise RuntimeError("The current README still identifies an unapproved review candidate.")
    try:
        check = subprocess.run(
            ["gitleaks", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Gitleaks must be installed before initializing the release history.") from exc
    if not check.stdout:
        raise RuntimeError("Unable to verify the Gitleaks installation.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--initialize-clean-git", action="store_true")
    parser.add_argument("--author-name")
    parser.add_argument("--author-email")
    args = parser.parse_args()

    records, skipped = collect_archive()
    if args.check_only:
        print(f"Release export preview: {len(records)} source files; {skipped} review-only files omitted.")
        print("Inventory only; security, identity, third-party and owner reviews still required.")
        return 0

    if args.output is None:
        parser.error("--output is required unless --check-only is selected")
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise RuntimeError("The output directory must be outside the source checkout.")
    if output.exists():
        raise RuntimeError("Refusing to overwrite an existing output directory.")

    if args.initialize_clean_git:
        if not args.author_name or not args.author_email:
            parser.error("--author-name and --author-email are required when initializing Git.")
        assert_ready_to_initialize(records, args.author_email)

    output.mkdir(parents=True, exist_ok=False)
    for path, content in records:
        target = output.joinpath(*PurePosixPath(path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    if args.initialize_clean_git:
        import os
        subprocess.run(
            ["gitleaks", "dir", str(output), "--no-banner", "--log-level", "error", "--redact=100"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        git("init", "-b", "main", str(output))
        git("config", "user.name", args.author_name, cwd=output)
        git("config", "user.email", args.author_email, cwd=output)
        git("add", "--all", cwd=output)
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME": args.author_name,
            "GIT_AUTHOR_EMAIL": args.author_email,
            "GIT_COMMITTER_NAME": args.author_name,
            "GIT_COMMITTER_EMAIL": args.author_email,
        })
        git("commit", "-m", "Initial proprietary Telaryn source release", cwd=output, env=env)
        print("Created a new local Git root with a verified noreply identity; nothing was pushed.")
    else:
        print("Created a history-free offline source preview; no Git repository initialized.")
    print(f"Files: {len(records)}; review-only files omitted: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
