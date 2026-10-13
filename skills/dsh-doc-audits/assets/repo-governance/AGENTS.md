# AGENTS.md

{{PROJECT_NAME}} uses repository-local documentation governance. Read [docs/AGENTS.md](docs/AGENTS.md) before changing documentation.

- Update the current fact owner in the same change as behavior, API, configuration, storage, or operational changes.
- When new content has no owner yet, create the tier that the table in docs/AGENTS.md assigns to it; do not grow README or this file instead.
- Run `python scripts/verify_docs.py --repo .` before finishing and act on its warnings; for branch impact checks add `--base <ref>`.
- Do not edit generated material directly. Change its source and regenerate it.
