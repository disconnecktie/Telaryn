# Third-party dependency and asset notices (release candidate)

Telaryn is proprietary first-party software. Its [LICENSE](LICENSE) covers only the
rights the Telaryn owner can grant. **This file does not replace upstream license
texts or grant any new license to third-party content.**

## JavaScript dependency inventory

The checked-in `frontend/package-lock.json` identifies 246 non-root npm package
records, including transitive dependencies and platform-specific optional binaries.
Its declared license distribution at the time of review is:

| License in npm lockfile | Package records |
| --- | ---: |
| MIT | 191 |
| Apache-2.0 | 17 |
| ISC | 12 |
| MPL-2.0 | 12 |
| BSD-2-Clause | 8 |
| BSD-3-Clause | 3 |
| MIT-0 | 1 |
| CC-BY-4.0 | 1 |
| BlueOak-1.0.0 | 1 |

The less common licenses in the lockfile include:

- **CC-BY-4.0:** `caniuse-lite` (browser-compatibility dataset derived from [Can I Use](https://caniuse.com/)). **Attribution:** Browser compatibility data from [caniuse.com](https://caniuse.com/), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The upstream project [requests attribution to caniuse.com](https://github.com/browserslist/caniuse-lite#license).
- **MPL-2.0:** `lightningcss` and related native platform packages
- **BlueOak-1.0.0:** `minimatch`
- **MIT-0:** `@csstools/color-helpers`

The list above summarizes *declared package metadata*, not independently verified
licenses of all package files and transitive subcomponents. Installation of dependencies
via `npm ci` remains subject to each package's own terms. Review exact package
versions, upstream notices, and whether any dependency code or data is included in
distributed bundles before shipping a packaged client or modified third-party library.

## Python dependencies

`requirements.txt` and `requirements-dev.txt` include FastAPI, SQLAlchemy,
Alembic, Azure SDK components, OpenAI's Python SDK, ReportLab, Pillow and other
third-party libraries. A CI metadata audit inspected **62 exactly pinned Python
runtime packages** and verified installed versions. All 62 reported a license
name or expression, including **one LGPLv3** classification and **two MPL-related**
classifications, which need a targeted distribution/notice review. Build-time and
runtime distributions may have different obligations. This is a package metadata
inventory, not a legal conclusion or a substitute for the actual upstream license
texts and distributed binary contents.

## Artwork, icons and marks

- `frontend/public/telaryn-mark.svg` and Telaryn product artwork are presented
  under the first-party proprietary notice **only to the extent they are original
  works owned by Telaryn's copyright owner**.
- Seven unused assets were excluded from the current release tree after
  an automated reference audit: four `atlas-icon` PNGs, an unused favicon,
  and starter React/Vite SVG logos. These older files still exist in historical
  commits; removal from the current tree does not remove historical copyright
  or trademark considerations.
- `frontend/public/icons.svg` contains social-platform glyphs. Brand and
  trademark rights are not granted by access to this repository.
- The original provenance, licensing, and distribution rights of the four remaining PNG
  assets (three Telaryn icons plus `frontend/src/assets/hero.png`) should be
  verified before approval. Do not assume a successful image transfer establishes
  copyright ownership.

## Release handling

Before making this repository public, the owner should confirm the included
dependencies and assets may be distributed in source form, attach or retain
required copyright notices where relevant, and confirm the hosted application's
Privacy and Terms policies accurately describe its current behavior.

**Status: JS and Python package metadata inventories complete; unused starter/legacy assets
removed from the current tree. Copyleft-related notices and image/mark provenance
reviews are pending.**
