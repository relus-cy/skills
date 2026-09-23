# skills

Reusable Agent Skills maintained by `relus-cy`.

## Included skill

### `dsh-doc-audits`

A portable adaptation of the DeepSeek Harness documentation governance model. It bootstraps new repositories, migrates brownfield documentation, maps Git diffs to current owners, audits documentation drift, and installs repository-local verification.

The design keeps one current owner per durable fact and separates current behavior, decision rationale, historical process, and generated material. DeepSeek-specific bilingual, Cordis, VitePress, TypeScript, and pnpm mechanics are intentionally excluded.

## Run it

From this repository:

```bash
python skills/dsh-doc-audits/scripts/repo_docs.py inspect --repo /path/to/project
python skills/dsh-doc-audits/scripts/repo_docs.py plan --repo /path/to/project --profile small-web-app
python skills/dsh-doc-audits/scripts/repo_docs.py bootstrap --repo /path/to/project --profile small-web-app --dry-run
```

The target repository receives its own `scripts/verify_docs.py` and CI workflow. Existing files are preserved unless `--force` is explicit.

## Repository documentation

- [Architecture](docs/architecture.md)
- [Governance CLI](docs/subsystems/governance-cli.md)
- [Skill contract](docs/reference/skill-contract.md)
- [Release procedure](docs/runbooks/release.md)
- [Decision rationale](.agents/notes/implemented/process/2026-09-23-portable-dsh-doc-governance.md)

## Verify

```bash
bash scripts/verify.sh
```

The suite uses Python's standard library and Git; no runtime Python dependencies are required.
