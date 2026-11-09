# Telaryn source publication review — BLOCKED

This checklist applies to the **private** `release/source-candidate` branch. Do not make this repository public, merge as release-approved, publish a package, or deploy this snapshot until the owner approves the exact release content and every mandatory gate is recorded.

## Provenance and separation

- Source baseline: `disconnecktie/Atlas`, Git ref `policy/proprietary-source-available` at `52d0511f6f05ea0485cb12e4bc42097f720135a7`. The source branch's licensing changes are draft and have not been merged into the original Atlas `main`.
- This repository began empty with its own Git history; only selected source snapshots were copied from Atlas. Its new commits remain in the same Telaryn repository and will be visible if the repository becomes public.
- Included for review: `app/`, `frontend/` including original image assets, `alembic/`, selected `tests/`, local development build configuration, and the reviewed public-safe root documentation.
- Excluded: all `infra/` staging/production files, private operational documentation, development audit exports, old workflow/Actions logs, Atlas historical commits and PRs, and direct cloud provisioning/recovery scripts.
- Selected tests that depended on private deployment code or original documentation were not transferred: `test_production_foundation.py`, `test_staging_operations.py`, `test_staging_recovery.py`, `test_release_identity.py`, `test_ai_configuration.py`, `test_source_guideposts.py`, `test_branding_identity.py`, and `test_public_documentation.py`.

## Mandatory gates before public visibility

- [ ] **Owner source review:** Inspect every file in this branch and verify no internal identities, privileged account information, cloud resource names, URLs, recovery targets, personal contact details or private work content remain. Initial pattern checks are not a comprehensive secret or privacy audit.
- [x] **Public-candidate migration hardening:** `alembic/versions/a108b010c002_repair_production_bootstrap_owner.py` no longer includes a fixed production administrator email and now requires an explicit environment approval for a placeholder-owner repair. Added tests for repair, refusal, and no-op. **Atlas originals and deployed databases were not modified.**
- [ ] **Migration compatibility sign-off:** Confirm the public-only migration revision is appropriate for future clean installs and that it will never be used to update production without a separately reviewed deployment path.
- [ ] **Content and identity review:** Review `frontend/src/pages/AboutJay.jsx`, `frontend/src/devlog/entries.js`, public policy copy, published contact details, and other user-visible content for intentional disclosure.
- [ ] **Secret scan:** Run an up-to-date dedicated scanner (such as Gitleaks) across the **assembled candidate tree and its new history**, and manually inspect the findings. Rotate any real credentials found. Report only aggregate findings, never secret values.
- [x] **Commit metadata disclosure accepted:** The owner understands that public Git history exposes author and committer metadata, including the existing personal email address, and is comfortable with that exposure. **No additional repository or history rewrite is required solely for this reason.**
- [ ] **Third-party rights:** Review package dependency notices, art/fonts, and any independently authored code. The proprietary LICENSE does not override third-party licenses.
- [ ] **Legal/terms:** Owner approves `LICENSE`, privacy notice, and hosted-service Terms. Copyright protects original expression, not general software ideas.
- [ ] **Backend:** Run the transferred pytest suite, syntax checks, and independent migration upgrade/smoke tests in a disposable database. Confirm that excluded environment-specific tests are either replaced or not applicable to the public snapshot.
- [ ] **Frontend:** Run `npm ci`, `npm run lint`, `npm test`, `npm run build`; check responsive desktop/mobile and the original assets.
- [ ] **Containers:** Validate `docker compose config`, local integration, and the intended development-only configuration. Do not expose the Compose example directly to the internet.
- [ ] **Repository controls:** Configure branch protection/rulesets, least-privilege Actions permissions, dependency alerts, secret scanning as available, and GitHub private vulnerability reporting. Confirm the new repository contains no deployment secrets.
- [ ] **Final Git history audit:** Review the complete current repository history, all reachable branches/tags, previous edits and deleted files for secrets, private infrastructure references, and sensitive content. Author email metadata is intentionally permitted, but any other sensitive material still blocks publication. Atlas history must never be imported.
- [ ] **Owner sign-off:** Record the exact approved commit, test runs, scan summary, and legal review, then decide whether to publish.

## Application-versus-website scope

Making this GitHub repository public discloses source but **does not** deploy or expose the Telaryn-hosted website. Public product pages, invitation-only workspaces, and public production launch have separate deployment and security gates under the private Atlas operations runbooks.

**Current disposition: NOT APPROVED FOR PUBLICATION.**
