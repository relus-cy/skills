# skills architecture

Status: current authority
Last reviewed: 2026-09-23

## Purpose and boundaries

This repository distributes reusable Agent Skills. Each skill is self-contained in a top-level `<name>/` directory and follows the Agent Skills directory contract: `SKILL.md` provides activation and core instructions, while `scripts/`, `references/`, and `assets/` are loaded or executed only when needed.

The initial skill, `dsh-doc-audits`, governs documentation architecture in other repositories. It does not own those repositories' product facts. It installs repository-local rules and deterministic checks, then leaves project-specific semantic ownership with the target repository.

## Component map

```text
Agent runtime
  → dsh-doc-audits/SKILL.md
      → references/                 semantic governance and mode rules
      → scripts/repo_docs.py        inspect, plan, bootstrap, verify, audit, impact
      → assets/repo-governance/     portable target-repository scaffold

Repository development
  → tests/                          deterministic behavior and scenario fixtures
  → scripts/verify.sh               one-command local gate
  → .github/workflows/              CI gates
  → docs/                           current architecture, contracts, and runbooks
  → .agents/notes/                  durable decision rationale
```

## Primary flows

### Bootstrap or migrate a target repository

The agent reads the skill and the relevant mode reference, runs `repo_docs.py inspect` and `plan`, reviews the authority map, then runs `bootstrap`. The script creates missing governance assets and preserves conflicting existing files. The agent performs semantic migration; the script does not blindly rewrite historical prose.

### Verify and audit

The target repository's generated `scripts/verify_docs.py` checks deterministic invariants and reports selected corpus warnings without requiring the global skill. The bundled `repo_docs.py verify` provides the deterministic subset, while `audit` adds the same duplicate-prose and historical-authority checks for scoped or external runs. Detailed behavior belongs to [the governance CLI subsystem](subsystems/governance-cli.md).

### Develop and release the skill

Changes start with tests, run through `bash scripts/verify.sh`, and pass the same repository-local governance gates the skill installs elsewhere. Release steps belong to [the release runbook](runbooks/release.md).

## Trust and write boundaries

The global skill may read a target repository and create governance scaffolding. Existing files are preserved by default; overwrites require explicit `--force`. Product-code changes, GitHub publication, and destructive document cleanup remain separate authorized actions.

The generated verifier uses JSON-compatible YAML and Python's standard library. This trades conventional YAML comments for deterministic, dependency-free execution.

## Extension points

New repository profiles add focused guidance and mappings without changing the core one-owner model. New deterministic checks require a failing fixture first, a repository-local equivalent when appropriate, and documentation in the subsystem and reference contracts.
