# AGENTS.md

{{PROJECT_NAME}} uses repository-local documentation governance. Read [docs/AGENTS.md](docs/AGENTS.md) before changing documentation and [docs/architecture.md](docs/architecture.md) before changing cross-module structure.

- Update the current fact owner in the same change as behavior, API, configuration, storage, or operational changes.
- Keep rationale in [Agent Notes](.agents/notes/README.md); keep plans, reports, handoffs, releases, and postmortems historical.
- Run `python scripts/verify_docs.py --repo .`; for branch impact checks add `--base <ref>`.
- Do not edit generated material directly. Change its source and regenerate it.
