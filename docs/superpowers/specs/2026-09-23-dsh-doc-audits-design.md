# dsh-doc-audits Design

Status: approved
Date: 2026-09-23

## Purpose

`dsh-doc-audits` is a portable Agent Skill for bootstrapping, migrating, synchronizing, and auditing repository documentation governance. It generalizes the governance core of DeepSeek Harness `dsh-doc` while removing DeepSeek-specific bilingual, Cordis package, VitePress, and pnpm assumptions.

The skill must leave every target repository self-governing: project facts and rules live in the target repository, deterministic checks run without the skill, and CI can block documentation drift even when the skill is not loaded.

## Design principles

1. One durable fact has one current owner; other documents link to that owner.
2. Current-state documentation, decision rationale, historical process, and generated reference are separate tiers.
3. Operational claims require executable or source-backed evidence.
4. Machine-checkable constraints belong in repository-local scripts and CI; judgment belongs in the skill.
5. Migration is report-first, non-destructive, idempotent, and preserves unowned documents.
6. Ordinary docs describe current behavior. Agent Notes preserve durable why and trade-offs. Historical plans and reports stay historical.
7. A fresh-context agent must be able to reconstruct the relevant system path through a small number of linked pages.

## Supported modes

- `bootstrap`: initialize governance in an empty or near-empty repository.
- `migrate`: inventory a brownfield repository, propose authority ownership, scaffold the target structure, and guide semantic migration.
- `sync`: map a Git diff to affected documentation owners.
- `audit`: compare current documentation with source, tests, commands, and governance rules without modifying files by default.
- `upgrade`: update generated governance assets while preserving project-owned content.

## Skill layout

The repository is multi-skill ready. The initial skill lives at `dsh-doc-audits/` and contains:

- `SKILL.md`: concise activation and workflow entry point.
- `references/`: governance model, mode rules, audit rubric, repository contract, Agent Note lifecycle, and profile guidance.
- `assets/`: target-repository templates.
- `scripts/repo_docs.py`: dependency-free CLI for inspect, plan, bootstrap, verify, audit, and impact checks.
- `agents/openai.yaml`: optional client metadata.

## Target repository contract

A governed repository may contain:

```text
AGENTS.md
README.md
CONTEXT.md                         # optional glossary
docs/
  AGENTS.md
  architecture.md
  backlog.md
  governance.yaml                 # JSON-compatible YAML
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

`docs/governance.yaml` is intentionally JSON-compatible YAML so the verifier can use Python's standard library. Projects may replace it with conventional YAML only if they also provide a parser dependency and update the verifier contract.

## Deterministic checks

The repository-local verifier checks:

- required authority files exist;
- current and historical tiers do not overlap;
- local Markdown links resolve;
- Agent Note path, status, and required headings agree;
- implemented notes do not contain proposal-only headings;
- character budgets are respected;
- hard code-to-doc mappings are updated for a selected Git diff;
- duplicate long prose blocks are reported;
- current docs do not designate historical paths as current authority.

## Migration safety

- Default operations are read-only or create-missing-only.
- Existing files are never overwritten without `--force`.
- Historical files are preserved; semantic demotion is an Agent task, not a blind script rewrite.
- The script writes a plan before applying scaffolding.
- Re-running the same command produces no duplicate files or content.
- Product code is out of scope unless the user separately authorizes it.

## Validation strategy

Tests use disposable repositories and cover:

1. greenfield bootstrap;
2. brownfield inventory and plan generation;
3. preservation of existing files;
4. broken links and missing authorities;
5. Agent Note lifecycle violations;
6. hard mapping drift;
7. duplicate prose and historical-authority leakage;
8. skill metadata and repository structure.

The test suite uses only Python standard-library `unittest` and Git.

## Attribution

The governance model is inspired by DeepSeek Harness `dsh-doc`, `docs/AGENTS.md`, and Agent Note lifecycle rules. DeepSeek Harness is MIT-licensed. This repository includes the relevant attribution and license notice while reimplementing the portable workflow in original form.
