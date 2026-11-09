# Telaryn: clean-history publication plan (private review)

**Status: preparation only. The repository must remain private.**

## Why another Git history is necessary

The new `disconnecktie/Telaryn` staging repository has commits containing a personal author email. Updating GitHub's email privacy setting, amending the HEAD commit, or changing future author settings **does not remove metadata from historical commits**. A force-push to `main` also does not guarantee that refs from draft PRs and GitHub caches become inaccessible.

The already-open draft PR, its original commits, and the internal discussions should stay **private**. Do not directly turn this existing history public.

## Safe identity-preserving publication sequence

1. Finish code/migration, license, asset and personal-profile review. Run pytest, frontend checks, container smoke, Gitleaks on the exact candidate, and review the published README.
2. Export the approved snapshot into a separate directory **without .git** by using `python scripts/prepare_clean_release.py --output <new-directory>`. This tool does not push or publish anything, excludes review-only scripts/checklists/CI workflows, and refuses existing output directories.
3. Once every publication gate is explicitly approved and the README is cleaned, initialize the exported snapshot as an entirely **new root Git history** using `--initialize-clean-git --author-email <verified-GitHub-noreply-email>`. Review the new initial commit's author/committer addresses and `git log --all`. The exporter refuses to initialize an unapproved source snapshot.
4. Create a **new separate private** GitHub repository temporarily named `Telaryn-release`. Push only the freshly initialized root branch to it. **Never push Atlas or the current Telaryn staging history to it.**
5. Inspect the new repository's files, refs, commit count, Gitleaks summary, security settings, and GitHub Actions. Configure private vulnerability reporting, branch protection, and least-privilege CI. Obtain explicit owner approval.
6. In GitHub repository Settings, rename the existing **private** `Telaryn` repository to `Telaryn-internal` (keeping the draft PR private). Rename the clean private `Telaryn-release` repository to `Telaryn`. Confirm both actual destinations and check for any ambiguous URL redirects.
7. Only then, after verifying the new `disconnecktie/Telaryn` has *no inherited private history*, make the clean repository public. The original Atlas and renamed Telaryn-internal repos remain private.

**Why rename rather than delete?** The internal staging PR and its historical commit metadata stay accessible only to authorized users, without relying on GitHub purging orphaned commits or cache entries. The public repository gets a genuinely new root commit.

## Controls and limitations

- The export script has **no network push or repository administration code**. It never changes existing refs, cloud infrastructure, databases, or GitHub visibility.
- Do not point the output at a preexisting directory or a path inside the source checkout.
- There is no claim that a passing keyword scan proves source is safe. Perform manual privacy reviews and a dedicated secrets scan of the exact export and its new Git history.
- Confirm the email address used for the public commit is one that GitHub recognizes as your **noreply** identity. Do not assume hiding an email in account settings rewrites old commits.
- Do not publish the staging-only release checklist, private Gitleaks workflow, or intentionally-failing prerelease CI. The clean public repository needs its own reviewed standard CI.
- The published README must not contain the current **private review candidate** warning before the exporter can initialize a new public-release Git root.
- The public proprietary LICENSE and the service's hosted-use Terms are separate. Public GitHub access does not confer broad modification/redeployment rights.
