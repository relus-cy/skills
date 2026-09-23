# skills

Reusable Agent Skills maintained by `relus-cy`. Each skill is a top-level directory for simple discovery and synchronization.

## dsh-doc-audits · 0.2.0

A thin, portable adaptation of DeepSeek Harness documentation governance: one current owner per durable fact; separate current behavior, decision rationale and historical work. A capable model decides how to split a project. Local tools validate evidence, reviewed plans, write boundaries and documentation readiness.

Use it to initialize a documentation scaffold, migrate an existing repository, synchronize changed contracts, audit drift or upgrade generated governance assets. No fixed WebApp layout, project-specific domain names, mandatory external skill, model service or network access is built in.

## Install and use

Sync or copy the complete `dsh-doc-audits/` directory to your Agent Skills location. Keep its scripts, schemas, references and assets together. Then give your agent this request:

```text
Use dsh-doc-audits to migrate this repository's documentation. Derive the
smallest useful owner structure from source and existing docs. Prepare and
review the plan before applying it; preserve history and product code.
Report actual verification and any missing independent assessment.
```

For read-only inspection from this checkout:

```bash
python dsh-doc-audits/scripts/repo_docs.py doctor --repo /path/to/project --json
python dsh-doc-audits/scripts/repo_docs.py plan --repo /path/to/project --json
```

`plan` starts as an unexecutable draft. The agent authors a proposal; `plan --proposal` seals it, `review-pack` supplies a focused review diff, and `apply` requires a separate approval of the unchanged plan. See the [skill entry](dsh-doc-audits/SKILL.md) and [review/application contract](dsh-doc-audits/references/authority-review.md).

## What is verified

Scaffolding is explicitly marked and cannot pass migration completion. Prepared plans protect exact file scope and detect stale checkouts. The standalone verifier checks structure and bounded drift signals without this global skill. Semantic correctness and reviewer identity remain human/agent responsibilities; an approval JSON is not authenticated proof. No deployment, hooks, package installation, commit or push runs automatically.

## Maintain and verify

```bash
bash scripts/verify.sh
python scripts/smoke_reviewed_workflow.py
```

Only Python 3.11+ standard library and Git are required. The smoke test uses synthetic review evidence, not a live independent model. The final migration workflow validates real fresh-session evidence supplied by the host.

[Architecture](docs/architecture.md) · [CLI contract](docs/subsystems/governance-cli.md) · [Skill contract](docs/reference/skill-contract.md) · [Release procedure](docs/runbooks/release.md) · [Changelog](CHANGELOG.md)

See `LICENSE` and `THIRD_PARTY_NOTICES.md` for attribution. The project is independently maintained and does not claim DeepSeek endorsement.
