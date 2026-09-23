# Authority review and application

## What the model decides

Each candidate records `id`, `path`, `tier`, `responsibility`, `evidence`, `current_sources`, and `separation_reason`. Evidence lists existing repository files or `decision:<id>` entries recorded from user decisions. A candidate without evidence is rejected. A generic profile changes no directory counts or business names.

## Artifacts and commands

JSON Schemas live in the bundle's `schemas/` directory: `proposal.schema.json`, `migration-plan.schema.json`, `review-package.schema.json`, `review-result.schema.json`, and `fresh-session-result.schema.json`. The dependency-free validator supports exactly the schema subset used here and rejects unsupported keywords. This is not a general-purpose JSON Schema implementation.

Control artifacts must be outside the target or inside its untracked `.dsh-doc-audits/`. Prefer an external temporary directory for large review packages. No production secrets should enter proposal bodies, diffs or review reports.

The proposal's `files` object contains:

| Field | Entry |
| --- | --- |
| `create` | `{path, content, reason}`; target must not exist |
| `edit` | `{path, content, reason}`; target must exist |
| `move` | `{from, to, reason}`; move preserves source bytes |
| `demote_to_historical` | `{path, content, reason}`; content prepends historical/owner metadata and retains the complete original body |
| `preserve` | Exact paths that must not also be written |

`write_scope` lists exact paths, including both sides of a move. `link_repairs` lists `{path, targets}` with repository-relative target paths. `verification` and `rollback` are reviewer instructions; no commands in them are executed. `open_conflicts` blocks application. Separate conflict-free work into its own plan.

`plan --proposal` seals a prepared plan. Its snapshot covers Git HEAD, branch, checkout root and hashes/modes of tracked and non-ignored untracked files. Git-ignored runtime files are outside that snapshot; tracked files remain covered even when an ignore pattern matches. The untracked control directory is excluded. No timestamps alone serve as proof of freshness.

`review-pack` contains candidates, scope, operations, preserved paths and one exact diff. It omits duplicate full-document bodies and the full repository fingerprint map. Reviewers can read more of the referenced repository when needed.

## Reviewer output

Use an actual separate reviewer. An approval result has this shape:

```json
{
  "schema_version": 1,
  "plan_digest": "<copy the exact prepared plan digest>",
  "verdict": "approve",
  "reviewer": {"kind": "independent-agent", "identity": "<actual model or reviewer>", "context_id": "<fresh session identifier>"},
  "missing_domains": [],
  "over_split_owners": [],
  "under_split_owners": [],
  "authority_conflicts": [],
  "required_changes": [],
  "summary": "<evidence-based review conclusion>"
}
```

This is a shape example, not an approval to copy. `revise` or `block`, a mismatched digest, nonempty findings, or the author's same context claiming independence all prevent application. A human may use `kind: human`. Self-review uses `kind: self` and needs explicit `--allow-self-review`; the receipt says `degraded-self-review`.

A hash binds review to bytes. It does not authenticate the reviewer or prove that a model actually reviewed those bytes. Reviewer identity and conclusions are attestations. Use your host's independent sessions and access controls; do not put signing or model credentials in this skill.

## Write boundary

Application accepts root `README.md`, `AGENTS.md`, `CONTEXT.md`, Markdown under `docs/` and active `.agents/notes/`, `docs/governance.yaml`, `scripts/verify_docs.py`, and `.github/workflows/docs-governance.yml`. It rejects product files, Git metadata, traversal, symlink paths, hardlinked targets, unsupported file types and frozen archives. The default narrow scope is deliberate; module-local documentation outside it needs a separately reviewed scope extension.

Existing historical plans/reports/releases cannot be rewritten or moved by first-pass migration. Metadata-only demotion keeps their body. All targets are checked before writes. Clean ordinary checkouts require `--allow-in-place`; linked worktrees do not. Neither mode permits dirty product work.

Writes replace one file atomically and restore owned bytes after caught in-process failures. There is no multi-file crash transaction, OS sandbox or protection against a hostile concurrent process. An interrupted process can leave `.dsh-doc-audits/apply.lock`; inspect the diff and restore only affected paths before clearing it. Never run `git reset --hard` or `git clean` to hide partial work.

A second application against the exact post-apply snapshot is a no-op. New commits or intervening changes can invalidate the snapshot; safely replan rather than force the old approval. Application always leaves migration completion pending.

## Fresh-session result

After authoring, ask a fresh-context reader to find: purpose/first commands, architecture, one subsystem, one operation, one durable decision with alternatives, current/history distinction, and verification entry point. Use topic identifiers `purpose`, `architecture`, `subsystem`, `operations`, `decision`, `authority`, `verification` exactly once. Each answer includes its text and existing Markdown evidence paths. For an inapplicable topic, explain why and cite the document explicitly recording that limitation.

Record `schema_version: 1`, the post-migration `snapshot_digest` from `doctor`, the actual `reviewer`, `verdict: pass|fail`, `answers: [{topic, answer, evidence}]`, and `limitations`. Store the result in the control area so it does not change the snapshot. `verify --completion --fresh-session <file>` rejects missing, malformed, incomplete or stale evidence. Self-simulation needs explicit opt-in and remains degraded. The tool validates evidence shape and freshness, not whether the answers are semantically correct; the reader must actually perform this check.
