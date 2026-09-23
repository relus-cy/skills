# Governance CLI

Status: current authority
Owner paths: `dsh-doc-audits/scripts/repo_docs.py`, `dsh-doc-audits/assets/repo-governance/scripts/verify_docs.py`

## Purpose

The CLI turns the semantic governance model into safe, repeatable repository operations. It inventories repositories, proposes a migration plan, installs missing assets, checks deterministic invariants, audits selected corpus risks, and evaluates Git diff impact mappings.

## Public boundary

Run the bundled CLI with Python:

```bash
python dsh-doc-audits/scripts/repo_docs.py <command> --repo <path>
```

Commands are `inspect`, `plan`, `bootstrap`, `verify`, `audit`, and `impact`. `--json` returns stable machine-readable results. `bootstrap` supports `--dry-run` and `--force`; `impact` requires `--base` and accepts `--head`.

## Safety semantics

- `inspect`, `plan`, `verify`, `audit`, and `impact` are read-only.
- `bootstrap` creates missing files and preserves differing existing files.
- `--force` updates template-owned collisions and must be used only after reviewing the plan.
- Repeated bootstrap runs classify equal files as `unchanged` and create no duplicates.
- The CLI never edits product code or automatically deletes historical material.

## Verification semantics

`verify` checks governance manifest parsing, authority paths, current/historical overlap, relative Markdown links, Agent Note lifecycle and headings, and Unicode-character budgets. The generated repository-local verifier runs the same core checks and also reports duplicate-prose and historical-authority warnings in one pass.

`impact` reads `impact_mappings` from `docs/governance.yaml`. A changed hard-mapped code path with no changed owner document is an error; a soft mapping is a warning.

`audit` includes deterministic findings and additionally reports repeated long prose across current owners and current docs that describe historical tiers as present authority.

## Failure behavior

Invalid paths, missing templates, malformed governance manifests, or failed Git commands produce a nonzero CLI exit and a concrete error. Verification commands return exit code `1` when findings contain an error; usage and I/O failures return `2`.

## Related decisions

The portable governance boundary and JSON-compatible YAML choice are recorded in [the implemented Agent Note](../../.agents/notes/implemented/process/2026-09-23-portable-dsh-doc-governance.md).
