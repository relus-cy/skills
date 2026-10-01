# Changelog

## Unreleased

- Add the manual-only `recall` skill: `recall.py list` and `show` read Claude Code, Codex and Pi transcripts for one repository (cwd, main worktree or Codex `repository_url` match), keep real user messages and each turn's final reply, merge paginated Codex sessions, extract commit SHAs and GitHub PR/issue URLs, redact secrets, and warn on transcript files that no longer parse.

## 0.3.0 — 2026-10-01

- Resolve optional `authority.glossary` consistently across inspection, planning and reviewed writes; recognize `GLOSSARY.md` and legacy `CONTEXT.md` when unset, and leave dual-name authority conflicts for explicit resolution.
- Support Matt workflow coexistence: template tiers cover ADRs and agent guides, existing owners and the `Agent skills` block stay preserved, and external tracker close-out writes durable conclusions back to repository owners. ADRs use the existing Agent Notes opt-out.
- Record Matt source provenance and the boundary between compatibility and imported implementation.

- Prepared plans bind the checkout root, the paths they read or write and the names of current-tier documents, so unrelated commits and new historical documents no longer invalidate them. Reviews bind a location-independent `content_digest`, and an unchanged proposal replanned in another worktree keeps its review. Plan, review-package and review-result schemas move to version 2.
- Guard errors name changed paths and the next command; `doctor` adds a `remediation` map. Evidence must be Git-visible, and fingerprints ignore non-executable mode bits.
- The plan guard reads protected historical paths from the manifest's `tiers.historical`. Template defaults, historical-surface inspection and impact mappings are now project-neutral.
- The template recognizes the authority terms `为权威`, `唯一入口`, `为准` and `定稿`. Scanning 7,292 local Markdown files found no line with one of these terms and a historical path.
- Bootstrap installs only a core (entry pages, documentation standard, manifest, verifier, and CI where `.github/workflows/` exists). Other tiers move to `assets/skeletons/` and are created when they first have content, following a "Create when" column in the template's `docs/AGENTS.md`. New warnings `documentation-untiered` and `doc-owner-missing` signal content that has outgrown its home; a hard mapping without any owner yet warns instead of blocking.
- `verify` and `audit` output labels results `structure-only`. The references document the uncommitted-work path, checkout-bound previews and the Agent Notes opt-out. The template's documentation standard requires writing shipped plans' conclusions back to current owners.

## 0.2.0 — 2026-09-23

- Kept the skill thin and project-neutral; models supply owner boundaries rather than fixed domain trees.
- Added read-only doctor, snapshot-bound prepared plans, compact review packages and exact-scoped apply with a dry run.
- Added schemas for proposals, plans, reviews and fresh-session results; stale or incomplete approvals are rejected.
- Protected product paths, symlinks, hardlinks, frozen archives and existing historical bodies; caught write errors restore owned bytes.
- Distinguished scaffold readiness from completed current documentation; empty manifests and placeholder authorities now fail their appropriate gates.
- Generated repository-local checks from the maintained CLI to prevent verifier drift.
- Explicitly labeled self-review, synthetic tests, declared reviewer attestations and unperformed independent model assessment.


## 0.1.0 — 2026-09-23

- Added the standards-compliant `dsh-doc-audits` Agent Skill at the repository root for Skillshare-compatible discovery.
- Added `bootstrap`, `migrate`, `sync`, `audit`, and `upgrade` guidance derived from the portable governance core of DeepSeek Harness `dsh-doc`.
- Added a dependency-free Python CLI for repository inspection, migration planning, safe scaffolding, verification, corpus audits, and Git diff impact checks.
- Added repository-local governance assets, Agent Note templates, documentation budgets, code-to-doc mappings, and GitHub Actions.
- Added greenfield, brownfield, drift, preservation, no-doc-impact, exclusion, link, and lifecycle regression fixtures.
- Added DeepSeek Harness MIT attribution and lineage documentation.
