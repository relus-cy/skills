# AGENTS.md

This repository contains reusable Agent Skills. Follow the Agent Skills specification: each skill lives in a top-level `<name>/` directory, the directory name matches the `name` frontmatter field, and detailed material stays in one-hop `references/`, `scripts/`, or `assets/` resources.

Before changing `dsh-doc-audits`, read [the architecture](docs/architecture.md), [the governance CLI contract](docs/subsystems/governance-cli.md), and the relevant design or implementation plan under `docs/superpowers/`.

- Skill activation and stable interface changes update [the skill contract](docs/reference/skill-contract.md).
- CLI or template behavior changes update [the governance CLI subsystem](docs/subsystems/governance-cli.md).
- Durable trade-offs update the existing Agent Note or create a new lifecycle-correct note.
- Run `bash scripts/verify.sh` before completion.
