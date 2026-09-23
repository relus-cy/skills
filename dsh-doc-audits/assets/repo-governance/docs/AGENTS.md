# Documentation standard

## One owner per fact

Each durable fact has one current owner. Other pages summarize briefly and link to it.

| Tier | Owns | Does not own |
| --- | --- | --- |
| Root `AGENTS.md` | Standing orders needed in every agent session | Procedures, examples, rationale |
| `docs/architecture.md` | Ordered system map, boundaries, dependencies, extension points | Detailed subsystem contracts or decision history |
| `docs/subsystems/` | Current subsystem semantics, lifecycle, failure behavior, interfaces | Cross-system narrative or implementation diary |
| `docs/runbooks/` | Executable operating procedures with verification and recovery | Design rationale |
| `docs/reference/` | Precise lookup contracts such as APIs, configuration, formats, limits | Tutorials or historical discussion |
| `.agents/notes/` | Durable why, alternatives, consequences, and lifecycle | Current user instructions or implementation plans |
| Historical tiers | Plans, reports, handoffs, releases, postmortems | Current authority |

## Writing rules

- Describe current behavior in ordinary docs. Use Git history, Agent Notes, releases, plans, reports, handoffs, and postmortems for history.
- Verify commands, defaults, paths, APIs, and failure behavior from the current checkout. Mark anything unverified and name its verification owner.
- Put detail at the nearest owner. Higher-level pages link down instead of repeating it.
- Move a document and repair every inbound link in the same change.
- Keep generated outputs read-only; edit their source or generator.
- Treat budgets as guardrails. When a document exceeds one, relocate, then condense, then raise the limit with a recorded reason.

## Completion

Run `python scripts/verify_docs.py --repo .`. Major migrations also require a fresh-context reader to find project purpose, architecture, one subsystem contract, one operating procedure, and one decision rationale without scanning the whole repository.
