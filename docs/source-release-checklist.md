# Telaryn source publication review — BLOCKED

This checklist applies to the **private** `release/source-candidate` branch. Do not make this repository public, merge as release-approved, publish a package, or deploy this snapshot until the owner approves the exact release content and every mandatory gate is recorded.

## Provenance and separation

- Source baseline: `disconnecktie/Atlas`, Git ref `policy/proprietary-source-available` at `52d0511f6f05ea0485cb12e4bc42097f720135a7`. The source branch's licensing changes are draft and have not been merged into the original Atlas `main`.
- This repository began empty with its own Git history; only selected source snapshots were copied from Atlas. Its new commits remain in the same Telaryn repository and will be visible if the repository becomes public.
- Included for review: `app/`, `frontend/` including current Telaryn brand assets, `alembic/`, selected `tests/`, local development build configuration, and the reviewed public-safe root documentation.
- Excluded: all `infra/` staging/production files, private operational documentation, development audit exports, old workflow/Actions logs, Atlas historical commits and PRs, and direct cloud provisioning/recovery scripts.
- Selected tests that depended on private deployment code or original documentation were not transferred: `test_production_foundation.py`, `test_staging_operations.py`, `test_staging_recovery.py`, `test_release_identity.py`, `test_ai_configuration.py`, `test_source_guideposts.py`, `test_branding_identity.py`, and `test_public_documentation.py`.

## Mandatory gates before public visibility

- [ ] **Owner source review:** Inspect every file in this branch and verify no internal identities, privileged account information, cloud resource names, URLs, recovery targets, personal contact details or private work content remain. Initial pattern checks are not a comprehensive secret or privacy audit.
- [x] **Public-candidate migration hardening:** `alembic/versions/a108b010c002_repair_production_bootstrap_owner.py` no longer includes a fixed production administrator email and now requires an explicit environment approval for a placeholder-owner repair. Added tests for repair, refusal, and no-op. **Atlas originals and deployed databases were not modified.**
- [ ] **Migration compatibility sign-off:** Confirm the public-only migration revision is appropriate for future clean installs and that it will never be used to update production without a separately reviewed deployment path.
- [ ] **Content and identity review:** Review `frontend/src/pages/AboutJay.jsx`, `frontend/src/devlog/entries.js`, public policy copy, published contact details, and other user-visible content for intentional disclosure.
- [x] **Automated history scanning:** Private Gitleaks full-ref run [#42662313992](https://github.com/disconnecktie/Telaryn/actions/runs/42662313992) passed. CI [#42662313813](https://github.com/disconnecktie/Telaryn/actions/runs/42662313813) also passed a separate all-reachable-commit tree/path and known-marker audit. Recheck both at the exact final publication head; these are not a guarantee that no sensitive material exists.
- [x] **Commit metadata disclosure accepted:** The owner understands that public Git history exposes author and committer metadata, including the existing personal email address, and is comfortable with that exposure. **No additional repository or history rewrite is required solely for this reason.**
- [x] **JavaScript dependency license inventory:** Added [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md), covering 246 npm lockfile package records, less common declared licenses, and upstream Can I Use compatibility-data attribution.
- [x] **Unused image cleanup:** Automated reference audit found no frontend references to four legacy Atlas PNG icons, an inactive favicon, or the React/Vite starter SVGs. All seven are absent from the current release tree; they remain accessible in old Git commits.
- [x] **Python license metadata inventory:** CI inspected 62 pinned runtime packages and verified installed versions; every package returned license metadata. One reported LGPLv3 and two reported MPL-related licenses. The manual upstream license and distribution review remains open.
- [x] **Current PNG provenance:** On 9 November 2026 the owner confirmed personally generating all four current PNG assets (three Telaryn icons and `frontend/src/assets/hero.png`). Provenance attested by owner, not independently verified as exclusively copyrightable; generation-platform terms and potential third-party resemblance remain subject to review.
- [ ] **Third-party rights sign-off:** Confirm exact upstream package notices, Python dependency licenses, applicable image-generation-platform reuse rights, social-brand marks and historical asset files, plus rights to include all materials in a source-available repository. The proprietary LICENSE does not override those rights.
- [ ] **Legal/terms:** Owner approves `LICENSE`, privacy notice, and hosted-service Terms. Copyright protects original expression, not general software ideas.
- [x] **Backend and local migration CI:** Backend tests and local PostgreSQL migration smoke passed in [#42662313813](https://github.com/disconnecktie/Telaryn/actions/runs/42662313813).
- [ ] **Excluded-test review:** Confirm excluded environment-specific tests are replaced or not relevant to the intended public source release; separately approve production migration compatibility.
- [x] **Automated frontend checks:** `npm ci`, `npm run lint`, `npm test`, `npm run build` passed in [#42662313813](https://github.com/disconnecktie/Telaryn/actions/runs/42662313813).
- [ ] **Manual UI check:** Verify responsive desktop/mobile workflows and whether all original assets may be published.
- [x] **Containers:** `docker compose config`, backend/frontend image builds, and temporary database migration smoke passed in [#42662313813](https://github.com/disconnecktie/Telaryn/actions/runs/42662313813). The Compose configuration is for local development only and must not be exposed directly to the internet.
- [ ] **Repository controls:** Configure branch protection/rulesets when eligible, least-privilege Actions permissions, dependency alerts, secret scanning as available, and private vulnerability reporting where supported. GitHub currently returns a plan-gating error for private-repository rulesets and the integration cannot inspect branch-protection settings. Verify controls in GitHub Settings before approving public visibility; do not change visibility merely to enable protections.
- [x] **Reachable historical path audit:** CI [#42662313813](https://github.com/disconnecktie/Telaryn/actions/runs/42662313813) checked commit trees, historical file paths, and selected sensitive markers; none blocked. The separate Gitleaks history scan passed. No Atlas history was imported.
- [x] **Historical administrator-email disclosure accepted:** The owner explicitly approved public visibility of the generic `admin@telaryn.app` address in older migration and test-fixture commits. This acceptance applies to that address only; other historical secrets, operational metadata, and personal data must still be reviewed. Current migration code remains environment-configured and opt-in.
- [ ] **Final exact-head audit:** Re-run the checks after final edits and manually review all reachable refs and retained PR content, including other possible operational or personal disclosures.
- [ ] **Owner sign-off:** Record the exact approved commit, test runs, scan summary, and legal review, then decide whether to publish.

## Application-versus-website scope

Making this GitHub repository public discloses source but **does not** deploy or expose the Telaryn-hosted website. Public product pages, invitation-only workspaces, and public production launch have separate deployment and security gates under the private Atlas operations runbooks.

**Current disposition: NOT APPROVED FOR PUBLICATION.**
