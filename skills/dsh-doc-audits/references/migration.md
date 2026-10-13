# Migration rules

## Before changes

Use read-only `doctor`, inspection and an unexecutable draft first. The model then proposes owners and exact edits with concrete repository evidence. Preserve the existing policy until a reviewed migration explicitly replaces it. Profiles are hints; they never prescribe business names or a fixed number of documents.

## Safe order

Prepare all new owners, routing changes, metadata-only historical demotions and link repairs in the same reviewed plan. Do not leave two current owners of the same fact. Preserve original historical bodies, production paths and frozen archives. Unknown production configuration remains unverified; source defaults do not override deployed evidence.

## Application

The prepared plan binds content and repository state as [authority review](authority-review.md) describes. Reviewer approval binds its `content_digest`. `apply --dry-run` checks the whole write set before any change. Then the authorized write run applies only that set. It does not execute commands embedded in documents or verification lists.

Dirty repositories can be inspected. Move actual application to a clean worktree, or use explicit in-place permission on a clean checkout. Stop on changed bound files, unresolved domain conflicts or a review verdict other than approve. Split independently decidable work into another plan instead of suppressing findings.

## Uncommitted work

`apply` refuses a dirty tree, including with `--dry-run`, and a plan prepared in a dirty tree never applies. A linked worktree is created from a commit, so it cannot see uncommitted work. When the migration must build on work in progress:

1. Commit the work in progress on its own branch in the original checkout.
2. Create a worktree on a new branch from that commit: `git worktree add -b <branch> <path> <commit>`. A detached worktree cannot record the migration commit on a branch.
3. Author the proposal in that worktree. A demotion's content must end with the post-WIP body, byte for byte, because the check is `content.endswith(<current body>)`.

## Preview

A plan applies only in the checkout that prepared it (`plan belongs to another checkout`), so a scratch clone cannot preview a change for the real repository. Preview in the real clean worktree: the review package's `diff` plus the `would_change` list from `apply --dry-run`. Unrelated commits keep the plan valid. Replanning an unchanged proposal against identical bound files, for example in a fresh worktree, keeps the existing review.

## Completion and rollback

Apply returns a pending-verification receipt, never a completed migration. Run local checks, semantic review and a fresh-session assessment. Record all unverified operational claims and actual reviewer limitations. Scaffolds cannot pass completion.

The tool restores its own changes after a caught write error. It cannot guarantee all-file atomicity after process termination or power loss. Inspect interrupted work and recover individual paths from Git or the plan's original snapshot. Preserve unrelated work. Never delete history or use force-push as recovery.
