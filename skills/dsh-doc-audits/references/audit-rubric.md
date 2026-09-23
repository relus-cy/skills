# Audit Rubric

## Order of work

1. Inventory documentation and source surfaces.
2. Run deterministic repository-local verification.
3. Establish current evidence for the requested scope.
4. Compare claims with behavior.
5. Audit ownership, duplication, history placement, and retrieval paths.
6. Report before repair unless direct repair was requested.

## Evidence standard

A confirmed drift finding includes:

- the current source of truth: source code, schema, manifest, test, generator, command output, or current decision owner;
- the stale, missing, duplicated, or misplaced documentation;
- the affected reader or operator;
- a specific repair direction;
- checks run and checks skipped.

A negative claim such as “nothing reads this setting” requires checking all plausible locations and transitive callers. A single search result is not enough.

## Severity

- `P0`: stale guidance can cause security exposure, data loss, outage, credential mishandling, or irreversible corruption.
- `P1`: blocks deployment, recovery, setup, migration, API integration, or a common operator workflow.
- `P2`: materially misleads maintainers, agents, users, or reviewers about behavior or ownership.
- `P3`: lower-risk naming, navigation, example, or prose cleanup.

Repository-local deterministic failures use `error` and `warning`; translate their user impact into the P0–P3 rubric in a semantic report.

## Corpus checks

- one current owner per fact;
- no historical document presented as current authority;
- no current contract duplicated across owners;
- no generated catalog maintained by hand;
- no stale paths, commands, defaults, APIs, fields, or limits;
- no proposal-stage language in implemented decisions;
- no frozen archive used as a mutable current source;
- no entry page overloaded with descendant detail;
- likely failures, recovery, and verification are documented where procedures require them.

## Audit report

```markdown
# Documentation audit: scope

## Summary

## Findings

### P1: title
- Drift:
- Impact:
- Evidence:
- Repair direction:

## Current owners checked
## Historical surfaces preserved
## Checks run
## Checks skipped and residual risk
## Fresh-session result
```

For a whole-repository audit, list inventoried surfaces that were not deeply inspected. Never imply complete coverage when time or access limited the pass.
