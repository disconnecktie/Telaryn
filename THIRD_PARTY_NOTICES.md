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

No installed npm package directories or compiled frontend bundles are tracked in this
release-candidate Git tree. A future distributed frontend bundle or container image
must separately preserve upstream notices and other obligations.

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
classifications:
- `psycopg[binary]==3.2.10`: LGPLv3 per installed metadata; [upstream license](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt).
- `certifi==2026.7.22`: MPL-2.0 per installed metadata; [upstream license](https://github.com/certifi/python-certifi/blob/master/LICENSE).
- `tqdm==4.70.0`: MPL-2.0 AND MIT per installed metadata; [upstream license and attribution](https://tqdm.github.io/licence/).

### Upstream license-text and distribution-scope review (10 November 2026)

An initial upstream-source check supports the three license classifications above:

- **Psycopg 3.2.10:** PyPI declares LGPLv3 for the pinned `psycopg` release.
  The `[binary]` extra installs a separately packaged, self-contained
  `psycopg-binary` implementation, including compiled components and bundled
  native libraries. [Psycopg installation and bundled-binary explanation](https://www.psycopg.org/psycopg3/docs/basic/install.html)
  and [pinned PyPI release](https://pypi.org/project/psycopg/3.2.10/).
  **Before distributing a production Docker image or binary package**, inventory
  the actual installed wheel and native libraries and fulfill all applicable
  notices and LGPL requirements; the source repository does not contain the wheel.
- **Certifi:** PyPI confirms MPL-2.0, and the [upstream LICENSE](https://github.com/certifi/python-certifi/blob/master/LICENSE)
  describes the Mozilla-derived certificate authority bundle. Retain upstream
  notices when redistributing that bundled data in a packaged application.
- **tqdm:** The [upstream license text](https://tqdm.github.io/licence/)
  identifies MPL-2.0 for principally maintained files and MIT terms for specified
  contributions. Its project-level combined metadata does **not** imply every
  file can be relicensed as MIT.

This is a **source-level license classification and notice-scope check**, not
independent verification of every package byte, legal advice, or distribution
approval. No installed dependency wheels, `node_modules/`, Docker images,
or built frontend bundles are committed to this source candidate. Build-time
and runtime distributions have separate third-party obligations.

## Artwork, icons and marks

- `frontend/public/telaryn-mark.svg` and Telaryn product artwork are presented
  under the first-party proprietary notice **only to the extent they are original
  works owned by Telaryn's copyright owner**.
- Eight unused assets were excluded from the current release tree after
  an automated reference audit. Their exact historical paths are
  `frontend/public/atlas-icon.png`,
  `frontend/public/atlas-icon-180.png`,
  `frontend/public/atlas-icon-192.png`,
  `frontend/public/atlas-icon-512.png`,
  `frontend/public/favicon.svg`,
  `frontend/src/assets/react.svg`,
  `frontend/src/assets/vite.svg`, and
  `frontend/public/icons.svg`.
  Their deletion commits were examined on 10 November 2026; the content remains
  accessible through older commits of the same repository. **A source-available
  release exposing these commits requires rights/provenance review of the
  historical files too**, or a separately approved history strategy.
  Deleting a path from the current tree is not enough. The
  [official Vite create-vite license](https://github.com/vitejs/vite/blob/main/packages/create-vite/LICENSE)
  makes Vite-generated starter template files CC0, but this does not transfer
  React, Vite or other brand/trademark rights or establish that every
  historical SVG was sourced from that exact release.
- Historical `frontend/public/icons.svg` contained identifiable Bluesky,
  Discord, GitHub, and X social-platform symbol artwork alongside generic icons.
  The owner explicitly confirmed on 10 November 2026 that these symbols were
  **not assets they supplied**. The same confirmation applies to the React/Vite
  starter logos in the historical commits. These are third-party or inherited
  template assets, **not first-party Telaryn/Atlas image creations**, and the
  proprietary license makes no ownership claim over them. The sprite has
  been removed from the current tree after a no-reference guard was added;
  it and the React/Vite starter icons remain available in prior Git commits.
  The social glyphs are subject to their respective brand guidelines and
  potentially copyright terms. For example,
  [Bluesky's social-icon guidance](https://bsky.social/about/support/branding)
  permits specified social profile linking, while
  [GitHub's brand toolkit](https://brand.github.com/foundations/logo)
  defines authorized uses of its logos. Neither gives Telaryn exclusive ownership
  of those marks. Confirm the actual SVGs' origin/redistribution rights or
  replace them if reused; assess the historical starter-logo contents separately.
  No active public frontend reference to the sprite was found in targeted
  manual inspection; CI checks source references across all frontend text
  files before accepting its absence.
### Historical third-party icon policy review (10 November 2026)

An additional inspection of retained historical SVG content identified the
exact glyph types and confirmed that they remain **absent from the current
release tree**, but exposed in Git commits if the repository becomes public:

| Former path | Historical content | Upstream use-rights context |
| --- | --- | --- |
| `frontend/public/favicon.svg` | Vite-style graphical mark | May be from a create-vite template; precise upstream file/version not independently matched |
| `frontend/src/assets/vite.svg` | Vite graphical mark | Vite [create-vite template files are CC0](https://github.com/vitejs/vite/blob/main/packages/create-vite/LICENSE), if the copied file originated in that template; trademark rights are separate |
| `frontend/src/assets/react.svg` | React atom-style logo, class `iconify--logos` | Mark is not the creator's proprietary artwork; original icon distributor/license and trademark permissions have not been independently established |
| `frontend/public/icons.svg` | Bluesky butterfly, Discord, GitHub Invertocat, X emblem, plus generic social/documentation glyphs | Historical SVG sprite has no confirmed attribution chain; [Bluesky](https://bsky.social/about/support/branding), [Discord](https://discord.com/branding), [GitHub](https://brand.github.com/foundations/logo) and [X](https://about.x.com/en/who-we-are/brand-toolkit) each impose independent brand-use limits |

**Rights distinction:** Vite's license grants CC0 to files copied from its
`template-*` directories; the create-vite package itself is MIT. Neither
license releases other organizations' trademarks, guarantees the exact historical
SVG came from that distribution, or grants unrestricted use of modified
platform logos. The old social glyphs do not appear to have been active UI
dependencies, and the current release source has removed them. This inspection
does **not** claim blanket legal clearance for publishing their *retained Git
history*.

Before source publication, the owner must explicitly choose between:
(a) making the existing repository's historical SVGs visible while preserving
the third-party carve-outs and accepting the remaining provenance/rights
questions, subject to appropriate legal review; or (b) preparing a separate
clean-history source candidate (or another specifically approved content
remediation) that does not carry the old third-party icons. **No history rewrite,
repository replacement, publication or deployment is authorized by this note.**

- **Owner-provided provenance statement (9 November 2026):** The Telaryn
  owner confirmed they personally generated all four PNG assets remaining in
  the current source tree: `frontend/public/telaryn-apple-touch-icon.png`,
  `frontend/public/telaryn-icon-192.png`,
  `frontend/public/telaryn-icon-512.png`, and
  `frontend/src/assets/hero.png`. No outside asset-source attribution was
  identified by the owner. This records provenance as reported, not
  independently verified exclusive copyright ownership or the generation
  platform's commercial/distribution terms. AI-generated elements may have
  limited copyright protection depending on jurisdiction and human authorship.
- **Owner-provided historical Atlas provenance statement (10 November 2026):**
  Owner reported creating the Atlas and Telaryn branding using ChatGPT, in
  response to a question covering four historical Atlas PNGs and an old
  favicon. The four `atlas-icon*.png` files are owner-attested first-party
  creations. Subsequent source inspection found the separately tracked
  `frontend/public/favicon.svg` is a **Vite-branded graphic**; its origin
  cannot responsibly be treated as independently verified first-party
  ChatGPT output merely from the broader answer. Classify that SVG with the
  framework/template marks pending source attribution. All five old files
  remain accessible in Git history; neither the historical React/Vite logos
  nor social-network glyphs are claimed as owner-created.

## ChatGPT image-generation provenance and rights review (10 November 2026)

The owner confirmed that **ChatGPT** was the generation tool for their Atlas
and Telaryn artwork, covering four active Telaryn PNGs and four historical
Atlas icon PNGs. The old `favicon.svg` is Vite-branded and its own provenance
needs separate treatment, as discussed above. This supplements the
owner-provided statements; no prompts, accounts or private conversations are
included in the public candidate.

The [OpenAI Terms of Use](https://openai.com/policies/terms-of-use/) effective
January 1, 2026 state that, as between the user and OpenAI, the user owns Output
to the extent permitted by applicable law, and OpenAI assigns any rights it may
have in that Output. The [OpenAI ChatGPT help article](https://help.openai.com/en/articles/6783457-what-is-chatgpt)
also confirms commercial reuse of generated output, subject to the Terms and
applicable policies. Output may not be unique; these terms do not grant
third-party intellectual-property or trademark rights.

**Platform permission is not a finding of exclusive copyright.** Under the
[U.S. Copyright Office's January 2025 guidance](https://www.copyright.gov/newsnet/2025/1060.html),
copyright protection for AI-assisted images depends on sufficient human-authored
expression; prompts alone may be insufficient. The degree of human editing and
authorship for these particular image files has not been independently examined.
Telaryn's proprietary notice therefore reserves rights only in legally
protectable first-party expression, and it does not claim rights in third-party
logos. No independent image-similarity or third-party-rights clearance has
been performed.

## Release handling

Before making this repository public, the owner should confirm the included
dependencies and assets may be distributed in source form, attach or retain
required copyright notices where relevant, and confirm the hosted application's
Privacy and Terms policies accurately describe its current behavior.

**Status: JS/Python package metadata inventories complete; upstream license
classifications for the three flagged Python packages checked against current
official documentation; unused starter/legacy assets removed only from the
current tree. Owner-attested provenance recorded for four current PNGs
and four historical Atlas icon PNGs. The old Vite-branded favicon is
considered separately as a template/brand-mark asset.
OpenAI ChatGPT output-use terms reviewed and generator identified; exclusive
copyright, historical third-party glyph/starter-logo rights, built-distribution
notices, retained-history content, and final owner/legal approval remain
pending.**
