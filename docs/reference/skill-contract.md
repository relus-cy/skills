# Skill contract

Status: current authority

## Interface

`dsh-doc-audits/` is a top-level, self-contained Agent Skills bundle. `SKILL.md` owns activation and short task routing; references own detailed judgment criteria; JSON Schemas own control-artifact shape; scripts gather facts and enforce deterministic boundaries. The format follows the published Agent Skills specification. There are no mandatory external skills, model APIs or network services.

## Modes and tools

The agent selects bootstrap, migrate, sync, audit or upgrade. The CLI exposes doctor, inspect, plan, review-pack, bootstrap, apply, verify, audit and impact. Migrate/sync/upgrade are agent workflows; no autonomous domain discovery, prose rewriting or reviewer is hidden behind a CLI name.

A capable model supplies the authority candidates and exact proposal. A separate reviewer supplies judgment. This separation keeps domain knowledge out of scripts and avoids fixed document counts or project-specific names in profiles.

## Safety and assurance

Normal audit is read-only. Prepared plans bind the checkout root and the exact bytes of the paths they read or write; reviews bind plan content, not checkout location. Apply accepts only approved, unchanged, scoped changes and never runs plan-supplied commands. Check results certify deterministic conditions, not semantic correctness. Self-review and self-simulated retrieval need explicit permission and are labeled degraded; an independent review cannot be claimed from author-written fixture JSON.

## Compatibility

Python 3.11+ and Git. JSON-compatible YAML remains the manifest encoding. Control JSON schemas reject missing and unexpected fields. Plan, review-package and review-result schemas are at version 2; version 1 plans and reviews must be prepared and reviewed again. Existing 0.1.0 manifests remain valid when they provide the original required fields with valid nested types. `exclude` is optional. Incomplete scaffolding can pass a structural bootstrap check with warnings and cannot pass completion.

Version 0.3.0 supports optional `authority.glossary` and Matt-style repository owners without adopting an external ticket workflow. The [repository contract](../../dsh-doc-audits/references/repository-contract.md#glossary-authority) owns glossary fallback, tier registration, ADR opt-out and tracker boundaries. Existing `CONTEXT.md` repositories remain supported. External tracker close-out is an agent sync responsibility, not a local-verifier guarantee.

The optional external-code mapping and independent Git range flags extend single-repository impact checks without changing their defaults; see the [mapping contract](../../dsh-doc-audits/references/repository-contract.md#hard-and-soft-mappings). Local link verification now checks supported Markdown section fragments as well as files.

## recall

`recall/` is independent of `dsh-doc-audits`. `disable-model-invocation: true` keeps it manual-only. Its stable interface is `recall/scripts/recall.py` (`list`, `show`, the `RECALL_*_ROOT` store overrides and the `--json` fields); `--help` owns flag details and `tests/test_recall.py` pins behavior. It only reads transcript stores and runs read-only `git` in the target; output is redacted before printing.

## Distribution

Copy or sync the whole `dsh-doc-audits/` directory, including scripts, schemas and references. A target's standalone verifier does not need that directory. The maintained source, templates and local generated verifier must remain consistent.
