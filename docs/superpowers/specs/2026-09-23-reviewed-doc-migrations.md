# Reviewed documentation migrations

Status: approved scope; implementation authorized in the conversation.

## Goal

Keep dsh-doc-audits thin: the agent judges how to split a repository, while Python gathers evidence and validates write boundaries. Add a portable, reviewable workflow without embedding any project's domain names or folder counts.

## Contract

- Python 3.11+ standard library and Git; no model SDK, external service, automatic hooks, production commands, pushes, or dependency installation.
- `doctor` is read-only and reports repository root, HEAD, branch, worktree, dirty state, runtime, governance presence and planning/application blockers. Planning remains available on dirty repositories; application requires a clean worktree and an isolated worktree or explicit in-place permission.
- `plan` emits a draft without invented owners. An agent supplies generic authority candidates, exact file contents and actions. A prepared plan binds those bytes, evidence paths, write scope and a Git/content snapshot to a digest.
- `review-pack` exports the sealed plan, exact diff and focused review questions. A separate reviewer supplies approve/revise/block and findings bound to that digest. Self-review needs explicit opt-in and is always reported as degraded. Neither a JSON document nor a hash authenticates reviewer identity or proves semantic correctness.
- `apply` accepts only a prepared, approved, unchanged plan. Paths are canonical relative paths, exact-scoped, and restricted to documentation plus named verifier/CI assets. Symlinks, traversal, product files and frozen archives are rejected. No shell commands from plans are executed. Preflight all operations; rollback on caught in-process write failure. Per-file replacement is atomic; multi-file crash recovery is a documented limitation.
- Scaffolding is not migration completion. Scaffold status is allowed during bootstrap and blocks completion. Current-authority placeholder prompts block ordinary verification. Do not ban legitimate TODO identifiers in code examples or quoted history.
- Repository-local checks remain dependency-free. Completion additionally requires a fresh-session result bound to the post-migration snapshot; independent assessment is not manufactured by this tool.
- Existing historical materials are preserved. Semantic conflicts pause the affected domain; independent, conflict-free work may be planned separately.
- Safe repeat execution is detected and returns already-applied without duplicate writes. Changed evidence or outputs invalidate approvals.

## Non-goals

No code restructuring, fixed WebApp output tree, automated expert system, runtime model selection, or deployment execution. No production chanapp migration in this release.

## Acceptance

Exercise actual temporary Git repositories: clean/dirty/worktree/unborn; plan sealing; stale snapshot, altered review and revision verdicts; allowed/forbidden/symlink paths; dry-run, idempotence and rollback; scaffold/current/completion checks; standalone verifier and full CLI round-trip. Run the old suite too. Publish a full-history Git bundle and verify import in a clean clone. Report absence of independent model eval honestly.
