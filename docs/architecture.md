# skills architecture

Status: current authority
Last reviewed: 2026-09-23

## Purpose and boundaries

The repository distributes independent, top-level Agent Skills. `dsh-doc-audits` applies the DSH one-owner documentation method across projects without embedding an application's business domains. Models decide the useful split; target repositories retain their facts and policy.

## Components

```text
Host agent / human reviewer
  -> SKILL.md                 thin task router
  -> references/              selective semantic guidance
  -> schemas/                 plan, review and reader-evidence contracts
  -> scripts/repo_docs.py     inspection, readiness checks and command entry point
       -> workflow_guard.py   snapshots, review binding and scoped filesystem writes
  -> assets/repo-governance/  core installed by bootstrap
  -> assets/skeletons/        starting pages for tiers created on demand

Target repository
  -> docs/governance.yaml     project-owned policy and owner mapping
  -> scripts/verify_docs.py   independent deterministic checks
  -> CI workflow             checks in pull requests and pushes
```

## Flows

Read-only planning gathers the actual checkout and creates an unexecutable draft. The agent authors a proposal; preparation seals it. A compact review package carries candidate boundaries and one exact diff. A separate review approves those bytes before application. The tool does not choose the model or create an approval. Final semantic review and a fresh reader remain outside deterministic proof.

Bootstrap only creates missing core files; other tiers appear when content needs them. Scaffolds have explicit status and fail completion until authored. Audit combines repository-local checks with agent judgment; routine diff synchronization can stay focused on existing owners. Large migrations and generated-asset upgrades use the prepared-plan boundary.

## Verification and generation

The source CLI owns deterministic check functions. `scripts/generate_verifier.py` emits a standalone verifier so installed targets need no global skill, model service or Python dependencies. Unit and filesystem/Git integration tests exercise failures as well as passing paths. [CLI semantics](subsystems/governance-cli.md) owns exact behavior, and [release procedure](runbooks/release.md) owns distribution steps.

## Trust boundaries

Plans and reviewer records are untrusted input until schema, path and digest checks pass. Even valid records cannot authenticate a reviewer. Write protection is a CLI guard, not an OS sandbox. No production command, package install, credential use or Git publication is part of the workflow. Private application data does not belong in this public skills repository.

## Extension policy

Add a deterministic check only when a concrete failure justifies it. Keep semantic rules short and generic. Project-specific migration decisions stay in the target. No fixed WebApp tree, automatic hooks or mandatory collection of external frameworks is imposed.
