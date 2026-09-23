# Repository Contract

## Generated structure

The default scaffold is:

```text
README.md
AGENTS.md
docs/
  AGENTS.md
  architecture.md
  backlog.md
  governance.yaml
  subsystems/
  runbooks/
  reference/
.agents/notes/
  README.md
  proposed/
  implemented/
  rejected/
  archived/
scripts/verify_docs.py
.github/workflows/docs-governance.yml
```

Projects may omit optional tiers when their scope does not need them. Existing project-owned entry pages are preserved during brownfield bootstrap.

## `docs/governance.yaml`

The bundled manifest uses JSON syntax in a `.yaml` file. JSON is valid YAML and lets the generated verifier stay dependency-free.

Required top-level fields:

- `schema_version`: integer contract version.
- `authority`: named current-owner paths.
- `tiers.current`: glob patterns for current human-facing docs.
- `tiers.historical`: glob patterns for historical material.
- `agent_notes`: root and lifecycle/status mapping.
- `budgets`: standing-document character ceilings.
- `impact_mappings`: code patterns, owning docs, and `hard` or `soft` level.
- `audit`: corpus-audit thresholds and authority terms.
- `exclude`: paths omitted from corpus scans, such as test fixtures, generated artifacts, and virtual environments.

Optional metadata such as `skill_version`, `profile`, and `project` supports upgrades and reporting.

## Hard and soft mappings

A hard mapping covers contracts where stale docs create meaningful operational or integration risk: public APIs, configuration, deployment, recovery, migrations, storage formats, security controls, or published workflows. A branch that changes mapped code must also change at least one owner or carry a separately reviewed no-impact record outside the generated verifier.

A soft mapping marks areas that require judgment, such as internal modules and non-observable refactors. The verifier warns but does not block.

Mappings are prompts to investigate, not proof that every changed file changes behavior. Keep them narrow enough to avoid ritual edits.

## Generated verifier

`scripts/verify_docs.py` uses only Python's standard library and checks:

- authority paths;
- tier overlap;
- relative Markdown links;
- Agent Note lifecycle and headings;
- document budgets;
- diff-aware impact mappings;
- duplicated long prose across current owners;
- current documents that present historical tiers as current authority.

These corpus checks are deterministic warnings. The global skill still performs broader evidence-based semantic review that a script cannot prove.

## Upgrade boundary

Files copied from `assets/repo-governance/` are generated scaffolding only at creation. After the project fills them with facts, they become project-owned except for clearly generated code such as the verifier and workflow. Upgrades must plan file ownership before overwriting anything.
