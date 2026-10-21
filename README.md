# skills

Reusable Agent Skills maintained by `relus-cy`. Every installable skill lives in `skills/<name>/`, and each of those directories is a complete bundle you can install on its own. Tests, development tools and design records stay at the repository root and are never installed.

| Skill | Origin |
| --- | --- |
| `dsh-doc-audits` | Original, documented below; carries its own [license](skills/dsh-doc-audits/LICENSE) and [notices](skills/dsh-doc-audits/NOTICE.md) |
| `recall` | Original; manual-only (`/recall`), see [recall](#recall) |
| `mail-cli` | User-provided email CLI with attachment enhancements and a portable skill; see [mail-cli](skills/mail-cli/README.md) |
| `create-verification-skill`, `maintain-verification-skill` | Vendored from [pstack](https://github.com/cursor/plugins/tree/main/pstack) with local patches; see [vendor sync](docs/runbooks/vendor-sync.md) |

## Install

Install everything, or pick one skill by its directory:

```bash
# skillshare
skillshare install github.com/relus-cy/skills --all
skillshare install relus-cy/skills/skills/dsh-doc-audits

# skills CLI (Claude Code, Codex, Cursor and others)
npx skills add relus-cy/skills
npx skills add relus-cy/skills --skill dsh-doc-audits
```

Copying a `skills/<name>/` directory into your agent's skills folder works as well.

## dsh-doc-audits · 0.5.0

A thin, portable adaptation of DeepSeek Harness documentation governance: one current owner per durable fact; separate current behavior, decision rationale and historical work. A capable model decides how to split a project. Local tools validate evidence, reviewed plans, write boundaries and documentation readiness.

Use it to initialize a documentation scaffold, migrate an existing repository, synchronize changed contracts, audit drift or upgrade generated governance assets. No fixed WebApp layout, project-specific domain names, mandatory external skill, model service or network access is built in.

## recall

Rebuilds recent working context from local Claude Code, Codex and Pi transcripts, then has the agent verify it against live `git`/`gh` state and write a short resume brief. It never reads another project unless asked, hides subagent sessions by default and redacts secrets in its output. `skills/recall/scripts/recall.py` is a read-only, standard-library CLI; `python3 skills/recall/scripts/recall.py list --help` documents scope, time window, store overrides (`RECALL_CLAUDE_ROOT`, `RECALL_CODEX_ROOT`, `RECALL_PI_ROOT`) and output. The workflow and brief format live in [its skill entry](skills/recall/SKILL.md).

## Install and use

Install `skills/dsh-doc-audits/` as shown above, or copy the complete directory to your Agent Skills location. Keep its scripts, schemas, references and assets together. Then give your agent this request:

```text
Use dsh-doc-audits to migrate this repository's documentation. Derive the
smallest useful owner structure from source and existing docs. Prepare and
review the plan before applying it; preserve history and product code.
Report actual verification and any missing independent assessment.
```

For read-only inspection from this checkout:

```bash
python skills/dsh-doc-audits/scripts/repo_docs.py doctor --repo /path/to/project --json
python skills/dsh-doc-audits/scripts/repo_docs.py plan --repo /path/to/project --json
```

`plan` starts as an unexecutable draft. The agent authors a proposal; `plan --proposal` seals it, `review-pack` supplies a focused review diff, and `apply` requires a separate approval of the unchanged plan. See the [skill entry](skills/dsh-doc-audits/SKILL.md) and [review/application contract](skills/dsh-doc-audits/references/authority-review.md).

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
