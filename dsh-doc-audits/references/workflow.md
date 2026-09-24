# Workflow

## Scope and judgment

Use the smallest workflow that covers the request. Directory names, document counts and business domains are model judgments grounded in the repository. The tool does not choose a model, load external architecture frameworks or call another skill automatically.

## Bootstrap and migration

1. Run `doctor` and inspect root/local instructions, code, tests and current documents. Dirty trees are inspectable but cannot be applied, even as a dry run. Use a separate clean worktree or explicitly authorized in-place checkout. For work in progress, commit it, create the worktree from that commit, then author the proposal there ([migration](migration.md)).
2. `plan` without a proposal emits an unexecutable draft. Write a proposal matching the bundled proposal schema: candidates with evidence and responsibility; exact create/edit/move/demote contents; preserved paths; exact write scope; link repairs; verification, rollback and open conflicts.
3. For an empty repository, record actual user decisions in `user_decisions` and cite them as `decision:<id>`. Never synthesize product decisions from a language or framework. Initialize Git separately before application.
4. Prepare with `plan --proposal`; the script binds the checkout root, the paths the plan reads or writes and the current-document set ([authority review](authority-review.md)). This does not approve the plan.
5. Run `review-pack`. Give its compact metadata and exact diff to a capable fresh-context reviewer or a human. The reviewer checks missing domains, overlaps, over/under-splitting and authority conflicts. The author must not manufacture approval.
6. `apply --dry-run` validates the reviewed plan and its binding. Remove dry-run only when writes are authorized. A stale plan needs `plan --proposal` again; the review carries over only when `content_digest` is unchanged.
7. Application does not execute verification commands, deploy, commit, push or declare semantic completion. Run safe checks separately, inspect the change, then conduct semantic review and the fresh-session assessment.
8. Run `verify --completion --fresh-session <result>` for the final evidence-contract check. Retain the report's limitations; do not turn declared reviewer evidence into a stronger claim.

`bootstrap` remains a create-missing-only convenience for scaffolding. It does not perform semantic migration or provide plan approval. It is suitable for an explicitly requested initial scaffold; use reviewed application for a major brownfield migration. `--force` refuses any differing project-owned target before writing anything. For upgrades, use a prepared plan of the named generated verifier and workflow only.

## Audit

`audit` runs deterministic checks and heuristic corpus warnings; its output labels itself `structure-only`. A clean result says nothing about whether documents match the code. The agent compares claims against code, tests, configuration, safely executed commands and current decisions. Provide both sides of confirmed mismatches, separate inferred gaps, and list uninspected surfaces. Do not modify files without explicit repair authorization.

## Sync

Use `impact --base <ref>` for committed branch differences. It uses Git's merge-base comparison; uncommitted changes are not covered. Read the relevant diff and owner documents. Narrow mappings to actual owners. A documentation touch cannot prove semantic correctness. The current checker has no no-impact-waiver parser; it cannot enforce a prose waiver in a PR. Revisit the mapping or use human review instead of making ritual edits.

## Upgrade

`upgrade` is an agent workflow through plan/review/apply, not a separate automatic CLI command. Re-render or obtain current generated verifier/workflow bytes, compare with the target, then include only intended exact edits. Keep project-specific mappings and commands intact. Never use template force-overwrite to reset filled documentation.
