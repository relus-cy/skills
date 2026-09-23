# Skill contract

Status: current authority

## Interface

`dsh-doc-audits/` is a top-level, self-contained Agent Skills bundle. `SKILL.md` owns activation and short task routing; references own detailed judgment criteria; JSON Schemas own control-artifact shape; scripts gather facts and enforce deterministic boundaries. The format follows the published Agent Skills specification. There are no mandatory external skills, model APIs or network services.

## Modes and tools

The agent selects bootstrap, migrate, sync, audit or upgrade. The CLI exposes doctor, inspect, plan, review-pack, bootstrap, apply, verify, audit and impact. Migrate/sync/upgrade are agent workflows; no autonomous domain discovery, prose rewriting or reviewer is hidden behind a CLI name.

A capable model supplies the authority candidates and exact proposal. A separate reviewer supplies judgment. This separation keeps domain knowledge out of scripts and avoids fixed document counts or project-specific names in profiles.

## Safety and assurance

Normal audit is read-only. Prepared plans bind exact bytes and checkout state. Apply accepts only approved, unchanged, scoped changes and never runs plan-supplied commands. Check results certify deterministic conditions, not semantic correctness. Self-review and self-simulated retrieval need explicit permission and are labeled degraded; an independent review cannot be claimed from author-written fixture JSON.

## Compatibility

Python 3.11+ and Git. JSON-compatible YAML remains the manifest encoding. Control JSON schemas reject missing and unexpected fields. Existing 0.1.0 manifests remain valid when they provide the original required fields with valid nested types. `exclude` is optional. Incomplete scaffolding can pass a structural bootstrap check with warnings and cannot pass completion.

## Distribution

Copy or sync the whole `dsh-doc-audits/` directory, including scripts, schemas and references. A target's standalone verifier does not need that directory. The maintained source, templates and local generated verifier must remain consistent.
