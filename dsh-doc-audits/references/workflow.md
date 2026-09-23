# Workflow

## Common sequence

Use this sequence in every mode:

1. Read root and more-specific `AGENTS.md` files.
2. Inspect repository state, current docs, source, tests, generators, CI, and historical material.
3. Classify each document by one primary job and audience.
4. Build an authority map: fact domain → current owner → evidence source → derivatives.
5. Write a plan before file moves or semantic rewrites.
6. Update the owner first; then repair summaries, navigation, and links.
7. Run deterministic checks.
8. Audit semantics and retrieval cost.
9. For major migrations, run a fresh-session test.
10. Report checks, unresolved conflicts, preserved history, and residual risk.

## `bootstrap`

Use for an empty or near-empty repository.

- Detect manifests, interfaces, storage, deployment, and existing policy evidence.
- Choose a profile and generate only the core structure the project needs.
- Leave unknown product facts explicit; do not invent architecture from framework conventions.
- Install repository-local governance assets and run them before claiming completion.

## `migrate`

Use for an existing repository whose facts are scattered, duplicated, or mixed with implementation history.

- Inventory first and preserve all unowned material.
- Separate current authority from historical evidence before rewriting prose.
- Produce a migration plan containing creates, edits, moves, preserved files, link repairs, and exclusions.
- Scaffold missing current owners, then move facts domain by domain.
- Mark old plans or specs historical and point to the current owner; avoid bulk deletion in the first pass.
- Keep product-code refactoring outside the migration unless separately authorized.

## `sync`

Use after a branch, feature, or release changes the repository.

- Determine the Git range.
- Run the impact mapping check.
- Read changed source and its current documentation owners.
- Update only affected contracts, runbooks, references, summaries, and decisions.
- A soft mapping requires review and an explicit conclusion; a hard mapping requires an owner update or a recorded, reviewable no-impact reason.

## `audit`

Audit is read-only unless repair is explicit.

- Run repository-local verification first.
- Compare claims with source, tests, schemas, manifests, CLI help, and executed commands.
- Separate confirmed drift from inferred gaps.
- Every confirmed finding names both sides of the mismatch.
- Rank operational, security, data, API, and onboarding risk above style polish.
- State surfaces inventoried but not deeply inspected; do not label a shallow sweep complete.

## `upgrade`

Use when the skill's generated assets or governance schema change.

- Compare the target's recorded `skill_version` with the current asset version.
- Refresh generated assets only.
- Preserve project-owned docs and manifest mappings.
- Generate a diff plan before writes and require `--force` only for known generated files.
- Run the target repository's existing verifier before and after the upgrade.

## Major-migration fresh-session test

Give a fresh-context reader only the repository and ask them to locate:

1. project purpose and first commands;
2. high-level architecture;
3. one named subsystem's current behavior and code owner;
4. one deployment or recovery procedure;
5. one lasting decision and its rejected alternatives;
6. the distinction between current and historical documentation;
7. the command that checks documentation governance.

Record wrong authority choices, dead ends, full-corpus scans, and conflicting answers. Fix navigation or ownership, then rerun. Self-simulation is weaker than an independent run and must be labeled accordingly.
