# Release dsh-doc-audits

Status: current procedure
Owner: repository maintainer
Last verified: 2026-09-23

## Outcome

Produce a verified source commit and portable archive for a new skill version.

## Preconditions

- Working tree contains only intended changes.
- `SKILL.md`, `pyproject.toml`, `CHANGELOG.md`, generated asset metadata, and governance manifest agree on the version.
- Python 3.11 or newer and Git are available.

## Steps

1. Run the full gate:

   ```bash
   bash scripts/verify.sh
   ```

2. Inspect the working tree and commit history:

   ```bash
   git status --short
   git log --oneline -5
   ```

3. Build portable artifacts outside the repository or under ignored `dist/`:

   ```bash
   mkdir -p dist
   git archive --format=zip --output=dist/skills-source.zip HEAD
   git bundle create dist/skills.git.bundle --all
   ```

4. Verify both artifacts can be inspected:

   ```bash
   unzip -t dist/skills-source.zip
   git bundle verify dist/skills.git.bundle
   ```

5. Create and push the remote repository or release only through an authenticated environment with explicit write authorization.

## Verification

The full gate must pass with zero test failures and both artifact verification commands must return exit code `0`.

## Failure and recovery

A failing gate blocks the release. Fix the owning source or test; do not edit generated artifacts. If an archive is bad, delete the ignored artifact and recreate it from a verified commit.

## Rollback

Artifacts are disposable. Remote rollback follows the hosting platform's repository or release controls and remains outside this runbook's automatic actions.
