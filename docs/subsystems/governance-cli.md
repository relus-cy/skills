# Governance CLI

Status: current authority
Owner paths: `dsh-doc-audits/scripts/repo_docs.py`, `dsh-doc-audits/scripts/workflow_guard.py`

## Boundary

Run `python dsh-doc-audits/scripts/repo_docs.py <command> --repo <path>`. `doctor`, `inspect`, `plan`, `review-pack`, `verify`, `audit` and `impact` inspect the target; explicitly selected control outputs are the only writes in planning. `bootstrap` creates scaffolds. `apply` executes an exact prepared and reviewed document change. Python 3.11+ and Git are required, with no third-party runtime dependencies. At a Git worktree root, `inspect`, `verify` and `audit` read the same file set as plan snapshots: tracked plus untracked non-ignored files. Other directories are walked in full.

## Plan and review

`plan` emits a draft with empty owner candidates. `--proposal <json>` accepts model-authored candidates and full changes, validates the schema and evidence, and binds the checkout/content to a digest. `review-pack --plan <json>` exports focused metadata and one exact diff. A separate human or fresh agent supplies the digest-bound review result. The tool cannot authenticate that reviewer or infer semantic correctness.

## Execution

`apply --plan <json> --review <json> --dry-run` preflights the reviewed contents. A write run requires a clean Git root and either a linked worktree or explicit `--allow-in-place`. Self-review is rejected without explicit `--allow-self-review` and is marked degraded. Changed snapshots, unresolved conflicts, non-approve verdicts and altered plans stop application. Control files belong in the target's `.dsh-doc-audits/`; the first control write there adds a `.gitignore` of `*`, so Git ignores the directory. Links above the repository root are followed as for `--repo`; below it, and anywhere on a path outside the target, symlinks are rejected.

The write set is exact, documentation-only, with narrowly named verifier/CI exceptions. Symlinks, hardlinks, traversal, product files, frozen archives and first-pass historical rewrites are rejected. A repeat against the exact post-apply snapshot returns already-applied. No verification, deployment, commit or publication commands are executed from a plan. Per-file replacement is atomic; caught failures restore owned bytes. Multi-file crash atomicity and hostile-concurrent-writer protection are outside the tool's guarantees.

## Verification

The verifier checks nested manifest types, owner existence, tier overlap, local Markdown paths, Note headings/status, budgets and unfinished current documents. Explicit scaffold status produces a normal warning and a completion error. Quoted history and fenced examples are excluded from authoring-prompt detection. Link checks skip fenced code blocks and inline code spans. Broken links in `tiers.historical` are warnings, because migrations preserve those bodies. These are bounded heuristics, not a proof of prose quality.

`audit` adds duplicate-prose and historical-authority warnings and still requires agent semantic review. `impact --base <ref> [--head <ref>]` uses committed three-dot Git differences and narrow owner mappings; a matching doc edit does not prove its accuracy. No PR no-impact waiver is parsed.

`verify --completion --fresh-session <json>` requires all seven documented retrieval topics and a current snapshot. Results declare reviewer assurance and limitations; fabricated reviewer attestations cannot be detected cryptographically by this tool. Missing independent assessment must remain visible.

## Repository-local generation

`scripts/generate_verifier.py` selects the actual deterministic check functions from the CLI and creates both the bundled template and this repository's standalone verifier. `--check` fails on drift. Targets receive one Python file, without this skill or its planning module. The local `--completion` checks document readiness only; fresh-session evidence validation belongs to the global workflow.

## Failure and recovery

Findings return exit 1. Invalid inputs, schema failures, stale approvals and unsafe operations return exit 2. `apply` never claims full migration completion. `--force` during bootstrap refuses differing project-owned documents before writes; use reviewed generated-asset edits for upgrades. Detailed workflow contracts live in the skill's one-hop references and schemas.
