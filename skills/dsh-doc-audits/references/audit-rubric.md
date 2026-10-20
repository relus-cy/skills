# Audit Rubric

## Order of work

1. Inventory documentation and source surfaces.
2. Run deterministic repository-local verification.
3. Establish current evidence for the requested scope.
4. Compare each claim with the source that settles its class ([claim authority](#claim-authority)); in a docs-only scope, compare the set with itself ([internal consistency](#internal-consistency)).
5. Audit ownership, duplication, history placement, and retrieval paths.
6. Report before repair unless direct repair was requested.

## Evidence standard

Every finding includes the following; a needs-decision finding names the unresolved choice instead of a repair direction:

- the finding class: documentation drift, implementation gap, internal conflict, or needs decision;
- the source that settles the claim: source code, schema, manifest, test, generator, command output, or approved decision owner; in a docs-only scope, the conflicting passages and any supersession evidence;
- the stale, missing, duplicated, or misplaced documentation;
- the affected reader or operator;
- a specific repair direction;
- checks run and checks skipped.

A negative claim such as “nothing reads this setting” requires checking all plausible locations and transitive callers. A single search result is not enough.

## Claim authority

Name the source that settles each class of claim before choosing a repair target. Documents that agree with each other may still misdescribe the system, and code may fall short of what was decided.

- A current-behavior claim in a current owner is settled by source, tests, configuration and safely executed commands. A mismatch is **documentation drift**; repair the document.
- An intended or contractual claim in an approved decision owner is settled by that decision. Such owners include an implemented Agent Note or accepted ADR, an approved spec that has not shipped, a published API or schema contract, and a security policy. A mismatch is an **implementation gap**. Report it; do not weaken the decision to match the code, and do not change product code during an audit.
- A current owner that presents approved but unimplemented behavior as current gets both findings: the implementation gap, and a repair that states the actual behavior and links the unmet decision.
- When approval status or the governing source is unclear, record **needs decision**, not a confirmed defect.

Severity rates the actual effect of the mismatch, whichever side needs repair.

## Internal consistency

Use these checks in a docs-only scope and alongside code comparison:

- contradiction: two passages cannot both hold, such as a limit of 5 in one PRD and 10 in another;
- terminology drift: several names for one concept, or one name used for different concepts;
- boundary mismatch: something listed as included in one place is excluded in another;
- sequence mismatch: a status, phase, date or dependency order that the other documents rule out;
- weak acceptance: passing every listed criterion would still leave the goal unmet.

Call text stale only when the set itself shows supersession: a later date or status, a replacement notice, or a recorded decision order. Without that evidence, a contradicted or unsupported claim is an internal conflict or needs decision. A set that agrees with itself has been shown consistent; whether the system behaves that way is still unverified.

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
- Class:
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
