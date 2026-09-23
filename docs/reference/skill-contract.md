# dsh-doc-audits skill contract

Status: current authority
Source owner: `dsh-doc-audits/`

## Skill identity

- Directory: `dsh-doc-audits/`
- Frontmatter name: `dsh-doc-audits`
- Version: `0.1.0`
- License: MIT
- Runtime requirement: Python 3.11+ and Git for diff-aware checks

## Activation scope

Use the skill for repository documentation bootstrap, brownfield migration, Git-diff synchronization, read-only corpus audit, and governance asset upgrades. It does not replace product design, code architecture implementation, or general prose editing.

## Resource contract

- `SKILL.md`: mode selection, standing rules, commands, completion contract.
- `references/`: focused semantic standards read on demand.
- `scripts/repo_docs.py`: dependency-free deterministic CLI.
- `assets/repo-governance/`: target-repository templates.
- `agents/openai.yaml`: optional client display metadata.

## Target manifest

`docs/governance.yaml` is JSON-compatible YAML. Schema version `1` defines named authority paths, current and historical glob tiers, Agent Note lifecycle mapping, character budgets, hard and soft code-to-doc impact mappings, and audit thresholds.

## Exit codes

- `0`: command completed and no blocking verification error exists.
- `1`: `verify`, `audit`, or `impact` found at least one blocking error.
- `2`: invalid arguments, missing paths, malformed input, or execution failure.

## Compatibility promise

Within `0.x`, command names and result fields may expand, but existing safety defaults remain: audit is read-only, bootstrap preserves existing files, and product code is out of scope. A schema change increments `schema_version` and requires an upgrade path.
