"""Check published frontend assets against source references.

Conservative static check. JavaScript can construct paths dynamically, so a
passing check is supporting evidence, not a provenance or rights determination.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
SEARCH_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx", ".css", ".html", ".json", ".md", ".webmanifest"}

# These legacy Atlas, starter-template, and inherited social-icon assets
# are unreferenced by the release source and excluded from its current tree.
LEGACY_ASSETS = (
    "atlas-icon-180.png",
    "atlas-icon-192.png",
    "atlas-icon-512.png",
    "atlas-icon.png",
    "favicon.svg",
    "react.svg",
    "vite.svg",
    "icons.svg",  # Unused inherited social-network icon sprite
)
CURRENT_ASSETS = (
    "telaryn-mark.svg",
    "telaryn-apple-touch-icon.png",
    "telaryn-icon-192.png",
    "telaryn-icon-512.png",
)


def main() -> int:
    corpus = []
    for path in FRONTEND.rglob("*"):
        if path.is_file() and path.suffix.lower() in SEARCH_EXTENSIONS:
            if "node_modules" in path.parts or "dist" in path.parts or path.name == "package-lock.json":
                continue
            corpus.append((str(path.relative_to(ROOT)), path.read_text(encoding="utf-8")))
    failures = []
    print(f"Asset-reference audit: {len(corpus)} frontend text files")
    for name in LEGACY_ASSETS:
        references = [path for path, text in corpus if name in text]
        retained = [str(path.relative_to(ROOT)) for path in FRONTEND.rglob(name) if path.is_file()]
        if retained:
            failures.append((name, retained))
        # A legacy path may appear in a README; count that as a reference
        # requiring manual inspection before removal.
        print(f"  Legacy {name}: {len(references)} source references")
        if references:
            failures.append((name, references))
    for name in CURRENT_ASSETS:
        references = [path for path, text in corpus if name in text]
        print(f"  Active {name}: {len(references)} source references")
        if not references:
            failures.append((name, ["missing HTML/manifest reference"]))
    if failures:
        for name, paths in failures:
            print(f"Review needed for {name}: {', '.join(paths[:5])}")
        return 1
    print("Asset-reference guard passed; ownership and licensing review still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
