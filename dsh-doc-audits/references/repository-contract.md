# Repository Contract

## Generated structure

Bootstrap installs a core, the set of files in `assets/repo-governance/`:

```text
README.md
AGENTS.md
docs/
  AGENTS.md
  governance.yaml
scripts/verify_docs.py
.github/workflows/docs-governance.yml   # only if .github/workflows/ exists
```

Every other tier is created when it first has content, as the table in the installed `docs/AGENTS.md` assigns; `assets/skeletons/` holds a starting page for each. The manifest already lists all tiers, so creating one never needs a manifest edit. Existing project-owned entry pages are preserved during brownfield bootstrap.

## `docs/governance.yaml`

The bundled manifest uses JSON syntax in a `.yaml` file. JSON is valid YAML and lets the generated verifier stay dependency-free.

Required top-level fields:

- `schema_version`: integer contract version.
- `authority`: named current-owner paths.
- `tiers.current`: glob patterns for current human-facing docs.
- `tiers.historical`: glob patterns for historical material. The plan guard reads this list: matching paths cannot be edited, moved or proposed as owners. The template lists only generic names; add the project's own planning or history folders.
- `agent_notes`: root and lifecycle/status mapping.
- `budgets`: standing-document character ceilings.
- `impact_mappings`: code patterns, owning docs, and `hard` or `soft` level.
- `audit`: corpus-audit thresholds and authority terms.
Optional `exclude`: paths omitted from corpus scans, such as test fixtures, generated artifacts, and virtual environments.

Optional metadata such as `skill_version`, `profile`, and `project` supports upgrades and reporting.

### Agent Notes opt-out

The `agent_notes` block is always required, but nothing else about Agent Notes is. A repository whose policy forbids decision records keeps the block and never creates `.agents/notes/`; the verifier checks Notes only where that directory exists. Name the Markdown home for decision rationale, such as `docs/decisions/`, in `docs/AGENTS.md` and list it under `tiers.current`. The fresh-session assessment must still answer the `decision` topic from a repository Markdown page, so rationale kept only in PRs, or nowhere, fails completion.

## Hard and soft mappings

A hard mapping covers contracts where stale docs create meaningful operational or integration risk: public APIs, configuration, deployment, recovery, migrations, storage formats, security controls, or published workflows. A branch that changes mapped code must also change at least one owner or stop for human review. The current verifier does not parse no-impact waivers.

A soft mapping marks areas that require judgment, such as internal modules and non-observable refactors. The verifier warns but does not block.

Either level only warns, with `doc-owner-missing`, while no existing file matches its owning patterns: the tier has not been created yet.

Mappings are prompts to investigate, not proof that every changed file changes behavior. Keep them narrow enough to avoid ritual edits.

## Generated verifier

`scripts/verify_docs.py` uses only Python's standard library and checks:

- manifest nested types and authority paths;
- scaffold/current/completion readiness;
- tier overlap;
- relative Markdown links;
- Agent Note lifecycle and headings;
- document budgets;
- diff-aware impact mappings;
- duplicated long prose across current owners;
- current documents that present historical tiers as current authority;
- `docs/*.md` pages matched by neither tier (`documentation-untiered`).

These corpus checks are deterministic warnings. The global skill still performs broader evidence-based semantic review that a script cannot prove.

A green result is structure-only. `verify` and `audit` output, and the local verifier's output, carry an `assurance` field beginning `structure-only`. No check compares a document's claims with code, configuration or behavior. Never report a pass as documentation accuracy.

## File scope and links

At a Git worktree root, checks read the files Git lists: tracked files plus untracked files that are not ignored, as plan snapshots do. Other directories are walked in full. `exclude` narrows either set.

Link checks skip fenced code blocks and inline code spans. A fence opens with three or more backticks or tildes, including one indented under a list item or blockquote; only the same character repeated at least as often closes it.

A missing or outside-repository link target is an error, except in files matched by `tiers.historical`. First-pass migration preserves historical bodies (authority review, write boundary), so the workflow cannot repair such a link: it is reported as a warning with `tier: historical`, also under `--completion`. Add the path to `exclude` only when even the warning is unwanted; that removes it from every scan.

## Upgrade boundary

Files copied from `assets/repo-governance/` are generated scaffolding only at creation. After the project fills them with facts, they become project-owned except for clearly generated code such as the verifier and workflow. Upgrades must plan file ownership before overwriting anything.
