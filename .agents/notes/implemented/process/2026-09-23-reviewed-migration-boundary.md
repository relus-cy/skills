# Agent Note: Reviewed migration boundary

Status: implemented

## Problem

A green structural scaffold can be mistaken for completed semantic migration. Broad overwrite flags and stale plans can also replace project-owned work. Encoding one application's directory tree would reduce reuse and increase the agent's standing context.

## Decision

The agent supplies evidence-backed owner candidates and exact document edits. Scripts gather checkout facts, seal the prepared plan, export a compact review package and enforce approved scope. Ordinary in-place application requires explicit permission; fresh-context or human review remains a declared external judgment. Scaffolds have a distinct status and cannot pass completion.

The standalone verifier is generated from the same source checks as the CLI and scans the same Git-visible files as plan snapshots. Because historical bodies are preserved, a broken link inside `tiers.historical` is a warning rather than an error no reviewed plan could repair. Control files default to the target's `.dsh-doc-audits/`; the tool's first write there adds a `*` `.gitignore`, as CPython's `venv`, pytest and ruff do for their own directories, so no project file is edited and nothing there can be staged by accident. No remote model, project-specific architecture generator, production command execution or automatic publication is introduced.

A prepared plan binds its checkout root, the fingerprints of only the paths it reads or writes (write scope, preserved paths, owners, evidence, current sources, link-repair targets and the manifest, with absent paths bound as absent) and the names of all current-tier documents. The name set is bound because a reviewer judges missing domains and overlaps against it. A review binds `content_digest`, which covers proposal, compiled bytes and that binding but not the checkout location. Apply compares the bound maps themselves, so a plan's stored digest cannot vouch for a stale binding. The guard reads protected historical paths from the manifest's `tiers.historical`, or from the bundled template when there is no manifest. This follows per-resource optimistic concurrency, the recognized best practice (Kubernetes `resourceVersion`, HTTP `If-Match`, `git push --force-with-lease`). Review carry-over follows Gerrit's emerging practice of copying approvals across trivial rebases. It does not follow the mainstream whole-state binding of Terraform saved plans.

## Alternatives considered

**Fixed project templates.** Predictable names would simplify snapshot tests but bias other projects toward one application. Tests instead exercise generic invariants and filesystem behavior.

**Prompt-only enforcement.** A short reminder would be easy to maintain but could not reliably catch a stale checkout, altered plan or path escape.

**Authenticated review platform.** Signing and identity infrastructure could strengthen provenance but would add credential handling and host coupling beyond this skill's scope. Records explicitly remain attestations.

**Whole-repository snapshot binding.** This was the 0.2.0 behavior and matches Terraform's saved-plan staleness check. It is the simplest to reason about, but in a 2026-09-24 brownfield trial any unrelated commit, such as a force-tracked probe report, forced a replan and a new independent review.

**Review bound to the proposal alone.** This would survive more replans. But when evidence changes under an unchanged proposal, a reviewed claim can silently go stale, so bound fingerprints stay in the reviewed digest.

**Configurable historical link severity.** A manifest switch would add schema surface and could restore blocking errors that the write boundary forbids repairing. `exclude` already removes a path from every scan.

**External temporary control directory.** It keeps the checkout untouched, but macOS `/tmp` and `/var` are symlinks that the output check rejects, and exempting system links would complicate that check.

**Project ignore entry.** A line in the project's `.gitignore` or `.git/info/exclude` would also work, but both are files the write boundary otherwise leaves alone.

## Consequences

The main skill stays short, with detail loaded only for the selected workflow. Major migrations gain an explicit plan/review/apply boundary. Stale links in historical records stay visible without failing CI. Unrelated work and new historical documents no longer invalidate a plan, but a content change to an unbound file that should have constrained the plan goes undetected, so evidence lists must name what the owners depend on; ignored files cannot be evidence. A new or removed current document still forces a new plan and review. The structure-only label on verifier output exists because in the 2026-09-24 brownfield trial a clean verify missed all six semantic conflicts the reviewer found. A clean tree is still required to write. Removing a linked worktree also removes its control files; `git clean -fd` keeps them because they are ignored. Scripts cannot prove semantic accuracy, the identity of an external reviewer, or all-file crash atomicity. Separate model evaluation remains necessary for stronger assurance.
