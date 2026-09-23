# Reviewed documentation migrations implementation plan

**Goal:** Deliver dsh-doc-audits 0.2.0 as a thin agent workflow with executable write controls.
**Architecture:** Keep repository inspection and deterministic checks in the existing CLI. Add a focused workflow module for snapshots, sealed plans, review validation and constrained application. Keep schemas and long examples out of SKILL.md.
**Tech stack:** Python 3.11+ standard library, Git, JSON-compatible YAML.
**Spec:** ../specs/2026-09-23-reviewed-doc-migrations.md

## Global constraints

Preserve the existing Git history. Work in this isolated sandbox clone on a feature branch. No remote writes or chanapp changes. No project-specific vocabulary in distributed rules. No pretending an author review is an independent model eval.

## Review focus

Dirty and changed repositories; untrusted JSON and path traversal; symlink/hardlink boundaries; scaffold falsely called current; missing/stale review and fresh-session evidence.

## Task 1 — Deterministic readiness

- [x] Add failing tests to tests/test_readiness.py for empty/malformed manifests, scaffold and current-authority placeholders, fenced-code exceptions, and standalone verifier parity.
- [x] Run `python -m unittest discover -s tests -p test_readiness.py -v`; observe rejection tests fail on 0.1.0.
- [x] Implement strict structural validation and completion findings in the bundled and repo-local verifier; mark generated architecture/README as scaffold.
- [x] Run full suite; keep bootstrap structurally valid while clearly pending semantic work.

## Task 2 — Plan, review and guarded apply

- [x] Add tests/test_reviewed_workflow.py with disposable Git repos and CLI tests. Fail on missing doctor/review-pack/apply and missing review/digest controls.
- [x] Add JSON Schemas for migration plans, review packages/results and fresh-session results.
- [x] Add scripts/workflow_guard.py; `plan --proposal` seals model-authored owners/actions without inventing them. `doctor` only gathers observations.
- [x] Wire CLI commands. Require clean snapshot, prepared status, approve verdict, exact scope and explicit in-place permission. Use no command execution from plans.
- [x] Test stale proposals, changed contents, product writes, unsafe paths, failed writes/rollback, repeat apply and declined/self reviews.

## Task 3 — Guidance, checks and release

- [x] Make SKILL.md a short router; add references/authority-review.md and examples for generic review/application.
- [x] Describe actual automated capabilities and remaining agent judgment; distinguish attestation from authentication.
- [x] Add process Agent Note; update architecture, CLI contract, changelog, version and local asset parity checks.
- [x] Run the entire suite, CLI demonstration, docs and impact checks, review the diff, and record limitations.
- [x] Commit on the feature branch; export and validate a full-history bundle and source ZIP. Rehearse safe upload against a local bare remote; document fast-forward upload or PR path without force.

## Execution note

Source implementation and deterministic acceptance are complete. The distribution bundle and upload rehearsal are recorded in the accompanying release verification report. Independent model review was unavailable; only author review and explicitly synthetic orchestration fixtures ran.
