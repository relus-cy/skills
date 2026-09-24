# Documentation standard

## One owner per fact

Each durable fact has one current owner. Other pages summarize briefly and link to it.

| Tier | Owns | Does not own | Create when |
| --- | --- | --- | --- |
| Root `AGENTS.md` | Standing orders needed in every agent session | Procedures, examples, rationale | Installed |
| `docs/architecture.md` | Ordered system map, boundaries, dependencies, extension points | Detailed subsystem contracts or decision history | The project has more than one module, or a flow crosses modules |
| `docs/subsystems/` | Current subsystem semantics, lifecycle, failure behavior, interfaces | Cross-system narrative or implementation diary | One module's contract no longer fits in `architecture.md` |
| `docs/runbooks/` | Executable operating procedures with verification and recovery | Design rationale | A procedure has verification or recovery steps |
| `docs/reference/` | Precise lookup contracts such as APIs, configuration, formats, limits | Tutorials or historical discussion | Readers must look up exact keys, fields, formats or limits |
| `docs/backlog.md` | Deferred work that spans releases, with its current disposition | Designs and plans | Deferred work outlives one plan |
| `.agents/notes/` | Durable why, alternatives, consequences, and lifecycle | Current user instructions or implementation plans | A decision is cross-module, hard to reverse, or argued a second time |
| Historical tiers | Plans, reports, handoffs, releases, postmortems | Current authority | A planning, reporting or release workflow writes into `docs/` |

A tier exists only once it has content; do not create empty pages. Creating one needs no manifest edit: `docs/governance.yaml` already lists every tier, its budget and its code mappings. Verifier warnings such as `documentation-untiered`, `doc-owner-missing` and an exceeded budget mean content has outgrown its current home.

## Writing rules

- Describe current behavior in ordinary docs. Use Git history, Agent Notes, releases, plans, reports, handoffs, and postmortems for history.
- Verify safe, authorized commands in isolation; mark dangerous or unavailable operations unverified with an owner. Verify defaults, paths, APIs, and failure behavior from the current checkout. Mark anything unverified and name its verification owner.
- When a plan, spec or report ships, write its durable conclusions (behavior, contracts, defaults, decisions) into the current owner or Agent Note in the same change. After write-back the plan is expiring scratch: delete it, or keep it only under a `tiers.historical` folder, which is never current authority.
- Put detail at the nearest owner. Higher-level pages link down instead of repeating it.
- Move a document and repair every inbound link in the same change.
- Keep generated outputs read-only; edit their source or generator.
- Treat budgets as guardrails. When a document exceeds one, relocate, then condense, then raise the limit with a recorded reason.

## Completion

Run `python scripts/verify_docs.py --repo .`. A pass is structure-only: it does not compare any document with the code. Major migrations also require a fresh-context reader to find project purpose, architecture, one subsystem contract, one operating procedure, and one decision rationale without scanning the whole repository.

Scaffolds use `Status: scaffold` until authored. They do not certify current behavior. Run the local verifier with `--completion` before declaring a migration ready; semantic review and independent-reader evidence remain separately required.
