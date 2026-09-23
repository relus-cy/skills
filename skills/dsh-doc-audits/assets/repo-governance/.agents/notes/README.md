# Agent Notes

Agent Notes preserve durable decision rationale that code, tests, and ordinary documentation cannot carry. Use the path `{lifecycle}/{class}/yyyy-mm-dd-topic.md`; create class folders only when the project needs them.

## Lifecycle

- `proposed/`: substantial reviewed proposals not fully shipped.
- `implemented/`: shipped decisions, maintained in present tense as paths and names evolve.
- `rejected/`: meaningful proposals declined with a one-line reason in `Status:`.
- `archived/`: frozen implemented history that no longer serves as current authority.

## Creation threshold

Write or update a note only for a durable, repeatedly relevant decision with meaningful alternatives or trade-offs. Mechanical edits and local presentation changes do not need one.

## Required format

The first lines are:

```markdown
# Agent Note: Title

Status: proposed|implemented|rejected — reason
```

Every active note includes `## Problem` and `## Alternatives considered`.

- Proposed: `## Proposal`, `## Acceptance criteria`, `## Risks`.
- Implemented: `## Decision`, `## Consequences`; no proposal-stage headings.
- Rejected: retain the proposal and freeze it after recording the verdict.

When a proposal ships, move it and rewrite future-tense plans into present-tense decisions and consequences. Archived notes remain frozen and are never current authority.
