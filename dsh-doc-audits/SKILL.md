---
name: dsh-doc-audits
description: Use when bootstrapping, migrating, synchronizing, auditing, or upgrading repository documentation governance; when current facts are mixed with historical plans; or when code changes may have left documentation stale.
license: MIT
compatibility: Requires Python 3.11+ for bundled deterministic checks and Git for diff-aware impact analysis.
metadata:
  author: relus-cy
  version: "0.1.0"
  lineage: deepseek-harness-dsh-doc
---

# DSH Doc Audits

## Overview

Build and maintain an agent-readable documentation control plane around one rule: **each durable fact has one current owner**. Keep current behavior, decision rationale, historical process, and generated material in separate tiers. Put deterministic constraints in the target repository so governance survives when this skill is not loaded.

## Select a mode

- **bootstrap** — create governance in an empty or near-empty repository.
- **migrate** — classify and restructure an existing documentation corpus without deleting history.
- **sync** — map a Git diff to the current documentation owners that may need updates.
- **audit** — compare docs with code, tests, commands, and governance rules; stay read-only unless repair is explicitly requested.
- **upgrade** — refresh generated governance assets while preserving project-owned content.

Read [workflow.md](references/workflow.md) for the selected mode before changing files. For existing repositories, also read [migration.md](references/migration.md).

## Standing rules

1. Read root and more-specific `AGENTS.md` files before repository content.
2. Inventory current docs, source, tests, generated artifacts, and historical material before choosing owners.
3. Assign every durable fact to the nearest current owner; replace duplicates with links.
4. Verify commands, defaults, paths, APIs, and error behavior from the current checkout. Record unavailable verification instead of guessing.
5. Ordinary docs state current behavior. Agent Notes retain durable rationale and trade-offs. Plans, reports, handoffs, and postmortems retain history.
6. Create or update the owner before derivative entry points such as README summaries.
7. Run deterministic checks before semantic review, then perform a fresh-session retrieval test for major migrations.
8. Do not modify product code during a documentation migration unless separately authorized.

Read [governance-core.md](references/governance-core.md) for tier ownership and [agent-notes.md](references/agent-notes.md) for lifecycle rules.

## Repository tooling

Run the bundled tool through Python; do not rely on executable bits:

```bash
python scripts/repo_docs.py inspect --repo <path>
python scripts/repo_docs.py plan --repo <path> --profile small-web-app
python scripts/repo_docs.py bootstrap --repo <path> --profile small-web-app
python scripts/repo_docs.py verify --repo <path>
python scripts/repo_docs.py audit --repo <path>
python scripts/repo_docs.py impact --repo <path> --base <ref>
```

Use `--json` for machine-readable output and `--dry-run` before writes. Existing files are preserved unless `--force` is explicit.

Read [repository-contract.md](references/repository-contract.md) before installing governance assets, [profile-small-web-app.md](references/profile-small-web-app.md) when that profile fits, and [audit-rubric.md](references/audit-rubric.md) before claiming a corpus is current. [lineage.md](references/lineage.md) records what was retained from and removed from DSH.

## Completion contract

A migration or bootstrap is complete only when:

- current owners and historical tiers are explicit;
- repository-local verification runs without this skill;
- every documented command was executed or marked unverified with an owner;
- links, Agent Note lifecycle, budgets, and diff mappings pass;
- a fresh-context reader can find architecture, subsystem behavior, operations, and decision rationale without scanning the whole repository;
- the final report lists checks run, unresolved authority conflicts, residual risk, and preserved historical material.

## Common mistakes

- Treating the skill as the authority instead of generating repository-local rules.
- Moving prose before deciding its owner.
- Rewriting historical plans into current docs while losing rationale or evidence.
- Requiring docs changes for every internal refactor instead of using hard and soft impact mappings.
- Editing generated output instead of its source.
- Calling a link check a semantic audit.
