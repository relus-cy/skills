# Release the skills repository

Status: current procedure

## Preconditions

Use a clean checkout containing the proposed release. Keep private project data, credentials and actual review transcripts out of the public source. Inspect the Git remote before publication; this procedure never requires force-push.

## Verify

Run from repository root:

```bash
bash scripts/verify.sh
python scripts/smoke_reviewed_workflow.py
```

The first command checks syntax, the complete test suite, generated asset freshness, documentation readiness and corpus checks. The second exercises the CLI in a disposable Git repository with explicitly synthetic review records. Neither proves a real model's semantic quality. Record separately whether an independent model assessment was performed.

## Package

Use a named release branch. Replace the branch and output names deliberately:

```bash
git bundle create ../skills-release.bundle <release-branch>
git bundle verify ../skills-release.bundle
git archive --format=zip --prefix=skills/ -o ../skills-release.zip <release-branch>
```

A full-history bundle allows clean import. Verify it from a repository, and test a fresh clone. Compute SHA-256 checksums of the deliverables. The bundle branch must descend from the previously published commit.

## Publish into the existing GitHub repository

Fetch the bundle into a separate local branch. Fetch the remote's current main and inspect divergence. Fast-forward main only when Git accepts that relationship. Otherwise publish the release branch and review/merge through a pull request. Never create a replacement repository or use force to remove remote changes.

Publication needs the user's authenticated Git environment and is a separate explicit action. A local test pass does not claim that GitHub Actions has run; inspect remote CI after upload.

## Recovery

Retain the original branch and full-history bundle. A failed fast-forward or rejected push leaves remote work intact; reconcile the branches rather than overwriting history.
