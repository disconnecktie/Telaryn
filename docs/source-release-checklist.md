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
- [x] **No vendored third-party packages in current source:** Current release tree contains no tracked `node_modules/`, installed Python packages, vendor bundles, compiled distributions or build output. Runtime dependencies are referenced by manifest/requirements; redistribution of built container images would require separate license-notice checks.
- [ ] **Third-party rights sign-off:** Confirm exact upstream package notices, Python dependency licenses, applicable image-generation-platform reuse rights, social-brand marks and historical asset files, plus rights to include all materials in a source-available repository. The proprietary LICENSE does not override those rights.
- [x] **Privacy text/implementation alignment:** Release-candidate Privacy Policy now distinguishes 90-day access-request expiry from actual cleanup triggers, clarifies 90/365-day closed-feedback purge rules and the absence of an in-app scheduler, and explains that screenshot image pixels are not redacted. Added frontend regression tests. Azure infrastructure code configures log retention for 30 days, but active deployment settings require verification.
- [x] **Production scheduling in private source:** Reviewed the Atlas production Container Apps schedule definition: `0 4 * * *` (04:00 UTC daily) executes `python -m app.cli purge-retained-data`; source and production operations runbook agree on 90/365-day closed-feedback and 90-day access-request retention.
- [x] **Production cleanup execution history (owner-confirmed):** On 9 November 2026, the owner located the scheduled production cleanup job in Azure Container App Jobs and reported that all displayed executions succeeded. This is an owner observation, not an independent Azure API verification; the exact inspected time window and deployed image/arguments were not captured.
- [ ] **Remaining live retention configuration:** Confirm the job's deployed image, command, schedule, database target, and absence of missing executions; verify actual operational-log retention and backup lifecycles without disclosing secrets or customer data.
- [ ] **Contact inbox verification:** The public policy identifies `support@telaryn.app`, `privacy@telaryn.app`, and `security@telaryn.app`, and Atlas documents them as intended identities. Verify each is routable, monitored, and replies to an external test message; source/DNS alone cannot prove functioning inboxes.
- [x] **Policy revision dated:** Updated the review candidate's privacy revision date to 9 November 2026; this has not been published to the hosted service.
- [ ] **Legal/terms:** Owner approves `LICENSE`, privacy notice, and hosted-service Terms, including exact production retention execution, deployed log settings, contact addresses, and any notices to active users. Copyright protects original expression, not general software ideas.
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

## Operator-only live verification (read-only until separately approved)

These checks verify running systems, not just configuration in Git. Never paste
credentials, connection strings, personal messages, customer content or sensitive
Azure identifiers into a PR comment or public repository.

- [x] **Azure cleanup execution results:** The owner located the production cleanup job under Container App Jobs and reported all visible executions as **Succeeded** on 9 November 2026. Independent access to the Azure execution details was not available.
- [ ] **Azure cleanup deployment details:** Confirm the live scheduled job uses the intended production image, database and `purge-retained-data` command, and that no executions were missed outside the displayed window. The documented Bicep cron is `0 4 * * *` (04:00 UTC daily).
  See the [Microsoft Azure scheduled jobs guide](https://learn.microsoft.com/en-us/azure/container-apps/jobs).
- [ ] **Live retention:** Compare the actual deployed log retention, PostgreSQL
  managed-backup period, and independent backup lifecycle against approved
  runbook values (30 days of operational logs; 14 days for the two backup
  channels). Review actual Azure configuration without exporting data.
- [ ] **Inbound contact tests:** Confirm that support, privacy and security
  contact identities each accept an external test email and that the appropriate
  operator can respond. Azure Communication Services outbound sending
  configuration and a domain's MX records alone do not establish inbound
  alias/mailbox routing.
- [ ] **Public content review:** Approve the user-visible About page, founder
  biography/LinkedIn/GitHub links, devlog engineering timeline, policy
  contacts, legal terms and updated Privacy revision effective date.
- [ ] **Repository settings:** Verify branch protections/rulesets where available,
  vulnerability reporting, security alerts, Actions permissions, and branch
  visibility controls before any GitHub publication.

These are manual verification gates. They have **not** been completed by
source review or CI and must not be checked off solely from repository contents.

## Application-versus-website scope

Making this GitHub repository public discloses source but **does not** deploy or expose the Telaryn-hosted website. Public product pages, invitation-only workspaces, and public production launch have separate deployment and security gates under the private Atlas operations runbooks.

**Current disposition: NOT APPROVED FOR PUBLICATION.**
