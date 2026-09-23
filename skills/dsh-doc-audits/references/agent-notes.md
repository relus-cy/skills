# Agent Notes

## Purpose

An Agent Note records durable decision rationale that current code and ordinary documentation cannot carry: the problem, the selected direction, genuine alternatives, and consequences. It prevents repeated re-litigation while keeping current contracts in their proper owners.

## Lifecycle

- `proposed/`: a substantial future decision reviewed before complete implementation.
- `implemented/`: a shipped decision. Maintain names, paths, defaults, and current consequences as the implementation evolves.
- `rejected/`: a meaningful proposal declined with the reason on the `Status:` line. Keep it only while it prevents a plausible mistake.
- `archived/`: frozen implemented history that has little current guidance value. It is never current authority.

The lifecycle is encoded in the path and must agree with the in-file status.

## Naming

Use:

```text
{lifecycle}/{class}/yyyy-mm-dd-topic-title.md
```

The date is when the topic was first proposed. Class names are project-owned; a compact default is `architecture`, `feature`, `bug-fix`, `simplification`, `process`, and `testing`.

## Required header

```markdown
# Agent Note: Title

Status: proposed
```

Allowed status forms:

```text
Status: proposed
Status: implemented
Status: rejected — concise reason
```

Archived notes retain `Status: implemented`; projects may add a mechanically checked archive date.

## Body contracts

Proposed:

```markdown
## Problem
## Proposal
## Alternatives considered
## Acceptance criteria
## Risks
```

Implemented:

```markdown
## Problem
## Decision
## Alternatives considered
## Consequences
```

Rejected notes retain their proposal body and verdict. Every active note includes `## Alternatives considered`; record real alternatives only.

When a proposal ships, move it, update status, rewrite future-tense proposal into present-tense decision, and convert acceptance criteria and risks into verification and consequences. Implemented notes must not retain `## Proposal`, `## Plan`, `## Migration plan`, or `## Acceptance criteria`.

## Creation threshold

Create or update a note when a decision is cross-module, hard to reverse, costly, repeatedly debated, security-sensitive, wire- or data-format relevant, or rich in meaningful alternatives. Skip mechanical edits, local refactors with no durable trade-off, and routine presentation changes.

Update the note that already owns a decision instead of creating a duplicate. A different decision gets a new cross-linked note. Archive or delete only after checking inbound links and preserving unique rationale in the current owner.
